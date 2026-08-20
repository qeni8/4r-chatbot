"""Yayında sessizce bozuk çalışmaya yol açan yapılandırmalar erkenden yakalanmalı."""

import pytest

from app.config import settings, yapilandirma_uyarilari


@pytest.fixture(autouse=True)
def _saglikli_varsayilan(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "anahtar")
    monkeypatch.setattr(settings, "cors_origins", "https://4r.com.tr")
    monkeypatch.setattr(settings, "whatsapp_app_secret", "gizli")
    monkeypatch.setattr(settings, "whatsapp_access_token", "token")
    monkeypatch.setattr(settings, "log_saklama_gun", 180)
    monkeypatch.setattr(settings, "bildirim_eposta", "lojistik@4r.com.tr")
    monkeypatch.setattr(settings, "smtp_host", "mail.4r.com.tr")


def test_saglikli_yapilandirma_uyari_vermez():
    assert yapilandirma_uyarilari() == []


def test_eksik_llm_anahtari_yakalanir(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert any("GEMINI_API_KEY" in u for u in yapilandirma_uyarilari())


def test_prodda_acik_cors_yakalanir(monkeypatch):
    monkeypatch.setattr(settings, "cors_origins", "*")
    assert any("CORS_ORIGINS" in u for u in yapilandirma_uyarilari())


def test_devde_acik_cors_uyari_degil(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "cors_origins", "*")
    assert yapilandirma_uyarilari() == []


def test_whatsapp_secret_eksikligi_yakalanir(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "")
    assert any("WHATSAPP_APP_SECRET" in u for u in yapilandirma_uyarilari())


def test_saklama_kapaliysa_kvkk_uyarisi(monkeypatch):
    monkeypatch.setattr(settings, "log_saklama_gun", 0)
    assert any("LOG_SAKLAMA_GUN" in u for u in yapilandirma_uyarilari())


def test_bildirim_kanali_yoksa_uyarir(monkeypatch):
    """Botun 'yetkiliye aktarıyorum' sözü boşta kalıyorsa bu sessiz kalmamalı."""
    monkeypatch.setattr(settings, "bildirim_eposta", "")
    monkeypatch.setattr(settings, "bildirim_whatsapp", "")
    assert any("Bildirim gönderilemiyor" in u for u in yapilandirma_uyarilari())


def test_tanimsiz_saglayici_yakalanir(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    assert any("LLM_PROVIDER" in u for u in yapilandirma_uyarilari())


def test_alicisi_var_ama_smtp_yoksa_uyarir(monkeypatch):
    """Alıcı yazılı diye 'her şey yolunda' denmemeli — posta yine gitmiyor."""
    monkeypatch.setattr(settings, "smtp_host", "")
    assert any("Bildirim gönderilemiyor" in u for u in yapilandirma_uyarilari())


def test_smtp_yoksa_calisir_whatsapp_yeter(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "bildirim_eposta", "")
    monkeypatch.setattr(settings, "bildirim_whatsapp", "905321112233")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "1")
    assert yapilandirma_uyarilari() == []
