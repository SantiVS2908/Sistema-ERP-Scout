from fastapi import APIRouter, Depends, HTTPException
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
    con = Depends(get_db),
):
    sql = """
        SELECT m.*, s.nombre AS seccion_nombre, s.color AS seccion_color
        FROM   miembros m
        LEFT JOIN secciones s ON m.seccion_id = s.id
        WHERE  1=1
    """
    params: list = []
    if seccion_id:
        sql += " AND m.seccion_id=%s"
        params.append(seccion_id)
    if activo is not None:
        sql += " AND m.activo=%s"
        params.append(activo)
    if tipo:
        sql += " AND m.tipo=%s"
        params.append(tipo)
    if q:
        like = f"%{q.lower()}%"
        sql += (" AND (LOWER(m.nombre) LIKE %s OR LOWER(m.apellido) LIKE %s "
                "OR LOWER(m.numero_scout) LIKE %s)")
        params += [like, like, like]
    sql += " ORDER BY m.apellido, m.nombre"
    
    with con.cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur)


@router.get("/{mid}")
def get_miembro(mid: str, con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("""
            SELECT m.*, s.nombre AS seccion_nombre, s.color AS seccion_color
            FROM   miembros m
            LEFT JOIN secciones s ON m.seccion_id = s.id
            WHERE  m.id=%s
        """, [mid])
        
        rows = rows_to_dicts(cur)
        if not rows:
            raise HTTPException(404, "Miembro no encontrado.")

        m = rows[0]
        
        cur.execute("SELECT * FROM equipo_bolsillo WHERE miembro_id=%s ORDER BY articulo", [mid])
        m["equipo"] = rows_to_dicts(cur)
        
        cur.execute("SELECT * FROM uniformes WHERE miembro_id=%s ORDER BY pieza", [mid])
        m["uniforme"] = rows_to_dicts(cur)
        
        cur.execute("SELECT * FROM registro_anual WHERE miembro_id=%s ORDER BY anio DESC", [mid])
        m["registro_anual"] = rows_to_dicts(cur)
        
        cur.execute("""
            SELECT t.*, so.nombre AS origen_nombre, sd.nombre AS destino_nombre
            FROM   transferencias t
            LEFT JOIN secciones so ON t.seccion_origen_id  = so.id
            LEFT JOIN secciones sd ON t.seccion_destino_id = sd.id
            WHERE  t.miembro_id=%s
            ORDER  BY t.fecha DESC
        """, [mid])
        m["transferencias"] = rows_to_dicts(cur)
        
    m["edad"] = calcular_edad(m.get("fecha_nacimiento"))
    return m


@router.post("", status_code=201)
def crear_miembro(
    body: MiembroIn, 
    user: dict = Depends(require_jefe),
    con = Depends(get_db)
):
    if body.tipo == "scouter":
        if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
            raise HTTPException(403, "Solo el Jefe de Grupo puede dar de alta a scouters.")
    else:
        if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
            if body.seccion_id and not can_manage_seccion(user, body.seccion_id):
                raise HTTPException(403, "Solo puedes agregar beneficiarios a tu propia sección.")

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

        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO miembros VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [mid, body.numero_scout, body.nombre, body.apellido,
                 body.tipo, body.fecha_nacimiento, cargo_final, body.seccion_id,
                 body.fecha_ingreso or today(), body.telefono, body.email,
                 body.direccion, body.nombre_tutor, body.telefono_emergencia,
                 body.grupo_sanguineo, body.alergias,
                 body.activo, body.notas, now()],
            )

            if body.tipo == "beneficiario":
                piezas_uniforme = [
                    "Camisa/Blusa", "Pañoleta", "Pantalón/Falda",
                    "Cinturón", "Zapatos", "Sombrero/Boina",
                ]
                for pieza in piezas_uniforme:
                    cur.execute(
                        "INSERT INTO uniformes VALUES (%s,%s,%s,false,NULL,'Pendiente',NULL)",
                        [uid(), mid, pieza],
                    )
                cur.execute(
                    "INSERT INTO registro_anual VALUES (%s,%s,%s,%s,NULL,NULL,NULL)",
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
    con = Depends(get_db),
):
    with con.cursor() as cur:
        if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
            cur.execute("SELECT seccion_id FROM miembros WHERE id=%s", [mid])
            m = cur.fetchone()
            if m and not can_manage_seccion(user, m["seccion_id"]):
                raise HTTPException(403, "No tienes permiso para editar miembros de otra sección.")
                
        cur.execute("""
            UPDATE miembros
            SET    numero_scout=%s, nombre=%s, apellido=%s, tipo=%s, fecha_nacimiento=%s, cargo=%s,
                   seccion_id=%s, fecha_ingreso=%s, telefono=%s, email=%s, direccion=%s,
                   nombre_tutor=%s, telefono_emergencia=%s, grupo_sanguineo=%s, alergias=%s,
                   activo=%s, notas=%s
            WHERE  id=%s
        """, [body.numero_scout, body.nombre, body.apellido, body.tipo,
              body.fecha_nacimiento, body.cargo, body.seccion_id,
              body.fecha_ingreso, body.telefono, body.email,
              body.direccion, body.nombre_tutor, body.telefono_emergencia,
              body.grupo_sanguineo, body.alergias,
              body.activo, body.notas, mid])
              
    return {"ok": True}


@router.delete("/{mid}")
def eliminar_miembro(
    mid: str, 
    user: dict = Depends(require_jefe),
    con = Depends(get_db)
):
    with con.cursor() as cur:
        if ROL_NIVEL.get(user["rol"], 0) < ROL_NIVEL["master"]:
            cur.execute("SELECT seccion_id FROM miembros WHERE id=%s", [mid])
            m = cur.fetchone()
            if m and not can_manage_seccion(user, m["seccion_id"]):
                raise HTTPException(403, "No tienes permiso para dar de baja a miembros de otra sección.")
                
        cur.execute("UPDATE miembros SET activo=false WHERE id=%s", [mid])
        
    return {"ok": True}