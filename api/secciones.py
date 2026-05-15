from fastapi import APIRouter, Depends, HTTPException
import sqlite3

# Inicializamos el enrutador modular
router = APIRouter(
    prefix="/api/secciones",
    tags=["Secciones"]
)

# Helpers limpios de la caja de herramientas
from utils import get_db, rows_to_dicts, get_seccion_ocupacion, uid, now

# 🌟 NUEVO ENFOQUE: Importamos el esquema desde su archivo dedicado
from schemas import SeccionIn

from security import require_master

@router.get("")
def listar_secciones(con: sqlite3.Connection = Depends(get_db)):
    secciones = rows_to_dicts(con.execute(
        "SELECT * FROM secciones WHERE activa=1 ORDER BY nombre"
    ))
    for s in secciones:
        occ = get_seccion_ocupacion(con, s["id"])
        s["ocupados"]    = occ["ocupados"]
        s["disponibles"] = occ["disponibles"]
        
        # Jefe asignado a esta sección
        jefe = con.execute("""
            SELECT u.id, u.nombre_completo, u.email
            FROM   usuarios u
            WHERE  u.seccion_id=? AND u.rol='jefe_seccion' AND u.activo=1
            LIMIT 1
        """, [s["id"]]).fetchone()
        s["jefe_id"]     = jefe["id"]             if jefe else None
        s["jefe_nombre"] = jefe["nombre_completo"] if jefe else None
        
        # Número de scouters en la sección
        s["scouters"] = con.execute(
            "SELECT COUNT(*) FROM miembros WHERE seccion_id=? AND tipo='scouter' AND activo=1",
            [s["id"]]
        ).fetchone()[0]
    return secciones


@router.get("/{sid}")
def get_seccion(sid: str, con: sqlite3.Connection = Depends(get_db)):
    rows = rows_to_dicts(con.execute("SELECT * FROM secciones WHERE id=?", [sid]))
    if not rows:
        raise HTTPException(404, "Sección no encontrada.")
    s = rows[0]
    s.update(get_seccion_ocupacion(con, sid))
    return s


@router.post("", status_code=201)
def crear_seccion(body: SeccionIn, user: dict = Depends(require_master),
                  con: sqlite3.Connection = Depends(get_db)):
    sid = uid()
    con.execute(
        "INSERT INTO secciones VALUES (?,?,?,?,?,?,?,1,?)",
        [sid, body.nombre, body.rama, body.color, body.capacidad,
         body.lider, body.descripcion, now()],
    )
    return {"id": sid, "nombre": body.nombre}


@router.put("/{sid}")
def actualizar_seccion(
    sid: str,
    body: SeccionIn,
    user: dict = Depends(require_master),
    con: sqlite3.Connection = Depends(get_db),
):
    con.execute(
        "UPDATE secciones SET nombre=?, rama=?, color=?, capacidad=?, "
        "lider=?, descripcion=? WHERE id=?",
        [body.nombre, body.rama, body.color, body.capacidad,
         body.lider, body.descripcion, sid],
    )
    return {"ok": True}


@router.delete("/{sid}")
def eliminar_seccion(sid: str, user: dict = Depends(require_master),
                     con: sqlite3.Connection = Depends(get_db)):
    miembros_activos = con.execute(
        "SELECT COUNT(*) FROM miembros WHERE seccion_id=? AND activo=1", [sid]
    ).fetchone()[0]
    if miembros_activos > 0:
        raise HTTPException(
            400,
            f"La sección tiene {miembros_activos} miembro(s) activo(s). "
            "Transfierelos antes de eliminar.",
        )
    con.execute("UPDATE secciones SET activa=0 WHERE id=?", [sid])
    return {"ok": True}