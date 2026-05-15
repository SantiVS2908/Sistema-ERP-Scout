from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from typing import Optional
from datetime import date

router = APIRouter(
    prefix="/api/calendario",
    tags=["Calendario"]
)

# Helpers e infraestructura desde utils.py
from utils import get_db, rows_to_dicts, today, uid, now

# Esquema de validación
from schemas import ActividadIn

from security import require_jefe

@router.get("")
def listar_calendario(
    seccion: Optional[str] = None,
    desde:   Optional[str] = None,
    hasta:   Optional[str] = None,
    con: sqlite3.Connection = Depends(get_db),
):
    sql    = "SELECT * FROM actividades_grupo WHERE 1=1"
    params: list = []
    if seccion: sql += " AND seccion=?";  params.append(seccion)
    if desde:   sql += " AND fecha>=?";   params.append(desde)
    if hasta:   sql += " AND fecha<=?";   params.append(hasta)
    sql += " ORDER BY fecha ASC, hora ASC"
    return rows_to_dicts(con.execute(sql, params))


@router.get("/proximas")
def proximas_actividades(
    seccion: Optional[str] = None,
    con: sqlite3.Connection = Depends(get_db),
):
    desde = today()
    hasta = date.fromordinal(date.today().toordinal() + 30).isoformat()
    sql    = "SELECT * FROM actividades_grupo WHERE fecha>=? AND fecha<=?"
    params: list = [desde, hasta]
    if seccion:
        sql += " AND seccion=?"
        params.append(seccion)
    sql += " ORDER BY fecha ASC, hora ASC"
    return rows_to_dicts(con.execute(sql, params))


@router.get("/proximas_seccion")
def proximas_actividades_seccion(
    nombre: Optional[str] = None,
    limit:  int           = 3,
    con: sqlite3.Connection = Depends(get_db),
):
    hoy = today()
    if nombre:
        rows = rows_to_dicts(con.execute("""
            SELECT * FROM actividades_grupo
            WHERE  fecha >= ?
              AND  (LOWER(seccion) = LOWER(?) OR seccion = 'Todo el Grupo')
            ORDER  BY fecha ASC, hora ASC
            LIMIT  ?
        """, [hoy, nombre, limit]))
    else:
        rows = rows_to_dicts(con.execute("""
            SELECT * FROM actividades_grupo
            WHERE  fecha >= ?
            ORDER  BY fecha ASC, hora ASC
            LIMIT  ?
        """, [hoy, limit]))
    return rows


@router.post("", status_code=201)
def crear_actividad(body: ActividadIn, user: dict = Depends(require_jefe),
                    con: sqlite3.Connection = Depends(get_db)):
    aid = uid()
    con.execute(
        "INSERT INTO actividades_grupo VALUES (?,?,?,?,?,?,?,?,?)",
        [aid, body.titulo, body.fecha, body.hora,
         body.descripcion, body.lugar, body.seccion, body.color, now()],
    )
    log.info("Actividad creada: %s (%s)", body.titulo, body.fecha)
    return {"id": aid}


@router.put("/{aid}")
def actualizar_actividad(
    aid: str,
    body: ActividadIn,
    user: dict = Depends(require_jefe),
    con: sqlite3.Connection = Depends(get_db),
):
    con.execute(
        "UPDATE actividades_grupo SET titulo=?, fecha=?, hora=?, descripcion=?, "
        "lugar=?, seccion=?, color=? WHERE id=?",
        [body.titulo, body.fecha, body.hora, body.descripcion,
         body.lugar, body.seccion, body.color, aid],
    )
    return {"ok": True}


@router.delete("/{aid}")
def eliminar_actividad(aid: str, user: dict = Depends(require_jefe),
                       con: sqlite3.Connection = Depends(get_db)):
    con.execute("DELETE FROM actividades_grupo WHERE id=?", [aid])
    return {"ok": True}