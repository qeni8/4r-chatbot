"""Yönetim paneli: erişim kontrolü ve içerik.

Panel şirket verisini gösterir — şifresiz açık kalması kabul edilemez.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.db import get_conn

SIFRE = "test-sifre"


def _yetki(kullanici: str = "4r", sifre: str = SIFRE) -> dict:
    kod = base64.b64encode(f"{kullanici}:{sifre}".encode()).decode()
    return {"Authorization": f"Basic {kod}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "yonetim_sifre", SIFRE)
    monkeypatch.setattr(settings, "yonetim_kullanici", "4r")
    with TestClient(main.app) as c:
        yield c


def _devir_ekle(soru: str = "lisans tarihi", ad: str | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "insert into devir_kayitlari (kanal, sebep, soru, cevap, ad, telefon) "
            "values ('web', 'bilgi_yok', ?, 'devir', ?, ?)",
            (soru, ad, "05001112233" if ad else None),
        )
        conn.commit()
        return cur.lastrowid


def test_sifresiz_erisim_reddedilir(client):
    assert client.get("/yonetim").status_code == 401


def test_yanlis_sifre_reddedilir(client):
    assert client.get("/yonetim", headers=_yetki(sifre="yanlis")).status_code == 401


def test_yanlis_kullanici_reddedilir(client):
    assert client.get("/yonetim", headers=_yetki(kullanici="baska")).status_code == 401


def test_sifre_ayarli_degilse_panel_kapali(monkeypatch):
    """Kazara açık kalmasın: şifre yoksa panel hiç yok."""
    monkeypatch.setattr(settings, "yonetim_sifre", "")
    with TestClient(main.app) as c:
        assert c.get("/yonetim", headers=_yetki()).status_code == 404


def test_panel_bekleyen_talepleri_gosterir(client):
    _devir_ekle("lisans belgeniz ne zaman bitiyor")
    html = client.get("/yonetim", headers=_yetki()).text
    assert "lisans belgeniz ne zaman bitiyor" in html
    assert "Bekleyen talepler" in html


def test_iletisim_birakan_musteri_vurgulanir(client):
    _devir_ekle("fiyat sorusu", ad="Ayşe Yılmaz")
    html = client.get("/yonetim", headers=_yetki()).text
    assert "Ayşe Yılmaz" in html
    assert "iletisim" in html  # vurgulu satır sınıfı


def test_okundu_isaretleme(client):
    devir_id = _devir_ekle("işaretlenecek soru")
    r = client.post(f"/yonetim/devir/{devir_id}/okundu", headers=_yetki(),
                    follow_redirects=False)
    assert r.status_code == 303
    with get_conn() as conn:
        durum = conn.execute("select durum from devir_kayitlari where id = ?",
                             (devir_id,)).fetchone()[0]
    assert durum == "okundu"
    assert "işaretlenecek soru" not in client.get("/yonetim", headers=_yetki()).text


def test_html_kacisi_yapilir(client):
    """Müşteri mesajı panele HTML olarak enjekte edilememeli."""
    _devir_ekle("<script>alert(1)</script>")
    html = client.get("/yonetim", headers=_yetki()).text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
