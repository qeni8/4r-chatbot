"""Veri yaşam döngüsü: KVKK saklama süresi ve şema göçü."""

import sqlite3

from app.config import settings
from app.db import GOCLER, db_file, eski_loglari_temizle, get_conn, init_db


def _log_ekle(gun_once: int, adet: int = 1) -> None:
    with get_conn() as conn:
        conn.executemany(
            "insert into konusma_loglari (kanal, soru, cevap, yontem, created_at) "
            "values ('web', 's', 'c', 'rag', datetime('now', ?))",
            [(f"-{gun_once} days",) for _ in range(adet)],
        )
        conn.commit()


def _sayi() -> int:
    with get_conn() as conn:
        return conn.execute("select count(*) from konusma_loglari").fetchone()[0]


def test_saklama_suresi_eskiyi_siler(monkeypatch):
    monkeypatch.setattr(settings, "log_saklama_gun", 30)
    _log_ekle(gun_once=60, adet=3)   # süresi dolmuş
    _log_ekle(gun_once=5, adet=2)    # taze
    silinen = eski_loglari_temizle()
    assert silinen == 3
    assert _sayi() == 2


def test_saklama_kapaliyken_silmez(monkeypatch):
    monkeypatch.setattr(settings, "log_saklama_gun", 0)
    _log_ekle(gun_once=900, adet=2)
    assert eski_loglari_temizle() == 0
    assert _sayi() == 2


def test_goc_eksik_sutunu_ekler(tmp_path, monkeypatch):
    """Eski bir veritabanı dosyası, yeni sütunlarla güncellenmeli."""
    eski = tmp_path / "eski.db"
    with sqlite3.connect(eski) as conn:  # 'istemci' sütunu olmayan eski şema
        conn.execute("create table konusma_loglari (id integer primary key, kanal text, "
                     "oturum_id text, soru text, cevap text, yontem text, kaynaklar text, "
                     "model text, created_at text default (datetime('now')))")
        conn.commit()

    monkeypatch.setattr(settings, "db_path", str(eski))
    init_db()

    with sqlite3.connect(db_file()) as conn:
        sutunlar = {r[1] for r in conn.execute("pragma table_info(konusma_loglari)")}
    for _tablo, sutun, _tanim in GOCLER:
        assert sutun in sutunlar
