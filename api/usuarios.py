from fastapi import APIRouter, Depends, HTTPException
import sqlite3
import secrets

router = APIRouter(
    prefix="/api/usuarios",
    tags=["Usuarios (Gestión)"]
)

# Caja de herramientas limpia
from utils import get_db, rows_to_dicts, uid, now

# Escudos de validación
from schemas import UsuarioIn, ActualizarRolIn

from security import require_master, generate_username, hash_password, DOMAIN, log

@router.get("")
def listar_usuarios(
    user: dict = Depends(require_master),
    con:  sqlite3.Connection = Depends(get_db),
):
    rows = rows_to_dicts(con.execute("""
        SELECT u.id, u.email, u.username, u.nombre_completo,
               u.rol, u.tipo, u.seccion_id, u.activo, u.debe_cambiar_pass,
               u.creado_en, u.ultimo_login, u.password_temporal,
               s.nombre AS seccion_nombre
        FROM   usuarios u
        LEFT JOIN secciones s ON u.seccion_id = s.id
        ORDER  BY u.rol DESC, u.nombre_completo
    """))
    return rows


@router.post("", status_code=201)
def crear_usuario(
    body: UsuarioIn,
    user: dict = Depends(require_master),
    con:  sqlite3.Connection = Depends(get_db),
):
    if body.rol == "dev" and user["rol"] != "dev":
        raise HTTPException(403, "Solo un dev puede crear cuentas dev.")

    username  = generate_username(body.nombre_completo)
    email     = f"{username}@{DOMAIN}"

    exists = con.execute(
        "SELECT id FROM usuarios WHERE email=? OR username=?", [email, username]
    ).fetchone()
    if exists:
        raise HTTPException(400, f"Ya existe un usuario con ese nombre/email ({email}).")

    uid_     = uid()
    password = username   # contraseña temporal = username
    salt     = secrets.token_hex(16)
    p_hash   = hash_password(password, salt)

    con.execute(
        """INSERT INTO usuarios
           (id, email, username, nombre_completo, password_hash, salt,
            password_temporal, rol, tipo, seccion_id, miembro_id,
            activo, debe_cambiar_pass, creado_en)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,1,1,?)""",
        [uid_, email, username, body.nombre_completo, p_hash, salt,
         password, body.rol, body.tipo, body.seccion_id, body.miembro_id, now()],
    )
    log.info("Usuario creado: %s (%s | %s)", email, body.rol, body.nombre_completo)
    return {
        "id":                uid_,
        "email":             email,
        "username":          username,
        "password_temporal": password,
        "rol":               body.rol,
    }


@router.put("/{uid_}/rol")
def actualizar_rol_usuario(
    uid_: str,
    body: ActualizarRolIn,
    user: dict = Depends(require_master),
    con:  sqlite3.Connection = Depends(get_db),
):
    if body.rol == "dev" and user["rol"] != "dev":
        raise HTTPException(403, "Solo un dev puede asignar el rol dev.")
    con.execute(
        "UPDATE usuarios SET rol=?, seccion_id=? WHERE id=?",
        [body.rol, body.seccion_id, uid_],
    )
    return {"ok": True}


@router.delete("/{uid_}")
def desactivar_usuario(
    uid_: str,
    user: dict = Depends(require_master),
    con:  sqlite3.Connection = Depends(get_db),
):
    if uid_ == user["id"]:
        raise HTTPException(400, "No puedes desactivar tu propia cuenta.")
    con.execute("UPDATE usuarios SET activo=0 WHERE id=?", [uid_])
    con.execute("DELETE FROM sesiones WHERE usuario_id=?", [uid_])
    return {"ok": True}