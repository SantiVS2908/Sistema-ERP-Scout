from fastapi import APIRouter, Depends, HTTPException

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
def listar_secciones(con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("SELECT * FROM secciones WHERE activa=true ORDER BY nombre")
        secciones = rows_to_dicts(cur)
        
        for s in secciones:
            occ = get_seccion_ocupacion(con, s["id"])
            s["ocupados"]    = occ["ocupados"]
            s["disponibles"] = occ["disponibles"]
            
            # Jefe asignado a esta sección
            cur.execute("""
                SELECT u.id, u.nombre_completo, u.email
                FROM   usuarios u
                WHERE  u.seccion_id=%s AND u.rol='jefe_seccion' AND u.activo=true
                LIMIT 1
            """, [s["id"]])
            jefe = cur.fetchone()
            s["jefe_id"]     = jefe["id"]              if jefe else None
            s["jefe_nombre"] = jefe["nombre_completo"] if jefe else None
            
            # Número de scouters en la sección (Nota el 'AS count')
            cur.execute(
                "SELECT COUNT(*) as count FROM miembros WHERE seccion_id=%s AND tipo='scouter' AND activo=true",
                [s["id"]]
            )
            s["scouters"] = cur.fetchone()["count"]
            
    return secciones


@router.get("/{sid}")
def get_seccion(sid: str, con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("SELECT * FROM secciones WHERE id=%s", [sid])
        rows = rows_to_dicts(cur)
        
    if not rows:
        raise HTTPException(404, "Sección no encontrada.")
    s = rows[0]
    s.update(get_seccion_ocupacion(con, sid))
    return s


@router.post("", status_code=201)
def crear_seccion(
    body: SeccionIn, 
    user: dict = Depends(require_master),
    con = Depends(get_db)
):
    sid = uid()
    with con.cursor() as cur:
        cur.execute(
            "INSERT INTO secciones VALUES (%s,%s,%s,%s,%s,%s,%s,true,%s)",
            [sid, body.nombre, body.rama, body.color, body.capacidad,
             body.lider, body.descripcion, now()],
        )
    return {"id": sid, "nombre": body.nombre}


@router.put("/{sid}")
def actualizar_seccion(
    sid: str,
    body: SeccionIn,
    user: dict = Depends(require_master),
    con = Depends(get_db),
):
    with con.cursor() as cur:
        cur.execute(
            "UPDATE secciones SET nombre=%s, rama=%s, color=%s, capacidad=%s, "
            "lider=%s, descripcion=%s WHERE id=%s",
            [body.nombre, body.rama, body.color, body.capacidad,
             body.lider, body.descripcion, sid],
        )
    return {"ok": True}


@router.delete("/{sid}")
def eliminar_seccion(
    sid: str, 
    user: dict = Depends(require_master),
    con = Depends(get_db)
):
    with con.cursor() as cur:
        # Nota el 'AS count' para poder extraer el número del diccionario
        cur.execute(
            "SELECT COUNT(*) as count FROM miembros WHERE seccion_id=%s AND activo=true", [sid]
        )
        miembros_activos = cur.fetchone()["count"]
        
        if miembros_activos > 0:
            raise HTTPException(
                400,
                f"La sección tiene {miembros_activos} miembro(s) activo(s). "
                "Transfiérelos antes de eliminar.",
            )
        cur.execute("UPDATE secciones SET activa=false WHERE id=%s", [sid])
        
    return {"ok": True}