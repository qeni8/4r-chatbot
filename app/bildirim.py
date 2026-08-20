"""Yetkiliye bildirim gönderimi (e-posta + WhatsApp).

Tasarım kuralı: bildirim ASLA müşteriye verilen cevabı düşürmez. Her kanal kendi
içinde hata yakalar; hiçbir kanal yapılandırılmamışsa kayıt yine tutulur ve loglanır.
"""

import logging
import smtplib
import threading
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger(__name__)


def _eposta_gonder(baslik: str, govde: str) -> bool:
    if not (settings.smtp_host and settings.bildirim_eposta):
        return False
    alicilar = [a.strip() for a in settings.bildirim_eposta.split(",") if a.strip()]
    if not alicilar:
        return False

    msg = EmailMessage()
    msg["Subject"] = baslik
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = ", ".join(alicilar)
    msg.set_content(govde)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
        if settings.smtp_tls:
            s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)
    return True


def _whatsapp_gonder(baslik: str, govde: str) -> bool:
    if not settings.bildirim_whatsapp:
        return False
    from app import whatsapp

    if not (settings.whatsapp_access_token and settings.whatsapp_phone_number_id):
        return False
    whatsapp.send(settings.bildirim_whatsapp, f"*{baslik}*\n\n{govde}")
    return True


def gonder(baslik: str, govde: str) -> list[str]:
    """Yapılandırılmış tüm kanallara gönderir; başarılı kanalların adını döndürür."""
    basarili: list[str] = []
    for ad, fn in (("eposta", _eposta_gonder), ("whatsapp", _whatsapp_gonder)):
        try:
            if fn(baslik, govde):
                basarili.append(ad)
        except Exception:
            log.exception("Bildirim gönderilemedi: %s", ad)
    if not basarili:
        log.warning("Bildirim kanalı yapılandırılmamış — yalnızca kayıt tutuldu: %s", baslik)
    return basarili


def gonder_arkaplan(baslik: str, govde: str, geri_cagir=None) -> None:
    """Cevap gecikmesin diye ayrı iş parçacığında gönderir."""
    def _calis() -> None:
        kanallar = gonder(baslik, govde)
        if geri_cagir:
            try:
                geri_cagir(kanallar)
            except Exception:
                log.exception("Bildirim sonrası kayıt güncellenemedi")

    if settings.bildirim_arkaplan:
        threading.Thread(target=_calis, daemon=True).start()
    else:
        _calis()
