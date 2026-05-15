from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

router = APIRouter(
    prefix="/api/asistencias",
    tags=["Asistencias"]
)

# Caja de herramientas central
from utils import get_db, rows_to_dicts, uid

# Esquemas de validación
from schemas import AsistenciaIn, AsistenciaLote

from security import require_jefe, ROL_NIVEL, log

@router.get("")
def listar_asistencias(
    seccion_id: Optional[str] = None,
    actividad:  Optional[str] = None,
    fecha:      Optional[str] = None,
    miembro_id: Optional[str] = None,
    con = Depends(get_db),
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
        sql += " AND m.seccion_id=%s"
        params.append(seccion_id)
    if actividad:
        sql += " AND LOWER(a.actividad) LIKE %s"
        params.append(f"%{actividad.lower()}%")
    if fecha:
        sql += " AND a.fecha=%s"
        params.append(fecha)
    if miembro_id:
        sql += " AND a.miembro_id=%s"
        params.append(miembro_id)
    sql += " ORDER BY a.fecha DESC, miembro_nombre"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)


@router.get("/actividades")
def listar_actividades(con = Depends(get_db)):
    sql = """
        SELECT actividad, fecha,
               COUNT(*) AS total,
               SUM(CASE WHEN presente THEN 1 ELSE 0 END) AS presentes
        FROM   asistencias
        GROUP  BY actividad, fecha
        ORDER  BY fecha DESC
    """
    with con.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        
    return [
        {
            "actividad": r["actividad"], 
            "fecha": r["fecha"], 
            "total": r["total"], 
            "presentes": r["presentes"] or 0
        }
        for r in rows
    ]


@router.post("/lote", status_code=201)
def registrar_asistencia_lote(
    body: AsistenciaLote,
    user: dict = Depends(require_jefe),
    con = Depends(get_db),
):
    try:
        with con.cursor() as cur:
            if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"] and user.get("seccion_id"):
                for r in body.registros:
                    cur.execute("SELECT seccion_id FROM miembros WHERE id=%s", [r["miembro_id"]])
                    m = cur.fetchone()
                    if m and m["seccion_id"] != user["seccion_id"]:
                        raise HTTPException(
                            403, "No puedes registrar asistencia de miembros de otra sección."
                        )

            cur.execute(
                "DELETE FROM asistencias WHERE actividad=%s AND fecha=%s",
                [body.actividad, body.fecha],
            )
            for r in body.registros:
                cur.execute(
                    "INSERT INTO asistencias VALUES (%s,%s,%s,%s,%s,%s)",
                    [uid(), r["miembro_id"], body.actividad, body.fecha,
                     bool(r.get("presente")), r.get("notas")],
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
    con = Depends(get_db),
):
    aid = uid()
    with con.cursor() as cur:
        cur.execute(
            "INSERT INTO asistencias VALUES (%s,%s,%s,%s,%s,%s)",
            [aid, body.miembro_id, body.actividad, body.fecha,
             body.presente, body.notas],
        )
    return {"id": aid}