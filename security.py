import hashlib
import logging
import secrets
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from typing import Optional
import os
from utils import get_db, now, uid
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # ← ¡NUEVO!

# Logging interno
log = logging.getLogger("scoutdb")

DOMAIN = os.getenv("SCOUT_DOMAIN", "domscout.org")

# Jerarquía de roles (mayor índice = mayor autoridad)
ROL_NIVEL = {
    "beneficiario":    0,
    "colaborador":     1,
    "subjefe_seccion": 2,
    "jefe_seccion":    3,
    "master":          4,
    "dev":             5,
}

# ── HELPERS INTERNOS Y DE ENCRIPTACIÓN ─────────────────────────────────────

def _normalize_str(s: str) -> str:
    """Elimina acentos y caracteres especiales, retorna solo ASCII."""
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()

def generate_username(nombre_completo: str) -> str:
    """Genera un username dinámico a partir del nombre completo."""
    particles = {"de", "del", "la", "las", "los", "el", "y", "e"}
    parts = [_normalize_str(p) for p in nombre_completo.strip().split() if p.lower() not in particles]
    if not parts:
        return "usuario"
    nombre = parts[0]
    ap1_ini = parts[-2][0] if len(parts) >= 3 else ""
    ap2_ini = parts[-1][0] if len(parts) >= 2 else ""
    return nombre + ap1_ini + ap2_ini

def hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return key.hex()

def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return hash_password(password, salt) == stored_hash

def create_session(con: sqlite3.Connection, usuario_id: str) -> str:
    token = secrets.token_hex(32)
    expira = (datetime.now() + timedelta(hours=24)).isoformat()
    con.execute("DELETE FROM sesiones WHERE usuario_id=? OR expira_en < ?", [usuario_id, now()])
    con.execute("INSERT INTO sesiones VALUES (?,?,?,?)", [token, usuario_id, now(), expira])
    return token

# ── DEPENDENCIAS DE ACCESO (LOS CANDADOS) ──────────────────────────────────

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    con: sqlite3.Connection = Depends(get_db)  # Asegúrate de que get_db esté importado arriba
) -> Optional[dict]:
    if not auth or auth.scheme != "Bearer":
        return None
    
    token = auth.credentials 
    
    row = con.execute("""
        SELECT u.id, u.email, u.username, u.nombre_completo,
               u.rol, u.tipo, u.seccion_id, u.activo, u.debe_cambiar_pass
        FROM   sesiones s
        JOIN   usuarios u ON s.usuario_id = u.id
        WHERE  s.token = ? AND s.expira_en > ? AND u.activo = 1
    """, [token, now()]).fetchone()
    
    if not row:
        return None
    return dict(row)


def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(401, "Autenticación requerida.")
    return user

def require_master(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(401, "Autenticación requerida.")
    if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
        raise HTTPException(403, "Solo el master o dev puede realizar esta acción.")
    return user

def require_dev(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(401, "Autenticación requerida.")
    if user["rol"] != "dev":
        raise HTTPException(403, "Solo los desarrolladores pueden realizar esta acción.")
    return user

def require_jefe(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(401, "Autenticación requerida.")
    if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["jefe_seccion"]:
        raise HTTPException(403, "Se requiere rol de jefe de sección o superior.")
    return user

# ── REGLAS DE NEGOCIO SCOUT ────────────────────────────────────────────────

def can_manage_seccion(user: dict, seccion_id: Optional[str]) -> bool:
    if ROL_NIVEL.get(user["rol"], 0) >= ROL_NIVEL["master"]:
        return True
    if user["seccion_id"] and user["seccion_id"] == seccion_id:
        return True
    return False

def determinar_rol_scouter(con: sqlite3.Connection, seccion_id: Optional[str]) -> str:
    if not seccion_id:
        return "colaborador"
    jefe = con.execute("SELECT id FROM usuarios WHERE seccion_id=? AND rol='jefe_seccion' AND activo=1", [seccion_id]).fetchone()
    return "subjefe_seccion" if jefe else "jefe_seccion"

def crear_cuenta_scouter(con: sqlite3.Connection, nombre: str, apellido: str, seccion_id: Optional[str], mid: str) -> dict:
    nombre_completo = f"{nombre} {apellido}"
    username = generate_username(nombre_completo)
    email    = f"{username}@{DOMAIN}"

    suffix = 1
    while con.execute("SELECT id FROM usuarios WHERE email=?", [email]).fetchone():
        username = generate_username(nombre_completo) + str(suffix)
        email    = f"{username}@{DOMAIN}"
        suffix  += 1

    rol  = determinar_rol_scouter(con, seccion_id)
    salt = secrets.token_hex(16)
    pw   = username
    con.execute(
        """INSERT INTO usuarios
           (id, email, username, nombre_completo, password_hash, salt,
            password_temporal, rol, tipo, seccion_id, miembro_id,
            activo, debe_cambiar_pass, creado_en)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,1,1,?)""",
        [uid(), email, username, nombre_completo, hash_password(pw, salt), salt,
         pw, rol, "scouter", seccion_id, mid, now()],
    )
    log.info("Cuenta scouter auto-creada: %s (%s)", email, rol)
    return {"email": email, "password_temporal": pw, "rol": rol, "username": username}