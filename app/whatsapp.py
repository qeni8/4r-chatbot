"""Meta WhatsApp Cloud API adaptörü (BSP'siz, doğrudan).

Webhook doğrulama + gelen metin mesajını ayrıştırma + cevap gönderme.
KVKK: log için telefon numarası ham değil, hash'lenmiş oturum kimliği kullanılır.
"""

import hashlib
import re

import httpx

from app.config import settings

GRAPH = "https://graph.facebook.com/v22.0"


def verify(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    if mode == "subscribe" and token and token == settings.whatsapp_verify_token:
        return challenge
    return None


def session_id(phone: str) -> str:
    return "wa-" + hashlib.sha256(phone.encode()).hexdigest()[:16]


def parse(payload: dict) -> list[dict]:
    """Gelen webhook payload'ından metin mesajlarını çıkarır: [{'from':..., 'text':...}]."""
    out: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []):
                if m.get("type") == "text":
                    out.append({"from": m["from"], "text": m["text"]["body"]})
    return out


def _wa_bicim(metin: str) -> str:
    # WhatsApp kalın: tek yıldız. Bizim **kalın** → *kalın*.
    return re.sub(r"\*\*(.+?)\*\*", r"*\1*", metin)


def send(to: str, metin: str) -> None:
    if not (settings.whatsapp_access_token and settings.whatsapp_phone_number_id):
        return  # token yoksa (dev) sessizce geç
    httpx.post(
        f"{GRAPH}/{settings.whatsapp_phone_number_id}/messages",
        headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": _wa_bicim(metin)},
        },
        timeout=30,
    )
