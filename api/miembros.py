from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from typing import Optional
from datetime import date

router = APIRouter(
    prefix="/api/miembros",
    tags=["Miembros"]
)

# Helpers limpios de nuestra caja de herramientas central
from utils import get_db, rows_to_dicts, calcular_edad, get_seccion_ocupacion, uid, today, now

# Esquema de validación
from schemas import MiembroIn

from security import require_jefe, ROL_NIVEL, can_manage_seccion, determinar_rol_scouter, crear_cuenta_scouter
from main import log  # El log sí se puede quedar de main por ahora

@router.get("")
def listar_miembros(
    seccion_id: Optional[str]  = None,
    activo:     Optional[bool] = None,
    tipo:       Optional[str]  = None,
    q:          Optional[str]  = None,
    con: sqlite3.Connection = Depends(get_db),
):
    sql = """
        SELECT m.*, s.nombre AS seccion_nombre, s.color AS seccion_color
        FROM   miembros m
        LEFT JOIN secciones s ON m.seccion_id = s.id
        WHERE  1=1
    """
    params: list = []
    if seccion_id:
        sql += " AND m.seccion_id=?";    params.append(seccion_id)
    if activo is not None:
        sql += " AND m.activo=?";        params.append(1 if activo else 0)
    if tipo:
        sql += " AND m.tipo=?";          params.append(tipo)
    if q:
        like = f"%{q.lower()}%"
        sql += (" AND (LOWER(m.nombre) LIKE ? OR LOWER(m.apellido) LIKE ? "
                "OR LOWER(m.numero_scout) LIKE ?)")
        params += [like, like, like]
    sql += " ORDER BY m.apellido, m.nombre"
    return rows_to_dicts(con.execute(sql, params))


@router.get("/{mid}")
def get_miembro(mid: str, con: sqlite3.Connection = Depends(get_db)):
    rows = rows_to_dicts(con.execute("""
        SELECT m.*, s.nombre AS seccion_nombre, s.color AS seccion_color
        FROM   miembros m
        LEFT JOIN secciones s ON m.seccion_id = s.id
        WHERE  m.id=?
    """, [mid]))
    if not rows:
        raise HTTPException(404, "Miembro no encontrado.")

    m = rows[0]
    m["equipo"] = rows_to_dicts(con.execute(
        "SELECT * FROM equipo_bolsillo WHERE miembro_id=? ORDER BY articulo", [mid]
    ))
    m["uniforme"] = rows_to_dicts(con.execute(
        "SELECT * FROM uniformes WHERE miembro_id=? ORDER BY pieza", [mid]
    ))
    m["registro_anual"] = rows_to_dicts(con.execute(
        "SELECT * FROM registro_anual WHERE miembro_id=? ORDER BY anio DESC", [mid]
    ))
    m["transferencias"] = rows_to_dicts(con.execute("""
        SELECT t.*, so.nombre AS origen_nombre, sd.nombre AS destino_nombre
        FROM   transferencias t
        LEFT JOIN secciones so ON t.seccion_origen_id  = so.id
        LEFT JOIN secciones sd ON t.seccion_destino_id = sd.id
        WHERE  t.miembro_id=?
        ORDER  BY t.fecha DESC
    """, [mid]))
    m["edad"] = calcular_edad(m.get("fecha_nacimiento"))
    return m


@router.post("", status_code=201)
def crear_miembro(body: MiembroIn, user: dict = Depends(require_jefe),
                  con: sqlite3.Connection = Depends(get_db)):
    if body.tipo == "scouter":
        if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
            raise HTTPException(403, "Solo el Jefe de Grupo puede dar de alta a scouters.")
    else:
        if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
            if body.seccion_id and not can_manage_seccion(user, body.seccion_id):
                raise HTTPException(403, "Solo puedes agregar beneficiarios a tu propia sección.")

    con.execute("BEGIN IMMEDIATE")
    try:
        if body.tipo == "beneficiario" and body.seccion_id:
            occ = get_seccion_ocupacion(con, body.seccion_id)
            if occ["disponibles"] <= 0:
                raise HTTPException(400, "La sección está llena. No hay espacios disponibles.")

        mid = uid()
        cargo_final = body.cargo
        if body.tipo == "scouter" and not cargo_final:
            rol_auto = determinar_rol_scouter(con, body.seccion_id)
            cargo_final = {
                "jefe_seccion":    "Jefe de Sección",
                "subjefe_seccion": "Sub-Jefe de Sección",
                "colaborador":     "Colaborador",
            }.get(rol_auto, "Scouter")

        con.execute(
            "INSERT INTO miembros VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [mid, body.numero_scout, body.nombre, body.apellido,
             body.tipo, body.fecha_nacimiento, cargo_final, body.seccion_id,
             body.fecha_ingreso or today(), body.telefono, body.email,
             body.direccion, body.nombre_tutor, body.telefono_emergencia,
             body.grupo_sanguineo, body.alergias,
             1 if body.activo else 0, body.notas, now()],
        )

        if body.tipo == "beneficiario":
            piezas_uniforme = [
                "Camisa/Blusa", "Pañoleta", "Pantalón/Falda",
                "Cinturón", "Zapatos", "Sombrero/Boina",
            ]
            for pieza in piezas_uniforme:
                con.execute(
                    "INSERT INTO uniformes VALUES (?,?,?,0,NULL,'Pendiente',NULL)",
                    [uid(), mid, pieza],
                )
            con.execute(
                "INSERT INTO registro_anual VALUES (?,?,?,?,NULL,NULL,NULL)",
                [uid(), mid, date.today().year, "Pendiente"],
            )

        credenciales = None
        if body.tipo == "scouter":
            credenciales = crear_cuenta_scouter(con, body.nombre, body.apellido, body.seccion_id, mid)

    except Exception:
        con.rollback()
        raise

    log.info("Miembro creado: %s %s (%s | %s)", body.nombre, body.apellido, body.tipo, mid)
    response = {"id": mid, "tipo": body.tipo}
    if credenciales:
        response["credenciales"] = credenciales
    return response


@router.put("/{mid}")
def actualizar_miembro(
    mid: str,
    body: MiembroIn,
    user: dict = Depends(require_jefe),
    con: sqlite3.Connection = Depends(get_db),
):
    if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
        m = con.execute("SELECT seccion_id FROM miembros WHERE id=?", [mid]).fetchone()
        if m and not can_manage_seccion(user, m["seccion_id"]):
            raise HTTPException(403, "No tienes permiso para editar miembros de otra sección.")
    con.execute("""
        UPDATE miembros
        SET    numero_scout=?, nombre=?, apellido=?, tipo=?, fecha_nacimiento=?, cargo=?,
               seccion_id=?, fecha_ingreso=?, telefono=?, email=?, direccion=?,
               nombre_tutor=?, telefono_emergencia=?, grupo_sanguineo=?, alergias=?,
               activo=?, notas=?
        WHERE  id=?
    """, [body.numero_scout, body.nombre, body.apellido, body.tipo,
          body.fecha_nacimiento, body.cargo, body.seccion_id,
          body.fecha_ingreso, body.telefono, body.email,
          body.direccion, body.nombre_tutor, body.telefono_emergencia,
          body.grupo_sanguineo, body.alergias,
          1 if body.activo else 0, body.notas, mid])
    return {"ok": True}


@router.delete("/{mid}")
def eliminar_miembro(mid: str, user: dict = Depends(require_jefe),
                     con: sqlite3.Connection = Depends(get_db)):
    if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
        m = con.execute("SELECT seccion_id FROM miembros WHERE id=?", [mid]).fetchone()
        if m and not can_manage_seccion(user, m["seccion_id"]):
            raise HTTPException(403, "No tienes permiso para dar de baja a miembros de otra sección.")
    con.execute("UPDATE miembros SET activo=0 WHERE id=?", [mid])
    return {"ok": True}