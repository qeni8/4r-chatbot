import pytest

from app import bot, llm
from app.bot import BOS, reply
from app.sabitler import DEVIR, YOGUNLUK


@pytest.fixture
def sahte_llm(monkeypatch):
    """llm.answer'ı yakalar: çağrıldı mı, hangi kaynaklarla?"""
    cagrilar = []

    def _sahte(soru, ek_kaynaklar=None, gecmis=None):
        cagrilar.append({"soru": soru, "ek": ek_kaynaklar or [], "gecmis": gecmis or []})
        return "Test cevabı.", "sahte-model"

    monkeypatch.setattr(bot.llm, "answer", _sahte)
    return cagrilar


@pytest.mark.parametrize("mesaj", ["", "   ", "\n\t "])
def test_bos_mesaj(mesaj: str):
    r = reply(mesaj, "test-bos", "web")
    assert r["method"] == "bos"
    assert r["answer"] == BOS


def test_atik_kodu_llm_gerektirmez(sahte_llm):
    r = reply("06 01 01 alıyor musunuz", "test-kod", "web")
    assert r["method"] == "atik_kodu"
    assert "alıyoruz" in r["answer"]
    assert sahte_llm == []  # modele hiç gitmemeli


@pytest.mark.parametrize("mesaj", ["merhaba", "Selam!", "teşekkürler", "sağ ol"])
def test_selam_tesekkur_modelsiz(mesaj: str, sahte_llm):
    r = reply(mesaj, "test-selam", "web")
    assert r["method"] == "selam"
    assert sahte_llm == []


def test_selam_ve_kod_yutulmaz(sahte_llm):
    r = reply("merhaba 06 01 01 alıyor musunuz", "test-selamkod", "web")
    assert r["method"] == "atik_kodu"


def test_tarih_sahte_kod_uretmez(sahte_llm):
    """01.05.2024 içindeki '05.2024' atık kodu sanılıp sahte cevap dönmemeli."""
    r = reply("01.05.2024 tarihinde gönderdiğim atık ne durumda", "test-tarih", "web")
    assert r["method"] == "rag"
    assert "bulamadım" not in r["answer"]


def test_kod_ve_baska_soru_modele_gider(sahte_llm):
    """'06 01 01 fiyatı ne kadar' → yapısal cevapla yutulmamalı, model tam soruyu cevaplamalı."""
    r = reply("06 01 01 fiyatı ne kadar", "test-kodfiyat", "web")
    assert r["method"] == "rag"
    assert len(sahte_llm) == 1
    kaynak_metni = " ".join(k["icerik"] for k in sahte_llm[0]["ek"])
    assert "06 01 01" in kaynak_metni  # tablo sonucu modele kaynak olarak verilmeli


def test_isimle_arama_kaynak_ekler(sahte_llm):
    reply("boya çamuru alıyor musunuz", "test-isim", "web")
    kaynak_metni = " ".join(k["icerik"] for k in sahte_llm[0]["ek"])
    assert "08 01 14" in kaynak_metni


def test_uydurma_atik_kodu_kullaniciya_gitmez(monkeypatch):
    """Model tabloda olmayan bir kod yazarsa cevap gönderilmemeli (en pahalı hata)."""
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: ("Bu atığı 07 07 07 koduyla gönderebilirsiniz.", "m"))
    r = reply("hangi kodla göndermeliyim", "test-uydurma", "web")
    assert r["method"] == "kod_dogrulama"
    assert "07 07 07" not in r["answer"]


def test_gecerli_kod_iceren_cevap_gecer(monkeypatch):
    """Doğrulama yanlış alarm vermemeli: tabloda olan kod normal geçmeli."""
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: ("08 01 14 kodlu atığı kabul ediyoruz.", "m"))
    r = reply("boya çamuru hangi kod", "test-gecerli", "web")
    assert r["method"] == "rag"


def test_iletisim_numarasi_kod_sanilmaz(monkeypatch):
    """Cevaptaki telefon numarası 'uydurma kod' olarak işaretlenmemeli."""
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: ("Bilgi için: +90 282 652 30 90, info@4r.com.tr", "m"))
    r = reply("telefon numaranız", "test-tel", "web")
    assert r["method"] == "rag"


def test_llm_kota_limiti_yogunluk_mesaji(monkeypatch):
    def _limit(*a, **kw):
        raise llm.LLMRateLimit("kota")

    monkeypatch.setattr(bot.llm, "answer", _limit)
    r = reply("vidanjör hizmetiniz var mı", "test-limit", "web")
    assert r["method"] == "yogunluk"
    assert r["answer"] == YOGUNLUK


def test_llm_gercek_hata_devir(monkeypatch):
    def _patla(*a, **kw):
        raise llm.LLMError("ayrıştırma hatası")

    monkeypatch.setattr(bot.llm, "answer", _patla)
    r = reply("vidanjör hizmetiniz var mı", "test-hata", "web")
    assert r["method"] == "hata"
    assert r["answer"] == DEVIR


def test_hatali_cevap_hafizaya_girmez(monkeypatch):
    """Başarısız turlar sonraki promptu kirletmemeli."""
    monkeypatch.setattr(bot.llm, "answer",
                        lambda *a, **kw: (_ for _ in ()).throw(llm.LLMError("geçici")))
    reply("ilk soru", "test-hafiza", "web")

    gorulen: list = []
    monkeypatch.setattr(bot.llm, "answer",
                        lambda soru, ek=None, gecmis=None: (gorulen.append(gecmis or []),
                                                            ("ok", "m"))[1])
    reply("ikinci soru", "test-hafiza", "web")
    assert gorulen[0] == []


def test_basarili_cevap_hafizaya_girer(monkeypatch):
    gorulen: list = []
    monkeypatch.setattr(bot.llm, "answer",
                        lambda soru, ek=None, gecmis=None: (gorulen.append(gecmis or []),
                                                            ("ilk cevap", "m"))[1])
    reply("ilk soru", "test-hafiza2", "web")
    reply("ikinci soru", "test-hafiza2", "web")
    assert gorulen[1] == [("ilk soru", "ilk cevap")]
