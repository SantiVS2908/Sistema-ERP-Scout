from fastapi import APIRouter, Depends, HTTPException, Header
import secrets
from typing import Optional

router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticación"]
)

# Herramientas del sistema
from utils import get_db, now

# Escudos de validación
from schemas import LoginIn, CambiarPasswordIn

from security import verify_password, hash_password, create_session, require_auth, DOMAIN, log


@router.post("/login")
def login(body: LoginIn, con = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email:
        email = f"{email}@{DOMAIN}"

    with con.cursor() as cur:
        cur.execute(
            "SELECT * FROM usuarios WHERE (email=%s OR username=%s) AND activo=true",
            [email, body.email.strip()],
        )
        u = cur.fetchone()
        
    if not u:
        raise HTTPException(401, "Credenciales inválidas.")

    if not verify_password(body.password, u["salt"], u["password_hash"]):
        raise HTTPException(401, "Credenciales inválidas.")

    # Nota arquitectónica: create_session vive en security.py, 
    # por lo que ese archivo también tendrá que ser refactorizado pronto.
    token = create_session(con, u["id"])
    
    with con.cursor() as cur:
        cur.execute("UPDATE usuarios SET ultimo_login=%s WHERE id=%s", [now(), u["id"]])
        
    log.info("Login: %s (%s)", u["email"], u["rol"])

    return {
        "token":            token,
        "usuario": {
            "id":                u["id"],
            "email":             u["email"],
            "username":          u["username"],
            "nombre_completo":   u["nombre_completo"],
            "rol":               u["rol"],
            "tipo":              u["tipo"],
            "seccion_id":        u["seccion_id"],
            "debe_cambiar_pass": bool(u["debe_cambiar_pass"]),
        },
    }


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(None),
    con = Depends(get_db),
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        with con.cursor() as cur:
            cur.execute("DELETE FROM sesiones WHERE token=%s", [token])
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(require_auth)):
    return user


@router.put("/cambiar-password")
def cambiar_password(
    body:          CambiarPasswordIn,
    user:          dict = Depends(require_auth),
    con = Depends(get_db),
):
    with con.cursor() as cur:
        cur.execute(
            "SELECT password_hash, salt FROM usuarios WHERE id=%s", [user["id"]]
        )
        row = cur.fetchone()
        
    if not row or not verify_password(body.password_actual, row["salt"], row["password_hash"]):
        raise HTTPException(400, "La contraseña actual es incorrecta.")
    if len(body.password_nueva) < 6:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 6 caracteres.")
    
    new_hash, new_salt = _make_hash(body.password_nueva)
    
    with con.cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET password_hash=%s, salt=%s, debe_cambiar_pass=false, password_temporal=NULL WHERE id=%s",
            [new_hash, new_salt, user["id"]],
        )
    return {"ok": True}


def _make_hash(password: str) -> tuple:
    salt = secrets.token_hex(16)
    return hash_password(password, salt), salt