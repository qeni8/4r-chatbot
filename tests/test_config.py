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


def test_tanimsiz_saglayici_yakalanir(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    assert any("LLM_PROVIDER" in u for u in yapilandirma_uyarilari())
