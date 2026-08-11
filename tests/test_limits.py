"""Anti-spam / maliyet koruması — projenin sert harcama tavanı, sınanmadan bırakılmamalı."""

import pytest

from app import limits
from app.config import settings
from app.db import get_conn


def _log_ekle(oturum: str, adet: int, yontem: str = "rag", gecmis_gun: int = 0) -> None:
    with get_conn() as conn:
        conn.executemany(
            "insert into konusma_loglari (kanal, oturum_id, soru, cevap, yontem, created_at) "
            "values ('web', ?, 's', 'c', ?, datetime('now', ?))",
            [(oturum, yontem, f"-{gecmis_gun} days") for _ in range(adet)],
        )
        conn.commit()


def test_temiz_baslangicta_izin_var():
    izin, _ = limits.check("oturum-temiz")
    assert izin is True


def test_ani_yuk_engellenir(monkeypatch):
    monkeypatch.setattr(settings, "burst_limit", 3)
    _log_ekle("oturum-burst", 3)
    izin, mesaj = limits.check("oturum-burst")
    assert izin is False
    assert "birkaç saniye" in mesaj


def test_oturum_gunluk_limiti(monkeypatch):
    monkeypatch.setattr(settings, "burst_limit", 1000)  # burst'e takılmasın
    monkeypatch.setattr(settings, "session_daily_limit", 5)
    _log_ekle("oturum-gunluk", 5)
    izin, mesaj = limits.check("oturum-gunluk")
    assert izin is False
    assert "mesaj sınırına" in mesaj


def test_global_gunluk_limiti(monkeypatch):
    monkeypatch.setattr(settings, "daily_limit", 4)
    _log_ekle("baska-oturum", 4)
    izin, mesaj = limits.check("yeni-oturum")
    assert izin is False
    assert "kapasitemiz doldu" in mesaj


def test_limit_redleri_sayilmaz(monkeypatch):
    """'limit' satırları sayılsaydı bot bir kez dolduktan sonra hiç açılmazdı."""
    monkeypatch.setattr(settings, "daily_limit", 3)
    _log_ekle("oturum-red", 10, yontem="limit")
    izin, _ = limits.check("oturum-red")
    assert izin is True


def test_dunku_mesajlar_bugunu_etkilemez(monkeypatch):
    monkeypatch.setattr(settings, "session_daily_limit", 2)
    monkeypatch.setattr(settings, "burst_limit", 1000)
    _log_ekle("oturum-dun", 10, gecmis_gun=2)
    izin, _ = limits.check("oturum-dun")
    assert izin is True


def test_oturumsuz_istek_global_limite_tabi(monkeypatch):
    monkeypatch.setattr(settings, "daily_limit", 2)
    _log_ekle("x", 2)
    izin, _ = limits.check(None)
    assert izin is False


@pytest.mark.parametrize("oturum", [None, "abc"])
def test_check_daima_ikili_doner(oturum):
    izin, mesaj = limits.check(oturum)
    assert isinstance(izin, bool) and isinstance(mesaj, str)
