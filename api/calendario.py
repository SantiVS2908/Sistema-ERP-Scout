from fastapi import APIRouter, Depends, HTTPException
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

# Importamos log que faltaba
from security import require_jefe, log

@router.get("")
def listar_calendario(
    seccion: Optional[str] = None,
    desde:   Optional[str] = None,
    hasta:   Optional[str] = None,
    con = Depends(get_db),
):
    sql    = "SELECT * FROM actividades_grupo WHERE 1=1"
    params: list = []
    if seccion: 
        sql += " AND seccion=%s"
        params.append(seccion)
    if desde:   
        sql += " AND fecha>=%s"
        params.append(desde)
    if hasta:   
        sql += " AND fecha<=%s"
        params.append(hasta)
    sql += " ORDER BY fecha ASC, hora ASC"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)


@router.get("/proximas")
def proximas_actividades(
    seccion: Optional[str] = None,
    con = Depends(get_db),
):
    desde = today()
    hasta = date.fromordinal(date.today().toordinal() + 30).isoformat()
    sql    = "SELECT * FROM actividades_grupo WHERE fecha>=%s AND fecha<=%s"
    params: list = [desde, hasta]
    if seccion:
        sql += " AND seccion=%s"
        params.append(seccion)
    sql += " ORDER BY fecha ASC, hora ASC"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)


@router.get("/proximas_seccion")
def proximas_actividades_seccion(
    nombre: Optional[str] = None,
    limit:  int           = 3,
    con = Depends(get_db),
):
    hoy = today()
    with con.cursor() as cur:
        if nombre:
            cur.execute("""
                SELECT * FROM actividades_grupo
                WHERE  fecha >= %s
                  AND  (LOWER(seccion) = LOWER(%s) OR seccion = 'Todo el Grupo')
                ORDER  BY fecha ASC, hora ASC
                LIMIT  %s
            """, [hoy, nombre, limit])
        else:
            cur.execute("""
                SELECT * FROM actividades_grupo
                WHERE  fecha >= %s
                ORDER  BY fecha ASC, hora ASC
                LIMIT  %s
            """, [hoy, limit])
        return rows_to_dicts(cur)


@router.post("", status_code=201)
def crear_actividad(
    body: ActividadIn, 
    user: dict = Depends(require_jefe),
    con = Depends(get_db)
):
    aid = uid()
    with con.cursor() as cur:
        cur.execute(
            "INSERT INTO actividades_grupo VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
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
    con = Depends(get_db),
):
    with con.cursor() as cur:
        cur.execute(
            "UPDATE actividades_grupo SET titulo=%s, fecha=%s, hora=%s, descripcion=%s, "
            "lugar=%s, seccion=%s, color=%s WHERE id=%s",
            [body.titulo, body.fecha, body.hora, body.descripcion,
             body.lugar, body.seccion, body.color, aid],
        )
    return {"ok": True}


@router.delete("/{aid}")
def eliminar_actividad(
    aid: str, 
    user: dict = Depends(require_jefe),
    con = Depends(get_db)
):
    with con.cursor() as cur:
        cur.execute("DELETE FROM actividades_grupo WHERE id=%s", [aid])
    return {"ok": True}