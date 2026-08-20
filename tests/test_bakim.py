"""Bakım: bot düştüğünde haber gitmeli, veritabanı yedeği tutarlı olmalı."""

import sqlite3

import httpx
import pytest

from app.config import settings
from app.db import db_file, get_conn
from scripts import bakim


class _Yanit:
    def __init__(self, kod: int, veri: dict):
        self.status_code = kod
        self._veri = veri

    def json(self) -> dict:
        return self._veri


def test_saglik_ok(monkeypatch):
    monkeypatch.setattr(bakim.httpx, "get",
                        lambda *a, **kw: _Yanit(200, {"status": "ok", "atik_kodu": 842}))
    assert bakim.saglik() is None


@pytest.mark.parametrize("yanit", [
    _Yanit(500, {}),
    _Yanit(200, {"status": "ok", "atik_kodu": 0}),
])
def test_saglik_sorunu_yakalar(monkeypatch, yanit):
    monkeypatch.setattr(bakim.httpx, "get", lambda *a, **kw: yanit)
    assert bakim.saglik() is not None


def test_ulasilamadiginda_bildirilir(monkeypatch):
    gonderilen = []
    monkeypatch.setattr(bakim.httpx, "get",
                        lambda *a, **kw: (_ for _ in ()).throw(httpx.ConnectError("kapalı")))
    monkeypatch.setattr(bakim.devir, "bildir",
                        lambda b, g: gonderilen.append(b) or [])
    assert bakim.main() == 1
    assert "YANIT VERMİYOR" in gonderilen[0]


def test_yedek_veriyi_tasir():
    with get_conn() as conn:
        conn.execute("insert into konusma_loglari (kanal, soru, cevap, yontem) "
                     "values ('web', 's', 'c', 'test')")
        conn.commit()

    hedef = bakim.yedekle()
    assert hedef.exists()
    with sqlite3.connect(hedef) as yedek:
        assert yedek.execute("select count(*) from konusma_loglari").fetchone()[0] >= 1


def test_eski_yedekler_silinir(monkeypatch):
    klasor = db_file().parent / "yedek"
    klasor.mkdir(parents=True, exist_ok=True)
    eski = klasor / f"{db_file().stem}_2000-01-01.db"
    eski.write_bytes(b"")
    monkeypatch.setattr(settings, "yedek_saklama_gun", 14)

    bakim.yedekle()
    assert not eski.exists()
