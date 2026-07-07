import hashlib
import hmac

from app import whatsapp
from app.config import settings


def _imzala(raw: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def test_imza_dogru(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "gizli")
    raw = b'{"entry":[]}'
    assert whatsapp.verify_signature(raw, _imzala(raw, "gizli")) is True


def test_imza_yanlis(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "gizli")
    raw = b'{"entry":[]}'
    assert whatsapp.verify_signature(raw, _imzala(raw, "baska")) is False
    assert whatsapp.verify_signature(raw, None) is False


def test_secret_yoksa_dev_gecer(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "")
    assert whatsapp.verify_signature(b"x", None) is True


def test_session_id_telefon_hashli():
    sid = whatsapp.session_id("905321112233")
    assert sid.startswith("wa-") and "905321112233" not in sid
