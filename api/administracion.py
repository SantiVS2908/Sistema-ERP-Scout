from fastapi import APIRouter, Depends, HTTPException
import sqlite3
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
def transferir_miembro(body: TransferenciaIn, user: dict = Depends(require_master), con: sqlite3.Connection = Depends(get_db)):
    con.execute("BEGIN IMMEDIATE")
    try:
        cur = con.execute("SELECT * FROM miembros WHERE id=? AND activo=1", [body.miembro_id])
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Miembro no encontrado o inactivo.")
        m_dict = dict(row)
        origen_id = m_dict["seccion_id"]

        if origen_id == body.seccion_destino_id:
            raise HTTPException(400, "El miembro ya pertenece a esa sección.")

        occ = get_seccion_ocupacion(con, body.seccion_destino_id)
        if occ["disponibles"] <= 0:
            destino = con.execute("SELECT nombre FROM secciones WHERE id=?", [body.seccion_destino_id]).fetchone()
            nombre = destino[0] if destino else "destino"
            raise HTTPException(400, f"La sección '{nombre}' está llena ({occ['ocupados']}/{occ['capacidad']}). Sin espacio disponible.")

        tid = uid()
        con.execute("INSERT INTO transferencias VALUES (?,?,?,?,?,?,?,?)",
                    [tid, body.miembro_id, origen_id, body.seccion_destino_id, today(), body.motivo, body.realizado_por, body.notas])
        con.execute("UPDATE miembros SET seccion_id=? WHERE id=?", [body.seccion_destino_id, body.miembro_id])

        origen_nombre_row = con.execute("SELECT nombre FROM secciones WHERE id=?", [origen_id]).fetchone() if origen_id else None
        destino_nombre_row = con.execute("SELECT nombre FROM secciones WHERE id=?", [body.seccion_destino_id]).fetchone()
        nuevo_espacio = get_seccion_ocupacion(con, origen_id) if origen_id else None
    except Exception:
        con.rollback()
        raise

    log.info("Transferencia: %s %s → %s", m_dict["nombre"], m_dict["apellido"], destino_nombre_row[0] if destino_nombre_row else "?")
    return {
        "ok": True,
        "transferencia_id": tid,
        "miembro": f"{m_dict['nombre']} {m_dict['apellido']}",
        "desde": origen_nombre_row[0] if origen_nombre_row else "Sin sección",
        "hacia": destino_nombre_row[0] if destino_nombre_row else "?",
        "disponibles_origen": nuevo_espacio["disponibles"] if nuevo_espacio else None,
    }

@router.get("/transferencias")
def listar_transferencias(miembro_id: Optional[str] = None, con: sqlite3.Connection = Depends(get_db)):
    sql = """
        SELECT t.*, m.nombre || ' ' || m.apellido AS miembro_nombre, so.nombre AS origen_nombre, sd.nombre AS destino_nombre
        FROM   transferencias t
        LEFT JOIN miembros  m  ON t.miembro_id         = m.id
        LEFT JOIN secciones so ON t.seccion_origen_id  = so.id
        LEFT JOIN secciones sd ON t.seccion_destino_id = sd.id
    """
    params: list = []
    if miembro_id:
        sql += " WHERE t.miembro_id=?"; params.append(miembro_id)
    sql += " ORDER BY t.fecha DESC"
    return rows_to_dicts(con.execute(sql, params))

# ══════════════════════════════════════════════════════════════════════════
# EQUIPO DE BOLSILLO
# ══════════════════════════════════════════════════════════════════════════

@router.get("/equipo")
def listar_equipo(miembro_id: Optional[str] = None, con: sqlite3.Connection = Depends(get_db)):
    sql = """
        SELECT e.*, m.nombre || ' ' || m.apellido AS miembro_nombre
        FROM   equipo_bolsillo e
        JOIN   miembros m ON e.miembro_id = m.id
        WHERE  1=1
    """
    params: list = []
    if miembro_id:
        sql += " AND e.miembro_id=?"; params.append(miembro_id)
    sql += " ORDER BY m.apellido, e.articulo"
    return rows_to_dicts(con.execute(sql, params))

@router.post("/equipo", status_code=201)
def agregar_equipo(body: EquipoIn, con: sqlite3.Connection = Depends(get_db)):
    eid = uid()
    con.execute("INSERT INTO equipo_bolsillo VALUES (?,?,?,?,?,?)", [eid, body.miembro_id, body.articulo, body.estado, body.fecha_asignacion or today(), body.notas])
    return {"id": eid}

@router.put("/equipo/{eid}")
def actualizar_equipo(eid: str, body: EquipoIn, con: sqlite3.Connection = Depends(get_db)):
    con.execute("UPDATE equipo_bolsillo SET articulo=?, estado=?, fecha_asignacion=?, notas=? WHERE id=?", [body.articulo, body.estado, body.fecha_asignacion, body.notas, eid])
    return {"ok": True}

@router.delete("/api/equipo/{eid}")
def eliminar_equipo(eid: str, con: sqlite3.Connection = Depends(get_db)):
    con.execute("DELETE FROM equipo_bolsillo WHERE id=?", [eid])
    return {"ok": True}

# ══════════════════════════════════════════════════════════════════════════
# UNIFORMES
# ══════════════════════════════════════════════════════════════════════════

@router.get("/uniformes")
def listar_uniformes(miembro_id: Optional[str] = None, con: sqlite3.Connection = Depends(get_db)):
    sql = """
        SELECT u.*, m.nombre || ' ' || m.apellido AS miembro_nombre
        FROM   uniformes u
        JOIN   miembros  m ON u.miembro_id = m.id
        WHERE  1=1
    """
    params: list = []
    if miembro_id:
        sql += " AND u.miembro_id=?"; params.append(miembro_id)
    sql += " ORDER BY m.apellido, u.pieza"
    return rows_to_dicts(con.execute(sql, params))

@router.put("/uniformes/{uid_}")
def actualizar_uniforme(uid_: str, body: UniformeIn, con: sqlite3.Connection = Depends(get_db)):
    con.execute("UPDATE uniformes SET tiene=?, talla=?, estado=?, notas=? WHERE id=?", [1 if body.tiene else 0, body.talla, body.estado, body.notas, uid_])
    return {"ok": True}

# ══════════════════════════════════════════════════════════════════════════
# REGISTRO ANUAL
# ══════════════════════════════════════════════════════════════════════════

@router.get("/registro-anual")
def listar_registro(anio: Optional[int] = None, seccion_id: Optional[str] = None, estado: Optional[str] = None, con: sqlite3.Connection = Depends(get_db)):
    sql = """
        SELECT ra.*, m.nombre || ' ' || m.apellido AS miembro_nombre, m.seccion_id, s.nombre AS seccion_nombre
        FROM   registro_anual ra
        JOIN   miembros       m ON ra.miembro_id = m.id
        LEFT JOIN secciones   s ON m.seccion_id  = s.id
        WHERE  m.activo=1
    """
    params: list = []
    if anio:       sql += " AND ra.anio=?";      params.append(anio)
    if seccion_id: sql += " AND m.seccion_id=?"; params.append(seccion_id)
    if estado:     sql += " AND ra.estado=?";    params.append(estado)
    sql += " ORDER BY m.apellido"
    return rows_to_dicts(con.execute(sql, params))

@router.put("/registro-anual/{rid}")
def actualizar_registro(rid: str, body: RegistroAnualIn, con: sqlite3.Connection = Depends(get_db)):
    con.execute("UPDATE registro_anual SET estado=?, fecha_pago=?, monto=?, observaciones=? WHERE id=?", [body.estado, body.fecha_pago, body.monto, body.observaciones, rid])
    return {"ok": True}

@router.post("/registro-anual", status_code=201)
def crear_registro(body: RegistroAnualIn, con: sqlite3.Connection = Depends(get_db)):
    existe = con.execute("SELECT id FROM registro_anual WHERE miembro_id=? AND anio=?", [body.miembro_id, body.anio]).fetchone()
    if existe:
        raise HTTPException(400, "Ya existe un registro para este miembro y año.")
    rid = uid()
    con.execute("INSERT INTO registro_anual VALUES (?,?,?,?,?,?,?)", [rid, body.miembro_id, body.anio, body.estado, body.fecha_pago, body.monto, body.observaciones])
    return {"id": rid}