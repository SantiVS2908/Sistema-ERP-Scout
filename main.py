"""
ScoutDB — Sistema de gestión para grupos Scout
Backend: FastAPI + SQLite (modo WAL, seguro para escrituras concurrentes)

Cambios vs. versión anterior (DuckDB):
  • Conexión por request, no global — thread-safe bajo carga.
  • PRAGMA journal_mode=WAL     → los lectores nunca bloquean escritores.
  • PRAGMA busy_timeout=30000   → si dos personas escriben a la vez, la
                                   segunda espera (hasta 30s) en vez de fallar.
  • PRAGMA foreign_keys=ON      → integridad referencial real.
  • Transacciones explícitas en operaciones multi-statement
    (transferencias, asistencia en lote, seed).
  • ILIKE → LOWER(…) LIKE …  (SQLite no tiene ILIKE).

Endpoints y respuestas JSON son IDÉNTICOS a la versión DuckDB:
no hay que tocar el frontend (index.html / app.html).
"""
import hashlib
import logging
import secrets
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from utils import get_db, open_db, rows_to_dicts, uid, now, today, calcular_edad, get_seccion_ocupacion, DB_PATH
from schemas import SeccionIn
from schemas import MiembroIn
from security import require_auth, require_jefe, require_master, require_dev, ROL_NIVEL, hash_password, DOMAIN, generate_username

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("scoutdb")

# ── Rutas portables (Windows / Linux / Mac) ───────────────────────────────
BASE_DIR   = Path(__file__).parent
DB_PATH    = str(BASE_DIR / "scout.db")
STATIC_DIR = BASE_DIR / "static"
IMAGES_DIR = STATIC_DIR / "images"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}

app = FastAPI(title="ScoutDB", version="3.0.0 (SQLite)")

# ══════════════════════════════════════════════════════════════════════════
# CONEXIÓN DE ROUTERS MODULARES 
# ══════════════════════════════════════════════════════════════════════════
from api.secciones import router as secciones_router
app.include_router(secciones_router)

from api.miembros import router as miembros_router
app.include_router(miembros_router)

from api.calendario import router as calendario_router
app.include_router(calendario_router)

from api.asistencias import router as asistencias_router
app.include_router(asistencias_router)

from api.usuarios import router as usuarios_router
app.include_router(usuarios_router)

from api.auth import router as auth_router
app.include_router(auth_router)

from api.administracion import router as administracion_router
app.include_router(administracion_router)



# ══════════════════════════════════════════════════════════════════════════
# ESQUEMA DE BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════
def init_db() -> None:
    """
    Inicializa la BD si no existe.
    Si existe scout_init.sql, restaura datos desde ahí.
    """
    db_exists = Path(DB_PATH).exists()
    
    with open_db() as con:
        # 1. Crear esquema (CREATE TABLE, índices, etc.)
        con.executescript("""
            CREATE TABLE IF NOT EXISTS secciones (
                id          TEXT PRIMARY KEY,
                nombre      TEXT NOT NULL,
                rama        TEXT,
                color       TEXT,
                capacidad   INTEGER NOT NULL DEFAULT 30,
                lider       TEXT,
                descripcion TEXT,
                activa      INTEGER DEFAULT 1,
                creada_en   TEXT
            );

            CREATE TABLE IF NOT EXISTS miembros (
                id                   TEXT PRIMARY KEY,
                numero_scout         TEXT,
                nombre               TEXT NOT NULL,
                apellido             TEXT NOT NULL,
                tipo                 TEXT NOT NULL DEFAULT 'beneficiario',
                fecha_nacimiento     TEXT,
                cargo                TEXT,
                seccion_id           TEXT,
                fecha_ingreso        TEXT,
                telefono             TEXT,
                email                TEXT,
                direccion            TEXT,
                nombre_tutor         TEXT,
                telefono_emergencia  TEXT,
                grupo_sanguineo      TEXT,
                alergias             TEXT,
                activo               INTEGER DEFAULT 1,
                notas                TEXT,
                creado_en            TEXT,
                FOREIGN KEY (seccion_id) REFERENCES secciones(id)
            );

            CREATE INDEX IF NOT EXISTS idx_miembros_seccion ON miembros(seccion_id);
            CREATE INDEX IF NOT EXISTS idx_miembros_activo  ON miembros(activo);
            CREATE INDEX IF NOT EXISTS idx_miembros_tipo    ON miembros(tipo);

            CREATE TABLE IF NOT EXISTS asistencias (
                id          TEXT PRIMARY KEY,
                miembro_id  TEXT NOT NULL,
                actividad   TEXT NOT NULL,
                fecha       TEXT NOT NULL,
                presente    INTEGER DEFAULT 0,
                notas       TEXT,
                FOREIGN KEY (miembro_id) REFERENCES miembros(id)
            );

            CREATE INDEX IF NOT EXISTS idx_asist_actividad_fecha
                ON asistencias(actividad, fecha);
            CREATE INDEX IF NOT EXISTS idx_asist_miembro ON asistencias(miembro_id);

            CREATE TABLE IF NOT EXISTS equipo_bolsillo (
                id                TEXT PRIMARY KEY,
                miembro_id        TEXT NOT NULL,
                articulo          TEXT NOT NULL,
                estado            TEXT DEFAULT 'Bueno',
                fecha_asignacion  TEXT,
                notas             TEXT,
                FOREIGN KEY (miembro_id) REFERENCES miembros(id)
            );

            CREATE INDEX IF NOT EXISTS idx_equipo_miembro ON equipo_bolsillo(miembro_id);

            CREATE TABLE IF NOT EXISTS uniformes (
                id          TEXT PRIMARY KEY,
                miembro_id  TEXT NOT NULL,
                pieza       TEXT NOT NULL,
                tiene       INTEGER DEFAULT 0,
                talla       TEXT,
                estado      TEXT DEFAULT 'Pendiente',
                notas       TEXT,
                FOREIGN KEY (miembro_id) REFERENCES miembros(id)
            );

            CREATE INDEX IF NOT EXISTS idx_uniformes_miembro ON uniformes(miembro_id);

            CREATE TABLE IF NOT EXISTS registro_anual (
                id            TEXT PRIMARY KEY,
                miembro_id    TEXT NOT NULL,
                anio          INTEGER NOT NULL,
                estado        TEXT DEFAULT 'Pendiente',
                fecha_pago    TEXT,
                monto         REAL,
                observaciones TEXT,
                FOREIGN KEY (miembro_id) REFERENCES miembros(id),
                UNIQUE (miembro_id, anio)
            );

            CREATE TABLE IF NOT EXISTS transferencias (
                id                 TEXT PRIMARY KEY,
                miembro_id         TEXT NOT NULL,
                seccion_origen_id  TEXT,
                seccion_destino_id TEXT NOT NULL,
                fecha              TEXT NOT NULL,
                motivo             TEXT,
                realizado_por      TEXT,
                notas              TEXT,
                FOREIGN KEY (miembro_id)         REFERENCES miembros(id),
                FOREIGN KEY (seccion_origen_id)  REFERENCES secciones(id),
                FOREIGN KEY (seccion_destino_id) REFERENCES secciones(id)
            );

            CREATE TABLE IF NOT EXISTS actividades_grupo (
                id          TEXT PRIMARY KEY,
                titulo      TEXT NOT NULL,
                fecha       TEXT NOT NULL,
                hora        TEXT,
                descripcion TEXT,
                lugar       TEXT,
                seccion     TEXT DEFAULT 'Todo el Grupo',
                color       TEXT DEFAULT '#2d6a4f',
                creada_en   TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_act_fecha ON actividades_grupo(fecha);

            CREATE TABLE IF NOT EXISTS usuarios (
                id                  TEXT PRIMARY KEY,
                email               TEXT UNIQUE NOT NULL,
                username            TEXT UNIQUE NOT NULL,
                nombre_completo     TEXT NOT NULL,
                password_hash       TEXT NOT NULL,
                salt                TEXT NOT NULL,
                password_temporal   TEXT,
                rol                 TEXT NOT NULL DEFAULT 'beneficiario',
                tipo                TEXT DEFAULT 'scouter',
                seccion_id          TEXT,
                miembro_id          TEXT,
                activo              INTEGER DEFAULT 1,
                debe_cambiar_pass   INTEGER DEFAULT 1,
                creado_en           TEXT,
                ultimo_login        TEXT,
                FOREIGN KEY (seccion_id) REFERENCES secciones(id)
            );

            CREATE INDEX IF NOT EXISTS idx_usuarios_email    ON usuarios(email);
            CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);

            CREATE TABLE IF NOT EXISTS sesiones (
                token       TEXT PRIMARY KEY,
                usuario_id  TEXT NOT NULL,
                creado_en   TEXT NOT NULL,
                expira_en   TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
        """)

        # 2. Restaurar datos desde scout_init.sql si existe y BD está vacía
        dump_file = BASE_DIR / "scout_init.sql"
        if dump_file.exists():
            n_secciones = con.execute(
                "SELECT COUNT(*) FROM secciones"
            ).fetchone()[0]
            
            if n_secciones == 0:  # BD vacía
                log.info("Restaurando datos desde %s", dump_file.name)
                try:
                    with open(dump_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                        con.executescript(sql_content)
                    log.info("✓ Datos restaurados correctamente.")
                except Exception as e:
                    log.warning("⚠ No se pudieron restaurar datos: %s", e)
            else:
                log.info("BD ya tiene datos (%d secciones). Omitiendo restauración.", n_secciones)
        else:
            log.info("scout_init.sql no encontrado. BD vacía, usa POST /api/seed para datos de ejemplo.")

    log.info("Base de datos inicializada (SQLite + WAL).")


init_db()



# ══════════════════════════════════════════════════════════════════════════
# GALERÍA DE IMÁGENES
# ══════════════════════════════════════════════════════════════════════════
@app.get("/api/imagenes/{carpeta}")
def listar_imagenes(carpeta: str):
    # Seguridad: sanitizar para evitar path traversal
    carpeta = carpeta.strip().lower().replace("..", "").replace("/", "").replace("\\", "")
    if not carpeta:
        raise HTTPException(status_code=400, detail="Carpeta inválida.")

    ruta = IMAGES_DIR / carpeta
    if not ruta.exists() or not ruta.is_dir():
        return {"carpeta": carpeta, "imagenes": []}

    imagenes = []
    for archivo in sorted(ruta.iterdir()):
        if archivo.is_file() and archivo.suffix.lower() in IMAGE_EXTENSIONS:
            imagenes.append({
                "nombre": archivo.stem.replace("-", " ").replace("_", " ").title(),
                "url":    f"/static/images/{carpeta}/{archivo.name}",
            })
    log.info("Galería '%s': %d imagen(es).", carpeta, len(imagenes))
    return {"carpeta": carpeta, "imagenes": imagenes}


@app.get("/api/images/{carpeta}")
def listar_imagenes_hero(carpeta: str):
    """Alias en inglés para el slideshow del hero."""
    return listar_imagenes(carpeta)


@app.get("/api/imagenes")
def listar_todas_carpetas():
    if not IMAGES_DIR.exists():
        return {"carpetas": []}
    carpetas = [
        {
            "carpeta": d.name,
            "total": sum(1 for f in d.iterdir()
                         if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS),
        }
        for d in sorted(IMAGES_DIR.iterdir()) if d.is_dir()
    ]
    return {"carpetas": carpetas}


# ══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════
@app.get("/api/dashboard")
def dashboard(con: sqlite3.Connection = Depends(get_db)):
    total_miembros  = con.execute("SELECT COUNT(*) FROM miembros  WHERE activo=1").fetchone()[0]
    total_secciones = con.execute("SELECT COUNT(*) FROM secciones WHERE activa=1").fetchone()[0]
    anio_actual      = date.today().year
    registrados_anio = con.execute(
        "SELECT COUNT(*) FROM registro_anual WHERE anio=? AND estado='Registrado'",
        [anio_actual],
    ).fetchone()[0]
    pendientes_reg   = con.execute(
        "SELECT COUNT(*) FROM registro_anual WHERE anio=? AND estado='Pendiente'",
        [anio_actual],
    ).fetchone()[0]
    primer_dia_mes   = f"{date.today().year}-{date.today().month:02d}-01"
    transferencias_mes = con.execute(
        "SELECT COUNT(*) FROM transferencias WHERE fecha >= ?",
        [primer_dia_mes],
    ).fetchone()[0]

    secciones = rows_to_dicts(con.execute(
        "SELECT id, nombre, color, capacidad FROM secciones "
        "WHERE activa=1 ORDER BY nombre"
    ))
    for s in secciones:
        # Ocupación = solo beneficiarios (los scouters no consumen cupo)
        occ = con.execute(
            "SELECT COUNT(*) FROM miembros WHERE seccion_id=? AND activo=1 AND tipo='beneficiario'",
            [s["id"]],
        ).fetchone()[0]
        s["ocupados"]    = occ
        s["disponibles"] = s["capacidad"] - occ
        # Para el tooltip: cuántos scouters hay en la sección
        s["scouters"] = con.execute(
            "SELECT COUNT(*) FROM miembros WHERE seccion_id=? AND activo=1 AND tipo='scouter'",
            [s["id"]],
        ).fetchone()[0]

    actividades = con.execute("""
        SELECT actividad, fecha,
               COUNT(*) AS total,
               SUM(CASE WHEN presente THEN 1 ELSE 0 END) AS presentes
        FROM   asistencias
        GROUP  BY actividad, fecha
        ORDER  BY fecha DESC
        LIMIT  5
    """).fetchall()

    return {
        "total_miembros":      total_miembros,
        "total_secciones":     total_secciones,
        "registrados_anio":    registrados_anio,
        "pendientes_registro": pendientes_reg,
        "transferencias_mes":  transferencias_mes,
        "secciones":           secciones,
        "ultimas_actividades": [
            {"actividad": r[0], "fecha": r[1], "total": r[2], "presentes": r[3] or 0}
            for r in actividades
        ],
    }






# ══════════════════════════════════════════════════════════════════════════
# SEED
# ══════════════════════════════════════════════════════════════════════════
@app.post("/api/seed")
def seed_data(con: sqlite3.Connection = Depends(get_db)): 
    import random
  

    existentes = con.execute("SELECT COUNT(*) FROM secciones").fetchone()[0]
    if existentes > 0:
        raise HTTPException(400, "Ya existen datos. Limpia la base antes de re-sembrar.")

    con.execute("BEGIN IMMEDIATE")
    try:
        secciones_seed = [
            (uid(), "Manada",    "Lobatos (7-10 años)", "#f4a261", 24, "Akela"),
            (uid(), "Tropa",     "Scouts (11-15 años)", "#2d6a4f", 32, "Scoutmaster"),
            (uid(), "Comunidad", "Caminantes (16-17)",  "#457b9d", 20, "Guía"),
            (uid(), "Clan",      "Rovers (18-21 años)", "#9b2226", 16, "Presidente"),
        ]
        for s in secciones_seed:
            con.execute(
                "INSERT INTO secciones VALUES (?,?,?,?,?,?,?,1,?)",
                [s[0], s[1], s[2], s[3], s[4], s[5], None, now()],
            )

        miembros_seed = [
            ("Carlos",    "Ramírez",   "2010-03-15", "Lobato",     0),
            ("Sofía",     "Mendoza",   "2009-07-22", "Lobato",     0),
            ("Miguel",    "Torres",    "2008-11-05", "Seis",       0),
            ("Ana",       "García",    "2011-02-18", "Lobato",     0),
            ("Luis",      "Hernández", "2007-09-30", "Scout",      1),
            ("Valentina", "López",     "2006-04-12", "Guía",       1),
            ("Eduardo",   "Martínez",  "2008-01-25", "Scout",      1),
            ("Camila",    "Rodríguez", "2005-12-08", "Sub-Guía",   1),
            ("Roberto",   "Sánchez",   "2006-06-14", "Scout",      1),
            ("Isabella",  "Flores",    "2005-08-20", "Patrullero", 1),
            ("Diego",     "Cruz",      "2004-03-02", "Caminante",  2),
            ("Mariana",   "Reyes",     "2003-10-17", "Caminante",  2),
            ("Javier",    "Morales",   "2002-05-28", "Rover",      3),
            ("Fernanda",  "Jiménez",   "2001-07-11", "Rover",      3),
        ]

        ids: list[str] = []
        for m in miembros_seed:
            mid        = uid()
            seccion_id = secciones_seed[m[4]][0]
            ids.append(mid)
            con.execute(
                "INSERT INTO miembros VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [mid, f"MX{100 + len(ids):04d}", m[0], m[1],
                 "beneficiario",          # tipo
                 m[2], m[3],              # fecha_nacimiento, cargo
                 seccion_id, "2023-02-01",
                 None, None, None,
                 f"Tutor de {m[0]}", None, None, None, 1, None, now()],
            )
            piezas = ["Camisa/Blusa", "Pañoleta", "Pantalón/Falda",
                      "Cinturón", "Zapatos", "Sombrero/Boina"]
            for pieza in piezas:
                tiene = random.random() > 0.3
                con.execute(
                    "INSERT INTO uniformes VALUES (?,?,?,?,?,?,?)",
                    [uid(), mid, pieza, 1 if tiene else 0,
                     "M" if tiene else None,
                     "Completo" if tiene else "Pendiente", None],
                )
            estado_reg = random.choice(["Registrado", "Registrado", "Pendiente"])
            con.execute(
                "INSERT INTO registro_anual VALUES (?,?,?,?,?,?,?)",
                [uid(), mid, date.today().year, estado_reg,
                 f"{date.today().year}-02-15" if estado_reg == "Registrado" else None,
                 350.0 if estado_reg == "Registrado" else None, None],
            )
            if m[4] >= 1:
                articulos = ["Brújula", "Navaja", "Botiquín", "Linterna", "Cantimplora"]
                for art in random.sample(articulos, random.randint(2, 4)):
                    con.execute(
                        "INSERT INTO equipo_bolsillo VALUES (?,?,?,?,?,?)",
                        [uid(), mid, art, random.choice(["Bueno", "Bueno", "Regular"]),
                         "2024-02-01", None],
                    )

        actividades_seed = [
            ("Reunión semanal",    "2025-03-08"),
            ("Caminata al cerro",  "2025-03-15"),
            ("Reunión semanal",    "2025-03-22"),
            ("Campamento mensual", "2025-03-29"),
            ("Reunión semanal",    "2025-04-05"),
        ]
        random.seed(42)
        for actividad, fecha in actividades_seed:
            for mid in ids:
                con.execute(
                    "INSERT INTO asistencias VALUES (?,?,?,?,?,?)",
                    [uid(), mid, actividad, fecha,
                     1 if random.random() > 0.25 else 0, None],
                )

        # ── Usuarios del sistema ──────────────────────────────────────────
        def _insert_user(nombre_completo, rol, tipo="scouter", seccion_id=None,
                         custom_pass=None, custom_username=None):
            uname = custom_username or generate_username(nombre_completo)
            email = f"{uname}@{DOMAIN}"
            temp  = custom_pass or uname
            salt  = secrets.token_hex(16)
            p_hash = hash_password(temp, salt)
            con.execute(
                """INSERT OR IGNORE INTO usuarios
                   (id,email,username,nombre_completo,password_hash,salt,
                    password_temporal,rol,tipo,seccion_id,activo,debe_cambiar_pass,creado_en)
                   VALUES (?,?,?,?,?,?,?,?,?,?,1,1,?)""",
                [uid(), email, uname, nombre_completo, p_hash, salt,
                 temp, rol, tipo, seccion_id, now()],
            )
            return {"email": email, "password_temporal": temp, "rol": rol, "username": uname}

        # Cuenta dev (username simple y memorable)
        dev_info    = _insert_user("Dev Admin",   "dev",    custom_pass="dev@Scout2024!",    custom_username="dev")
        # Cuenta master (jefe de grupo)
        master_info = _insert_user("Jefe Grupo",  "master", custom_pass="master@Scout2024!", custom_username="master")

        # 5 jefes de sección de prueba (uno por sección + un subjefe)
        jefes_prueba = [
            ("Pedro Flores Ramos",         "jefe_seccion",    secciones_seed[0][0]),  # Manada
            ("Laura Torres García",        "jefe_seccion",    secciones_seed[1][0]),  # Tropa
            ("Carlos Mendoza Silva",       "jefe_seccion",    secciones_seed[2][0]),  # Comunidad
            ("Sofía Reyes Cruz",           "jefe_seccion",    secciones_seed[3][0]),  # Clan
            ("Miguel Vázquez Luna",        "subjefe_seccion", secciones_seed[1][0]),  # SubJefe Tropa
        ]
        jefes_creados = []
        for nombre, rol, sec_id in jefes_prueba:
            info = _insert_user(nombre, rol, seccion_id=sec_id)
            info["nombre"] = nombre
            info["seccion"] = next(s[1] for s in secciones_seed if s[0] == sec_id)
            jefes_creados.append(info)

    except Exception:
        con.rollback()
        raise

    log.info("Seed: %d secciones, %d miembros.", len(secciones_seed), len(miembros_seed))
    return {
        "ok": True,
        "secciones": len(secciones_seed),
        "miembros":  len(miembros_seed),
        "usuarios_creados": [
            {"nombre": j["nombre"], "email": j["email"],
             "password_temporal": j["password_temporal"], "seccion": j["seccion"]}
            for j in jefes_creados
        ],
        "cuentas_sistema": [
            {"rol": "dev",    "nombre": "Dev Admin",  "email": dev_info["email"],    "password_temporal": dev_info["password_temporal"]},
            {"rol": "master", "nombre": "Jefe Grupo", "email": master_info["email"], "password_temporal": master_info["password_temporal"]},
        ],
    }

# ══════════════════════════════════════════════════════════════════════════
# BIBLIOTECA
# ══════════════════════════════════════════════════════════════════════════
BIBLIOTECA_DIR = STATIC_DIR / "biblioteca"

@app.get("/api/biblioteca/{rama}")
def listar_biblioteca(rama: str):
    rama = rama.strip().lower().replace("..", "").replace("/", "").replace("\\", "")
    if not rama:
        raise HTTPException(status_code=400, detail="Rama inválida.")
    
    if rama == "formatos":
        ruta = BIBLIOTECA_DIR / "formatos"
    else:
        ruta = BIBLIOTECA_DIR / "acervo" / rama
    
    if not ruta.exists() or not ruta.is_dir():
        return {"rama": rama, "documentos": []}
    
    documentos = []
    for archivo in sorted(ruta.iterdir()):
        if archivo.is_file() and archivo.suffix.lower() == ".pdf":
            # Nombre legible: guiones/guiones_bajos → espacios, Title Case
            nombre = archivo.stem.replace("-", " ").replace("_", " ").title()
            if rama == "formatos":
                url = f"/static/biblioteca/formatos/{archivo.name}"
            else:
                url = f"/static/biblioteca/acervo/{rama}/{archivo.name}"
            documentos.append({
                "nombre": nombre,
                "archivo": archivo.name,
                "url": url,
            })
    return {"rama": rama, "documentos": documentos}

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/intranet")
def intranet():
    return FileResponse(str(STATIC_DIR / "app.html"))

@app.get("/biblioteca")
def biblioteca():
    return FileResponse(str(STATIC_DIR / "biblioteca.html"))

@app.get("/{path:path}")
def spa_fallback(path: str):
    if path.startswith("intranet"):
        return FileResponse(str(STATIC_DIR / "app.html"))
    if path.startswith("biblioteca"):
        return FileResponse(str(STATIC_DIR / "biblioteca.html"))
    # Para rutas estáticas reales (imágenes, etc.)
    full_path = STATIC_DIR / path
    if full_path.exists():
        return FileResponse(str(full_path))
    return FileResponse(str(STATIC_DIR / "index.html"))

#@app.get("/{path:path}")
#def catch_all(path: str):
#    if path.startswith("static/") or path.startswith("api/"):
#        raise HTTPException(status_code=404)
#    if path.startswith("intranet"):
#        return FileResponse(str(STATIC_DIR / "app.html"))
#    return FileResponse(str(STATIC_DIR / "index.html"))
# 
