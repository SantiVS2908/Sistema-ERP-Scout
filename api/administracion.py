from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import date

router = APIRouter(
    prefix="/api",
    tags=["Administración Interna"]
)

# Herramientas globales
from utils import get_db, open_db, rows_to_dicts, uid, now, today, get_seccion_ocupacion

# Escudos de validación
from schemas import TransferenciaIn, EquipoIn, UniformeIn, RegistroAnualIn

# Seguridad compartida y logging
from security import require_master, log

# ══════════════════════════════════════════════════════════════════════════
# TRANSFERENCIAS
# ══════════════════════════════════════════════════════════════════════════

@router.post("/transferencias", status_code=201)
def transferir_miembro(body: TransferenciaIn, user: dict = Depends(require_master), con = Depends(get_db)):
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM miembros WHERE id=%s AND activo=true", [body.miembro_id])
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(404, "Miembro no encontrado o inactivo.")
            
            origen_id = row["seccion_id"]

            if origen_id == body.seccion_destino_id:
                raise HTTPException(400, "El miembro ya pertenece a esa sección.")

            occ = get_seccion_ocupacion(con, body.seccion_destino_id)
            if occ["disponibles"] <= 0:
                cur.execute("SELECT nombre FROM secciones WHERE id=%s", [body.seccion_destino_id])
                destino = cur.fetchone()
                nombre = destino["nombre"] if destino else "destino"
                raise HTTPException(400, f"La sección '{nombre}' está llena ({occ['ocupados']}/{occ['capacidad']}). Sin espacio disponible.")

            tid = uid()
            cur.execute("INSERT INTO transferencias VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        [tid, body.miembro_id, origen_id, body.seccion_destino_id, today(), body.motivo, body.realizado_por, body.notas])
            cur.execute("UPDATE miembros SET seccion_id=%s WHERE id=%s", [body.seccion_destino_id, body.miembro_id])

            if origen_id:
                cur.execute("SELECT nombre FROM secciones WHERE id=%s", [origen_id])
                origen_nombre_row = cur.fetchone()
            else:
                origen_nombre_row = None

            cur.execute("SELECT nombre FROM secciones WHERE id=%s", [body.seccion_destino_id])
            destino_nombre_row = cur.fetchone()
            nuevo_espacio = get_seccion_ocupacion(con, origen_id) if origen_id else None
            
            nombre_completo = f"{row['nombre']} {row['apellido']}"
            origen_nombre = origen_nombre_row["nombre"] if origen_nombre_row else "Sin sección"
            destino_nombre = destino_nombre_row["nombre"] if destino_nombre_row else "?"

    except Exception:
        con.rollback()
        raise

    log.info("Transferencia: %s → %s", nombre_completo, destino_nombre)
    return {
        "ok": True,
        "transferencia_id": tid,
        "miembro": nombre_completo,
        "desde": origen_nombre,
        "hacia": destino_nombre,
        "disponibles_origen": nuevo_espacio["disponibles"] if nuevo_espacio else None,
    }

@router.get("/transferencias")
def listar_transferencias(miembro_id: Optional[str] = None, con = Depends(get_db)):
    sql = """
        SELECT t.*, m.nombre || ' ' || m.apellido AS miembro_nombre, so.nombre AS origen_nombre, sd.nombre AS destino_nombre
        FROM   transferencias t
        LEFT JOIN miembros  m  ON t.miembro_id         = m.id
        LEFT JOIN secciones so ON t.seccion_origen_id  = so.id
        LEFT JOIN secciones sd ON t.seccion_destino_id = sd.id
    """
    params: list = []
    if miembro_id:
        sql += " WHERE t.miembro_id=%s"
        params.append(miembro_id)
    sql += " ORDER BY t.fecha DESC"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)

# ══════════════════════════════════════════════════════════════════════════
# EQUIPO DE BOLSILLO
# ══════════════════════════════════════════════════════════════════════════

@router.get("/equipo")
def listar_equipo(miembro_id: Optional[str] = None, con = Depends(get_db)):
    sql = """
        SELECT e.*, m.nombre || ' ' || m.apellido AS miembro_nombre
        FROM   equipo_bolsillo e
        JOIN   miembros m ON e.miembro_id = m.id
        WHERE  1=1
    """
    params: list = []
    if miembro_id:
        sql += " AND e.miembro_id=%s"
        params.append(miembro_id)
    sql += " ORDER BY m.apellido, e.articulo"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)

@router.post("/equipo", status_code=201)
def agregar_equipo(body: EquipoIn, con = Depends(get_db)):
    eid = uid()
    with con.cursor() as cur:
        cur.execute("INSERT INTO equipo_bolsillo VALUES (%s,%s,%s,%s,%s,%s)", 
                    [eid, body.miembro_id, body.articulo, body.estado, body.fecha_asignacion or today(), body.notas])
    return {"id": eid}

@router.put("/equipo/{eid}")
def actualizar_equipo(eid: str, body: EquipoIn, con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("UPDATE equipo_bolsillo SET articulo=%s, estado=%s, fecha_asignacion=%s, notas=%s WHERE id=%s", 
                    [body.articulo, body.estado, body.fecha_asignacion, body.notas, eid])
    return {"ok": True}

@router.delete("/equipo/{eid}")
def eliminar_equipo(eid: str, con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("DELETE FROM equipo_bolsillo WHERE id=%s", [eid])
    return {"ok": True}

# ══════════════════════════════════════════════════════════════════════════
# UNIFORMES
# ══════════════════════════════════════════════════════════════════════════

@router.get("/uniformes")
def listar_uniformes(miembro_id: Optional[str] = None, con = Depends(get_db)):
    sql = """
        SELECT u.*, m.nombre || ' ' || m.apellido AS miembro_nombre
        FROM   uniformes u
        JOIN   miembros  m ON u.miembro_id = m.id
        WHERE  1=1
    """
    params: list = []
    if miembro_id:
        sql += " AND u.miembro_id=%s"
        params.append(miembro_id)
    sql += " ORDER BY m.apellido, u.pieza"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)

@router.put("/uniformes/{uid_}")
def actualizar_uniforme(uid_: str, body: UniformeIn, con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("UPDATE uniformes SET tiene=%s, talla=%s, estado=%s, notas=%s WHERE id=%s", 
                    [body.tiene, body.talla, body.estado, body.notas, uid_])
    return {"ok": True}

# ══════════════════════════════════════════════════════════════════════════
# REGISTRO ANUAL
# ══════════════════════════════════════════════════════════════════════════

@router.get("/registro-anual")
def listar_registro(anio: Optional[int] = None, seccion_id: Optional[str] = None, estado: Optional[str] = None, con = Depends(get_db)):
    sql = """
        SELECT ra.*, m.nombre || ' ' || m.apellido AS miembro_nombre, m.seccion_id, s.nombre AS seccion_nombre
        FROM   registro_anual ra
        JOIN   miembros       m ON ra.miembro_id = m.id
        LEFT JOIN secciones   s ON m.seccion_id  = s.id
        WHERE  m.activo=true
    """
    params: list = []
    if anio:       
        sql += " AND ra.anio=%s"
        params.append(anio)
    if seccion_id: 
        sql += " AND m.seccion_id=%s"
        params.append(seccion_id)
    if estado:     
        sql += " AND ra.estado=%s"
        params.append(estado)
    sql += " ORDER BY m.apellido"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)

@router.put("/registro-anual/{rid}")
def actualizar_registro(rid: str, body: RegistroAnualIn, con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("UPDATE registro_anual SET estado=%s, fecha_pago=%s, monto=%s, observaciones=%s WHERE id=%s", 
                    [body.estado, body.fecha_pago, body.monto, body.observaciones, rid])
    return {"ok": True}

@router.post("/registro-anual", status_code=201)
def crear_registro(body: RegistroAnualIn, con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("SELECT id FROM registro_anual WHERE miembro_id=%s AND anio=%s", [body.miembro_id, body.anio])
        existe = cur.fetchone()
        
        if existe:
            raise HTTPException(400, "Ya existe un registro para este miembro y año.")
        
        rid = uid()
        cur.execute("INSERT INTO registro_anual VALUES (%s,%s,%s,%s,%s,%s,%s)", 
                    [rid, body.miembro_id, body.anio, body.estado, body.fecha_pago, body.monto, body.observaciones])
    return {"id": rid}