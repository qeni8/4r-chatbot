"""Meta WhatsApp Cloud API adaptörü (BSP'siz, doğrudan).

Webhook doğrulama + gelen metin mesajını ayrıştırma + cevap gönderme.
KVKK: log için telefon numarası ham değil, hash'lenmiş oturum kimliği kullanılır.
"""

import hashlib
import hmac
import logging
import re

import httpx

from app.config import settings

GRAPH = "https://graph.facebook.com/v22.0"
log = logging.getLogger(__name__)


def verify(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    if mode == "subscribe" and token and token == settings.whatsapp_verify_token:
        return challenge
    return None


def verify_signature(raw: bytes, signature: str | None) -> bool:
    """Gelen webhook'un Meta'dan geldiğini X-Hub-Signature-256 ile doğrular."""
    secret = settings.whatsapp_app_secret
    if not secret:
        # Prod'da secret yoksa webhook herkese açık olurdu → reddet. Yalnızca dev'de atlanır.
        if settings.app_env == "dev":
            log.warning("WHATSAPP_APP_SECRET boş — imza doğrulaması atlandı (dev)")
            return True
        log.error("WHATSAPP_APP_SECRET ayarlı değil — webhook isteği reddedildi")
        return False
    if not signature or not signature.startswith("sha256="):
        return False
    beklenen = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(beklenen, signature)


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
    try:
        r = httpx.post(
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
        r.raise_for_status()
    except httpx.HTTPError:
        # Sessiz kalırsa müşteri cevapsız kalır ve log'da başarılı görünür — mutlaka kaydet.
        log.exception("WhatsApp mesajı gönderilemedi")
