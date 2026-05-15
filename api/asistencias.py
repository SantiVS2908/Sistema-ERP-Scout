from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from typing import Optional

router = APIRouter(
    prefix="/api/asistencias",
    tags=["Asistencias"]
)

# Caja de herramientas central
from utils import get_db, rows_to_dicts, uid

# Esquemas de validación
from schemas import AsistenciaIn, AsistenciaLote

from security import require_jefe, ROL_NIVEL

@router.get("")
def listar_asistencias(
    seccion_id: Optional[str] = None,
    actividad:  Optional[str] = None,
    fecha:      Optional[str] = None,
    miembro_id: Optional[str] = None,
    con: sqlite3.Connection = Depends(get_db),
):
    sql = """
        SELECT a.*,
               m.nombre || ' ' || m.apellido AS miembro_nombre,
               m.seccion_id,
               s.nombre AS seccion_nombre
        FROM   asistencias a
        JOIN   miembros    m ON a.miembro_id = m.id
        LEFT JOIN secciones s ON m.seccion_id = s.id
        WHERE  1=1
    """
    params: list = []
    if seccion_id:
        sql += " AND m.seccion_id=?";            params.append(seccion_id)
    if actividad:
        sql += " AND LOWER(a.actividad) LIKE ?"; params.append(f"%{actividad.lower()}%")
    if fecha:
        sql += " AND a.fecha=?";                 params.append(fecha)
    if miembro_id:
        sql += " AND a.miembro_id=?";            params.append(miembro_id)
    sql += " ORDER BY a.fecha DESC, miembro_nombre"
    return rows_to_dicts(con.execute(sql, params))


@router.get("/actividades")
def listar_actividades(con: sqlite3.Connection = Depends(get_db)):
    rows = con.execute("""
        SELECT actividad, fecha,
               COUNT(*) AS total,
               SUM(CASE WHEN presente THEN 1 ELSE 0 END) AS presentes
        FROM   asistencias
        GROUP  BY actividad, fecha
        ORDER  BY fecha DESC
    """).fetchall()
    return [
        {"actividad": r[0], "fecha": r[1], "total": r[2], "presentes": r[3] or 0}
        for r in rows
    ]


@router.post("/lote", status_code=201)
def registrar_asistencia_lote(
    body: AsistenciaLote,
    user: dict = Depends(require_jefe),
    con: sqlite3.Connection = Depends(get_db),
):
    if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"] and user.get("seccion_id"):
        for r in body.registros:
            m = con.execute("SELECT seccion_id FROM miembros WHERE id=?",
                            [r["miembro_id"]]).fetchone()
            if m and m["seccion_id"] != user["seccion_id"]:
                raise HTTPException(
                    403, "No puedes registrar asistencia de miembros de otra sección."
                )

    con.execute("BEGIN IMMEDIATE")
    try:
        con.execute(
            "DELETE FROM asistencias WHERE actividad=? AND fecha=?",
            [body.actividad, body.fecha],
        )
        for r in body.registros:
            con.execute(
                "INSERT INTO asistencias VALUES (?,?,?,?,?,?)",
                [uid(), r["miembro_id"], body.actividad, body.fecha,
                 1 if r.get("presente") else 0, r.get("notas")],
            )
    except Exception:
        con.rollback()
        raise
    presentes = sum(1 for r in body.registros if r.get("presente"))
    log.info(
        "Asistencia '%s' %s: %d/%d presentes.",
        body.actividad, body.fecha, presentes, len(body.registros),
    )
    return {"ok": True, "registros": len(body.registros)}


@router.post("", status_code=201)
def crear_asistencia(
    body: AsistenciaIn,
    con: sqlite3.Connection = Depends(get_db),
):
    aid = uid()
    con.execute(
        "INSERT INTO asistencias VALUES (?,?,?,?,?,?)",
        [aid, body.miembro_id, body.actividad, body.fecha,
         1 if body.presente else 0, body.notas],
    )
    return {"id": aid}