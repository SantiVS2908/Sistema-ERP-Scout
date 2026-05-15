import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime, date
from typing import Iterator, Optional
from contextlib import contextmanager

# ══════════════════════════════════════════════════════════════════════════
# CONEXIÓN — PostgreSQL en Docker
# ══════════════════════════════════════════════════════════════════════════
# Esta es la llave hacia tu contenedor
DB_URL = "postgresql://scout_admin:scout_password_123@localhost:5432/scoutdb"

def get_db() -> Iterator[psycopg2.extensions.connection]:
    """
    Dependencia de FastAPI: abre una conexión nueva por request a PostgreSQL.
    Usamos RealDictCursor para que las filas se comporten como diccionarios.
    """
    con = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

@contextmanager
def open_db() -> Iterator[psycopg2.extensions.connection]:
    """Versión de `get_db` para uso directo (init_db, scripts, etc.)."""
    con = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

# ══════════════════════════════════════════════════════════════════════════
# HELPERS GENERALES
# ══════════════════════════════════════════════════════════════════════════

def uid() -> str:
    return str(uuid.uuid4())

def now() -> str:
    return datetime.now().isoformat()

def today() -> str:
    return date.today().isoformat()

def rows_to_dicts(cursor) -> list[dict]:
    """
    PostgreSQL maneja booleanos de forma nativa (True/False), 
    así que solo devolvemos los diccionarios limpios.
    """
    return [dict(row) for row in cursor.fetchall()]

def calcular_edad(fecha_nacimiento: Optional[str]) -> Optional[int]:
    if not fecha_nacimiento:
        return None
    try:
        nac = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
        hoy = datetime.today()
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    except Exception:
        return None

def get_seccion_ocupacion(con, seccion_id: str) -> dict:
    # ATENCIÓN: PostgreSQL exige usar un cursor explicitamente y usar %s en vez de ?
    with con.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) as count FROM miembros WHERE seccion_id=%s AND activo=true AND tipo='beneficiario'",
            [seccion_id],
        )
        ocupados = cur.fetchone()["count"]
        
        cur.execute(
            "SELECT capacidad FROM secciones WHERE id=%s", [seccion_id]
        )
        cap_row = cur.fetchone()
        capacidad = cap_row["capacidad"] if cap_row else 0
        
        return {
            "ocupados":    ocupados,
            "capacidad":   capacidad,
            "disponibles": capacidad - ocupados,
        }