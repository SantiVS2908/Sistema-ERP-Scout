from fastapi import APIRouter, Depends, HTTPException
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
    con = Depends(get_db),
):
    with con.cursor() as cur:
        cur.execute("""
            SELECT u.id, u.email, u.username, u.nombre_completo,
                   u.rol, u.tipo, u.seccion_id, u.activo, u.debe_cambiar_pass,
                   u.creado_en, u.ultimo_login, u.password_temporal,
                   s.nombre AS seccion_nombre
            FROM   usuarios u
            LEFT JOIN secciones s ON u.seccion_id = s.id
            ORDER  BY u.rol DESC, u.nombre_completo
        """)
        return rows_to_dicts(cur)


@router.post("", status_code=201)
def crear_usuario(
    body: UsuarioIn,
    user: dict = Depends(require_master),
    con = Depends(get_db),
):
    if body.rol == "dev" and user["rol"] != "dev":
        raise HTTPException(403, "Solo un dev puede crear cuentas dev.")

    username  = generate_username(body.nombre_completo)
    email     = f"{username}@{DOMAIN}"

    with con.cursor() as cur:
        cur.execute(
            "SELECT id FROM usuarios WHERE email=%s OR username=%s", [email, username]
        )
        exists = cur.fetchone()
        
        if exists:
            raise HTTPException(400, f"Ya existe un usuario con ese nombre/email ({email}).")

        uid_     = uid()
        password = username   # contraseña temporal = username
        salt     = secrets.token_hex(16)
        p_hash   = hash_password(password, salt)

        cur.execute(
            """INSERT INTO usuarios
               (id, email, username, nombre_completo, password_hash, salt,
                password_temporal, rol, tipo, seccion_id, miembro_id,
                activo, debe_cambiar_pass, creado_en)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,true,%s)""",
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
    con = Depends(get_db),
):
    if body.rol == "dev" and user["rol"] != "dev":
        raise HTTPException(403, "Solo un dev puede asignar el rol dev.")
    
    with con.cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET rol=%s, seccion_id=%s WHERE id=%s",
            [body.rol, body.seccion_id, uid_],
        )
    return {"ok": True}


@router.delete("/{uid_}")
def desactivar_usuario(
    uid_: str,
    user: dict = Depends(require_master),
    con = Depends(get_db),
):
    if uid_ == user["id"]:
        raise HTTPException(400, "No puedes desactivar tu propia cuenta.")
    
    with con.cursor() as cur:
        cur.execute("UPDATE usuarios SET activo=false WHERE id=%s", [uid_])
        cur.execute("DELETE FROM sesiones WHERE usuario_id=%s", [uid_])
        
    return {"ok": True}