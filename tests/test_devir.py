"""Devir akışı: bot 'yetkilimize aktarayım' dediğinde talep kaydedilip bildirilmeli.

Bu olmadan bot verdiği sözü tutmuyor: müşteri bekliyor, kimsenin haberi yok.
"""

import pytest

from app import bildirim, bot, devir, llm
from app.config import settings
from app.db import get_conn


@pytest.fixture(autouse=True)
def _eszamanli_bildirim(monkeypatch):
    monkeypatch.setattr(settings, "bildirim_arkaplan", False)


@pytest.fixture
def gonderilenler(monkeypatch):
    kayit = []
    monkeypatch.setattr(bildirim, "gonder",
                        lambda baslik, govde: (kayit.append((baslik, govde)), ["eposta"])[1])
    return kayit


def _devirler() -> list[tuple]:
    with get_conn() as conn:
        return conn.execute(
            "select id, sebep, soru, ad, telefon, bildirim from devir_kayitlari order by id"
        ).fetchall()


@pytest.mark.parametrize("yontem,cevap,beklenen", [
    ("rag", "Bu konuda kesin bilgi veremiyorum, sizi yetkilimize aktarayım.", "bilgi_yok"),
    ("atik_kodu", "Bu atık kodunu (999999) listemizde bulamadım.", "kod_yok"),
    ("atik_kodu", "Bu atığı şu an hiçbir tesisimizde kabul edemiyoruz.", "kabul_edilmiyor"),
    ("hata", "...", "hata"),
    ("yogunluk", "...", "hata"),
    ("limit", "Bugünkü yanıt kapasitemiz doldu.", "limit"),
    ("limit", "Çok fazla mesaj aldım, lütfen birkaç saniye sonra deneyin.", None),
    ("rag", "Evet, vidanjör hizmetimiz var.", None),
    ("selam", "Merhaba!", None),
])
def test_sebep_bul(yontem, cevap, beklenen):
    assert devir.sebep_bul(yontem, cevap) == beklenen


def test_cevaplanamayan_soru_kaydedilir_ve_bildirilir(monkeypatch, gonderilenler):
    devir_cevabi = "Bu konuda kesin bilgi veremiyorum, sizi yetkilimize aktarayım."
    monkeypatch.setattr(bot.llm, "answer", lambda *a, **kw: (devir_cevabi, "m"))
    r = bot.reply("lisans belgeniz hangi tarihe kadar geçerli", "dv-1", "web")

    assert r["devir_id"] is not None
    kayitlar = _devirler()
    assert len(kayitlar) == 1
    assert kayitlar[0][1] == "bilgi_yok"
    assert "lisans belgeniz" in kayitlar[0][2]
    assert len(gonderilenler) == 1
    assert "Yanıtlanamayan soru" in gonderilenler[0][0]


def test_basarili_cevap_devir_acmaz(monkeypatch, gonderilenler):
    monkeypatch.setattr(bot.llm, "answer", lambda *a, **kw: ("Evet, hizmetimiz var.", "m"))
    r = bot.reply("vidanjör var mı", "dv-2", "web")
    assert r["devir_id"] is None
    assert _devirler() == []
    assert gonderilenler == []


def test_model_hatasinda_devir_acilir(monkeypatch, gonderilenler):
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: (_ for _ in ()).throw(llm.LLMError("patladı")))
    r = bot.reply("atık su arıtma nasıl", "dv-3", "web")
    assert r["devir_id"] is not None
    assert _devirler()[0][1] == "hata"


def test_bildirim_kanali_kayda_islenir(monkeypatch, gonderilenler):
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: ("kesin bilgi veremiyorum", "m"))
    bot.reply("bilinmeyen soru", "dv-4", "web")
    assert _devirler()[0][5] == "eposta"


def test_iletisim_birakma_kaydi_tamamlar(monkeypatch, gonderilenler):
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: ("kesin bilgi veremiyorum", "m"))
    r = bot.reply("fiyat nedir", "dv-5", "web")

    ok = devir.iletisim_ekle(r["devir_id"], "Ayşe Yılmaz", "05321112233", "", "acil")
    assert ok is True

    kayit = _devirler()[0]
    assert kayit[3] == "Ayşe Yılmaz" and kayit[4] == "05321112233"
    assert any("GERİ DÖNÜŞ TALEBİ" in b for b, _ in gonderilenler)


def test_olmayan_devire_iletisim_eklenemez(gonderilenler):
    assert devir.iletisim_ekle(9999, "X", "0500") is False


def test_bildirim_hatasi_cevabi_dusurmez(monkeypatch):
    """SMTP çökse bile müşteri cevabını almalı."""
    monkeypatch.setattr(bildirim, "_eposta_gonder",
                        lambda *a: (_ for _ in ()).throw(OSError("smtp yok")))
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: ("kesin bilgi veremiyorum", "m"))
    r = bot.reply("soru", "dv-6", "web")
    assert r["answer"].startswith("kesin bilgi")
    assert r["devir_id"] is not None


def test_kanal_yoksa_kayit_yine_tutulur(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "bildirim_eposta", "")
    monkeypatch.setattr(settings, "bildirim_whatsapp", "")
    assert bildirim.gonder("baslik", "govde") == []
