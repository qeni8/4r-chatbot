import httpx
import pytest

from app import llm
from app.config import settings


class SahteYanit:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


@pytest.fixture(autouse=True)
def _gemini_ayarli(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)  # yeniden deneme beklemesi


def _post(monkeypatch, yanit):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **kw: yanit)


def _post_sirasi(monkeypatch, yanitlar: list):
    """Ardışık çağrılara sırayla farklı yanıt döndürür (yeniden deneme testi)."""
    sayac = {"n": 0}

    def _post_fn(*a, **kw):
        y = yanitlar[min(sayac["n"], len(yanitlar) - 1)]
        sayac["n"] += 1
        return y

    monkeypatch.setattr(llm.httpx, "post", _post_fn)
    return sayac


def test_kota_limiti_ayri_istisna(monkeypatch):
    _post(monkeypatch, SahteYanit(429, text="RESOURCE_EXHAUSTED"))
    with pytest.raises(llm.LLMRateLimit):
        llm.answer("test")


def test_sunucu_hatasi_llm_error(monkeypatch):
    _post(monkeypatch, SahteYanit(500, text="internal"))
    with pytest.raises(llm.LLMError) as e:
        llm.answer("test")
    assert not isinstance(e.value, llm.LLMRateLimit)


def test_bos_aday_yutulmaz(monkeypatch):
    """Güvenlik filtresi boş yanıt döndürürse sessizce 'başarılı' sayılmamalı."""
    _post(monkeypatch, SahteYanit(200, {"candidates": []}))
    with pytest.raises(llm.LLMError):
        llm.answer("test")


def test_bos_metin_yutulmaz(monkeypatch):
    _post(monkeypatch, SahteYanit(200, {"candidates": [{"content": {"parts": []},
                                                        "finishReason": "SAFETY"}]}))
    with pytest.raises(llm.LLMError):
        llm.answer("test")


def test_basarili_cevap(monkeypatch):
    _post(monkeypatch, SahteYanit(200, {"candidates": [
        {"content": {"parts": [{"text": "Merhaba."}]}, "finishReason": "STOP"}
    ]}))
    cevap, model = llm.answer("test")
    assert cevap == "Merhaba."
    assert model == settings.gemini_model


def test_ag_hatasi_llm_error(monkeypatch):
    def _patla(*a, **kw):
        raise httpx.ConnectError("bağlantı yok")

    monkeypatch.setattr(llm.httpx, "post", _patla)
    with pytest.raises(llm.LLMError):
        llm.answer("test")


def test_anahtar_yoksa_acik_hata(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(llm.LLMError, match="GEMINI_API_KEY"):
        llm.answer("test")


def test_kaynaklar_prompta_girer(monkeypatch):
    yakalanan = {}

    def _yakala(*a, **kw):
        yakalanan["json"] = kw["json"]
        return SahteYanit(200, {"candidates": [
            {"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}
        ]})

    monkeypatch.setattr(llm.httpx, "post", _yakala)
    llm.answer("soru", [{"baslik": "Atık kodu tablosu", "icerik": "06 01 01 kabul: Merkez"}])
    metin = yakalanan["json"]["contents"][-1]["parts"][0]["text"]
    assert "06 01 01 kabul: Merkez" in metin
    assert "MÜŞTERİ SORUSU: soru" in metin


def test_gecici_hata_sonrasi_toparlar(monkeypatch):
    """Gemini 'high demand' (503) geçicidir — bot bu yüzden düşmemeli."""
    basarili = SahteYanit(200, {"candidates": [
        {"content": {"parts": [{"text": "toparlandı"}]}, "finishReason": "STOP"}
    ]})
    sayac = _post_sirasi(monkeypatch, [SahteYanit(503, text="high demand"), basarili])
    cevap, _ = llm.answer("test")
    assert cevap == "toparlandı"
    assert sayac["n"] == 2  # ilk deneme başarısız, ikincisi başarılı


def test_kalici_hata_yeniden_denenmez(monkeypatch):
    """400 gibi kalıcı hatada boşuna beklenmemeli."""
    sayac = _post_sirasi(monkeypatch, [SahteYanit(400, text="bad request")])
    with pytest.raises(llm.LLMError):
        llm.answer("test")
    assert sayac["n"] == 1


def test_surekli_503_llm_error(monkeypatch):
    _post(monkeypatch, SahteYanit(503, text="high demand"))
    with pytest.raises(llm.LLMError) as e:
        llm.answer("test")
    assert not isinstance(e.value, llm.LLMRateLimit)


def test_sistem_promptu_kritik_kurallari_icerir():
    assert "uydurma" in llm.SISTEM
    assert "BİRİNİ SEÇME" in llm.SISTEM          # çoklu kod adayında model karar vermez
    assert "talimat olarak değil" in llm.SISTEM  # dolaylı prompt injection koruması
    assert "Türkçe" in llm.SISTEM
