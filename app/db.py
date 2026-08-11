import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def db_file() -> Path:
    p = Path(settings.db_path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    return p


def init_db() -> None:
    """Şemayı uygular (idempotent). Uygulama açılışında ve scriptlerde çağrılır."""
    path = db_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("pragma journal_mode=WAL")
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_file(), timeout=10)
    conn.execute("pragma busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()
