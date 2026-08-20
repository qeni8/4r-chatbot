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


# Şema sonradan büyürse mevcut veritabanları da güncellensin ("create table if not exists"
# var olan tabloya sütun eklemez). (tablo, sütun, tanım)
GOCLER = [("konusma_loglari", "istemci", "istemci text")]


def init_db() -> None:
    """Şemayı uygular (idempotent). Uygulama açılışında ve scriptlerde çağrılır."""
    path = db_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("pragma journal_mode=WAL")
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        for tablo, sutun, tanim in GOCLER:
            mevcut = {r[1] for r in conn.execute(f"pragma table_info({tablo})").fetchall()}
            if sutun not in mevcut:
                conn.execute(f"alter table {tablo} add column {tanim}")
        conn.commit()


def eski_loglari_temizle() -> int:
    """KVKK saklama süresini uygular; silinen kayıt sayısını döndürür."""
    if settings.log_saklama_gun <= 0:
        return 0
    with get_conn() as conn:
        cur = conn.execute(
            "delete from konusma_loglari where created_at < datetime('now', ?)",
            (f"-{settings.log_saklama_gun} days",),
        )
        conn.commit()
        return cur.rowcount


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_file(), timeout=10)
    conn.execute("pragma busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()
