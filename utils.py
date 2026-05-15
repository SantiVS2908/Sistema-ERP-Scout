import sqlite3
import uuid
from datetime import datetime, date
from typing import Iterator, Optional
from contextlib import contextmanager

# Definimos la ruta de la base de datos local
DB_PATH = "scout.db"

# ══════════════════════════════════════════════════════════════════════════
# CONEXIÓN — thread-safe, con WAL
# ══════════════════════════════════════════════════════════════════════════

def _configure(con: sqlite3.Connection) -> None:
    """Aplica los PRAGMAs críticos para concurrencia."""
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")    # rápido pero durable ante crash
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")    # 30s de espera ante lock


def get_db() -> Iterator[sqlite3.Connection]:
    """
    Dependencia de FastAPI: abre una conexión nueva por request,
    la cierra al terminar. Commit/rollback automático según éxito/fallo.
    """
    con = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    _configure(con)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@contextmanager
def open_db() -> Iterator[sqlite3.Connection]:
    """Versión de `get_db` para uso directo (init_db, scripts, etc.)."""
    con = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    _configure(con)
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

def rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    """Convierte filas a dicts, normalizando booleanos almacenados como 0/1."""
    bool_cols = {"activo", "activa", "presente", "tiene"}
    result: list[dict] = []
    for row in cursor.fetchall():
        d = dict(row)
        for k in list(d.keys()):
            if k in bool_cols and d[k] is not None:
                d[k] = bool(d[k])
        result.append(d)
    return result

def calcular_edad(fecha_nacimiento: Optional[str]) -> Optional[int]:
    if not fecha_nacimiento:
        return None
    try:
        nac = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
        hoy = datetime.today()
        return hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    except Exception:
        return None

def get_seccion_ocupacion(con: sqlite3.Connection, seccion_id: str) -> dict:
    # Solo los beneficiarios consumen capacidad; los scouters no ocupan cupo
    ocupados = con.execute(
        "SELECT COUNT(*) FROM miembros WHERE seccion_id=? AND activo=1 AND tipo='beneficiario'",
        [seccion_id],
    ).fetchone()[0]
    cap_row = con.execute(
        "SELECT capacidad FROM secciones WHERE id=?", [seccion_id]
    ).fetchone()
    capacidad = cap_row[0] if cap_row else 0
    return {
        "ocupados":    ocupados,
        "capacidad":   capacidad,
        "disponibles": capacidad - ocupados,
    }