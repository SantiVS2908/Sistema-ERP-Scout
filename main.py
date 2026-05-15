import logging
import secrets
import os
from pathlib import Path
from typing import Optional
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware # ← IMPORTANTE PARA PRODUCCIÓN
from utils import get_db, open_db, rows_to_dicts, uid, now, today, calcular_edad, get_seccion_ocupacion

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("scoutdb")

# ── Rutas ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
IMAGES_DIR = STATIC_DIR / "images"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}

app = FastAPI(title="ScoutDB", version="3.0.0 (PostgreSQL + Docker)")

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE CORS (PERMISO PARA LLAMADAS DE INTERNET)
# ══════════════════════════════════════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que tu frontend en internet se conecte sin bloqueos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# ESQUEMA DE BASE DE DATOS (PostgreSQL)
# ══════════════════════════════════════════════════════════════════════════
def init_db() -> None:
    """Crea las tablas en PostgreSQL si no existen."""
    with open_db() as con:
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS secciones (
                    id          TEXT PRIMARY KEY,
                    nombre      TEXT NOT NULL,
                    rama        TEXT,
                    color       TEXT,
                    capacidad   INTEGER NOT NULL DEFAULT 30,
                    lider       TEXT,
                    descripcion TEXT,
                    activa      BOOLEAN DEFAULT true,
                    creada_en   TEXT
                );

                CREATE TABLE IF NOT EXISTS miembros (
                    id                  TEXT PRIMARY KEY,
                    numero_scout        TEXT,
                    nombre              TEXT NOT NULL,
                    apellido            TEXT NOT NULL,
                    tipo                TEXT NOT NULL DEFAULT 'beneficiario',
                    fecha_nacimiento    TEXT,
                    cargo               TEXT,
                    seccion_id          TEXT REFERENCES secciones(id),
                    fecha_ingreso       TEXT,
                    telefono            TEXT,
                    email               TEXT,
                    direccion           TEXT,
                    nombre_tutor        TEXT,
                    telefono_emergencia TEXT,
                    grupo_sanguineo     TEXT,
                    alergias            TEXT,
                    activo              BOOLEAN DEFAULT true,
                    notas               TEXT,
                    creado_en           TEXT
                );

                CREATE TABLE IF NOT EXISTS asistencias (
                    id          TEXT PRIMARY KEY,
                    miembro_id  TEXT NOT NULL REFERENCES miembros(id),
                    actividad   TEXT NOT NULL,
                    fecha       TEXT NOT NULL,
                    presente    BOOLEAN DEFAULT false,
                    notas       TEXT
                );

                CREATE TABLE IF NOT EXISTS equipo_bolsillo (
                    id                TEXT PRIMARY KEY,
                    miembro_id        TEXT NOT NULL REFERENCES miembros(id),
                    articulo          TEXT NOT NULL,
                    estado            TEXT DEFAULT 'Bueno',
                    fecha_asignacion  TEXT,
                    notas             TEXT
                );

                CREATE TABLE IF NOT EXISTS uniformes (
                    id          TEXT PRIMARY KEY,
                    miembro_id  TEXT NOT NULL REFERENCES miembros(id),
                    pieza       TEXT NOT NULL,
                    tiene       BOOLEAN DEFAULT false,
                    talla       TEXT,
                    estado      TEXT DEFAULT 'Pendiente',
                    notas       TEXT
                );

                CREATE TABLE IF NOT EXISTS registro_anual (
                    id            TEXT PRIMARY KEY,
                    miembro_id    TEXT NOT NULL REFERENCES miembros(id),
                    anio          INTEGER NOT NULL,
                    estado        TEXT DEFAULT 'Pendiente',
                    fecha_pago    TEXT,
                    monto         NUMERIC,
                    observaciones TEXT,
                    UNIQUE (miembro_id, anio)
                );

                CREATE TABLE IF NOT EXISTS transferencias (
                    id                 TEXT PRIMARY KEY,
                    miembro_id         TEXT NOT NULL REFERENCES miembros(id),
                    seccion_origen_id  TEXT REFERENCES secciones(id),
                    seccion_destino_id TEXT NOT NULL REFERENCES secciones(id),
                    fecha              TEXT NOT NULL,
                    motivo             TEXT,
                    realizado_por      TEXT,
                    notas              TEXT
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
                    seccion_id          TEXT REFERENCES secciones(id),
                    miembro_id          TEXT,
                    activo              BOOLEAN DEFAULT true,
                    debe_cambiar_pass   BOOLEAN DEFAULT true,
                    creado_en           TEXT,
                    ultimo_login        TEXT
                );

                CREATE TABLE IF NOT EXISTS sesiones (
                    token       TEXT PRIMARY KEY,
                    usuario_id  TEXT NOT NULL REFERENCES usuarios(id),
                    creado_en   TEXT NOT NULL,
                    expira_en   TEXT NOT NULL
                );
            """)
    log.info("Infraestructura de base de datos lista en PostgreSQL.")

init_db()

# ─── DASHBOARD ───
@app.get("/api/dashboard")
def dashboard(con = Depends(get_db)):
    with con.cursor() as cur:
        cur.execute("SELECT COUNT(*) as count FROM miembros WHERE activo=true")
        total_miembros = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM secciones WHERE activa=true")
        total_secciones = cur.fetchone()["count"]

        anio_actual = date.today().year
        cur.execute("SELECT COUNT(*) as count FROM registro_anual WHERE anio=%s AND estado='Registrado'", [anio_actual])
        registrados_anio = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM registro_anual WHERE anio=%s AND estado='Pendiente'", [anio_actual])
        pendientes_reg = cur.fetchone()["count"]

        primer_dia_mes = f"{date.today().year}-{date.today().month:02d}-01"
        cur.execute("SELECT COUNT(*) as count FROM transferencias WHERE fecha >= %s", [primer_dia_mes])
        transferencias_mes = cur.fetchone()["count"]

        cur.execute("SELECT id, nombre, color, capacidad FROM secciones WHERE activa=true ORDER BY nombre")
        secciones = rows_to_dicts(cur)
        
        for s in secciones:
            cur.execute("SELECT COUNT(*) as count FROM miembros WHERE seccion_id=%s AND activo=true AND tipo='beneficiario'", [s["id"]])
            occ = cur.fetchone()["count"]
            s["ocupados"] = occ
            s["disponibles"] = s["capacidad"] - occ
            
            cur.execute("SELECT COUNT(*) as count FROM miembros WHERE seccion_id=%s AND activo=true AND tipo='scouter'", [s["id"]])
            s["scouters"] = cur.fetchone()["count"]

        cur.execute("""
            SELECT actividad, fecha,
                   COUNT(*) AS total,
                   SUM(CASE WHEN presente THEN 1 ELSE 0 END) AS presentes
            FROM   asistencias
            GROUP  BY actividad, fecha
            ORDER  BY fecha DESC
            LIMIT  5
        """)
        actividades = cur.fetchall()

    return {
        "total_miembros":      total_miembros,
        "total_secciones":     total_secciones,
        "registrados_anio":    registrados_anio,
        "pendientes_registro": pendientes_reg,
        "transferencias_mes":  transferencias_mes,
        "secciones":           secciones,
        "ultimas_actividades": [
            {"actividad": r["actividad"], "fecha": r["fecha"], "total": r["total"], "presentes": int(r["presentes"] or 0)}
            for r in actividades
        ],
    }

# ─── SEED ───
@app.post("/api/seed")
def seed_data(con = Depends(get_db)): 
    import random
    from security import hash_password, DOMAIN, generate_username

    with con.cursor() as cur:
        cur.execute("SELECT COUNT(*) as count FROM secciones")
        if cur.fetchone()["count"] > 0:
            raise HTTPException(400, "Ya existen datos en la base de datos.")

    try:
        with con.cursor() as cur:
            secciones_seed = [
                (uid(), "Manada",    "Lobatos (7-10 años)", "#f4a261", 24, "Akela"),
                (uid(), "Tropa",     "Scouts (11-15 años)", "#2d6a4f", 32, "Scoutmaster"),
                (uid(), "Comunidad", "Caminantes (16-17)",  "#457b9d", 20, "Guía"),
                (uid(), "Clan",      "Rovers (18-21 años)", "#9b2226", 16, "Presidente"),
            ]
            for s in secciones_seed:
                cur.execute("INSERT INTO secciones VALUES (%s,%s,%s,%s,%s,%s,%s,true,%s)",
                            [s[0], s[1], s[2], s[3], s[4], s[5], None, now()])

            miembros_data = [
                ("Carlos", "Ramírez", "2010-03-15", "Lobato", 0),
                ("Sofía", "Mendoza", "2009-07-22", "Lobato", 0),
                ("Luis", "Hernández", "2007-09-30", "Scout", 1),
                ("Valentina", "López", "2006-04-12", "Guía", 1),
                ("Diego", "Cruz", "2004-03-02", "Caminante", 2),
                ("Javier", "Morales", "2002-05-28", "Rover", 3),
            ]
            
            ids = []
            for m in miembros_data:
                mid = uid()
                ids.append(mid)
                sec_id = secciones_seed[m[4]][0]
                cur.execute("INSERT INTO miembros VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,NULL,NULL,%s,NULL,NULL,NULL,true,NULL,%s)",
                            [mid, f"MX{random.randint(1000,9999)}", m[0], m[1], "beneficiario", m[2], m[3], sec_id, "2024-01-01", f"Tutor de {m[0]}", now()])

                for pieza in ["Camisa", "Pañoleta", "Cinturón"]:
                    cur.execute("INSERT INTO uniformes VALUES (%s,%s,%s,true,'M','Completo',NULL)", [uid(), mid, pieza])
                
                cur.execute("INSERT INTO registro_anual VALUES (%s,%s,%s,'Registrado','2024-02-15',350.0,NULL)", 
                            [uid(), mid, date.today().year])

            def _quick_user(nombre, rol, uname):
                salt = secrets.token_hex(16)
                u_id = uid()
                cur.execute("""
                    INSERT INTO usuarios (id, email, username, nombre_completo, password_hash, salt, rol, tipo, activo, debe_cambiar_pass, creado_en)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'scouter',true,false,%s)
                """, [u_id, f"{uname}@{DOMAIN}", uname, nombre, hash_password(uname, salt), salt, rol, now()])

            _quick_user("Admin", "dev", "dev")
            _quick_user("Jefe de Grupo", "master", "master")

    except Exception as e:
        con.rollback()
        raise e

    return {"ok": True, "msg": "Base de datos poblada con éxito."}

# ─── RUTAS ESTÁTICAS Y SPA ───
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def root():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/intranet")
def intranet():
    return FileResponse(str(STATIC_DIR / "app.html"))

@app.get("/{path:path}")
def spa_fallback(path: str):
    if path.startswith("api/"):
        raise HTTPException(404)
    if path.startswith("intranet"):
        return FileResponse(str(STATIC_DIR / "app.html"))
    full_path = STATIC_DIR / path
    if full_path.exists():
        return FileResponse(str(full_path))
    return FileResponse(str(STATIC_DIR / "index.html"))