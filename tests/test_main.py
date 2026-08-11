"""API uçları — daha önce hiç çalıştırılmıyordu (CORS, /chat, webhook yolları dahil)."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app import bot, main
from app.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(bot.llm, "answer", lambda *a, **kw: ("Test cevabı.", "sahte-model"))
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    veri = r.json()
    assert veri["status"] == "ok"
    assert veri["atik_kodu"] > 0   # şema + veri gerçekten yüklü mü


def test_chat_yapisal_cevap(client):
    r = client.post("/chat", json={"message": "06 01 01 alıyor musunuz", "session_id": "api-1"})
    assert r.status_code == 200
    assert r.json()["method"] == "atik_kodu"


def test_chat_model_yolu(client):
    r = client.post("/chat", json={"message": "vidanjör hizmetiniz var mı",
                                   "session_id": "api-2"})
    assert r.json()["method"] == "rag"
    assert r.json()["answer"] == "Test cevabı."


def test_chat_bos_mesaj(client):
    r = client.post("/chat", json={"message": "", "session_id": "api-3"})
    assert r.json()["method"] == "bos"


def test_webhook_dogrulama_yanlis_token(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", "dogru")
    r = client.get("/webhook/whatsapp", params={"hub.mode": "subscribe",
                                                "hub.verify_token": "yanlis",
                                                "hub.challenge": "123"})
    assert r.status_code == 403


def test_webhook_dogrulama_dogru_token(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", "dogru")
    r = client.get("/webhook/whatsapp", params={"hub.mode": "subscribe",
                                                "hub.verify_token": "dogru",
                                                "hub.challenge": "123"})
    assert r.status_code == 200 and r.text == "123"


def test_webhook_gecersiz_imza_reddedilir(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "gizli")
    r = client.post("/webhook/whatsapp", json={"entry": []},
                    headers={"x-hub-signature-256": "sha256=yanlis"})
    assert r.status_code == 403


def test_webhook_gecerli_imza_kabul(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "gizli")
    govde = json.dumps({"entry": []}).encode()
    imza = "sha256=" + hmac.new(b"gizli", govde, hashlib.sha256).hexdigest()
    r = client.post("/webhook/whatsapp", content=govde,
                    headers={"x-hub-signature-256": imza,
                             "content-type": "application/json"})
    assert r.status_code == 200


def test_widget_ve_demo_servis_edilir(client):
    assert client.get("/widget.js").status_code == 200
    assert "4R" in client.get("/demo").text
