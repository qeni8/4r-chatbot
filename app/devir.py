"""Yetkiliye devir: bot cevaplayamadığında talebi kaydet, haber ver, iletişim topla.

Bot müşteriye "sizi yetkilimize aktarayım" diyor; bu modül olmadan bu söz boşta kalır.

Bildirim kuralı: hiçbir bildirim hatası müşteriye verilen cevabı düşürmez. Kanal
yapılandırılmamışsa kayıt yine tutulur ve yönetim panelinde görünür.
"""

import json
import logging
import smtplib
import threading
from email.message import EmailMessage

from app.config import settings
from app.db import get_conn
from app.sabitler import ILETISIM

log = logging.getLogger(__name__)

# Cevap metnindeki iz → devir sebebi. Sıra önemli (ilk eşleşen kazanır).
IZLER = [
    ("kesin bilgi veremiyorum", "bilgi_yok"),
    ("listemizde bulamadım", "kod_yok"),
    ("hiçbir tesisimizde kabul edemiyoruz", "kabul_edilmiyor"),
]
YONTEM_SEBEP = {"hata": "hata", "yogunluk": "hata", "kod_dogrulama": "bilgi_yok"}

SEBEP_ETIKET = {
    "bilgi_yok": "Bot cevabı bilmiyordu",
    "kod_yok": "Sorulan atık kodu listede yok",
    "kabul_edilmiyor": "Atık hiçbir tesiste kabul edilmiyor",
    "hata": "Teknik hata / model erişilemedi",
    "limit": "Mesaj sınırı doldu",
}


# --------------------------------------------------------------------------- bildirim


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
    from app import whatsapp

    if not (settings.bildirim_whatsapp and settings.whatsapp_access_token
            and settings.whatsapp_phone_number_id):
        return False
    whatsapp.send(settings.bildirim_whatsapp, f"*{baslik}*\n\n{govde}")
    return True


def bildir(baslik: str, govde: str) -> list[str]:
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


def _bildir_arkaplan(baslik: str, govde: str, geri_cagir=None) -> None:
    """Cevap gecikmesin diye ayrı iş parçacığında gönderir."""
    def _calis() -> None:
        kanallar = bildir(baslik, govde)
        if geri_cagir:
            try:
                geri_cagir(kanallar)
            except Exception:
                log.exception("Bildirim sonrası kayıt güncellenemedi")

    if settings.bildirim_arkaplan:
        threading.Thread(target=_calis, daemon=True).start()
    else:
        _calis()


# ------------------------------------------------------------------------------ devir


def sebep_bul(yontem: str, cevap: str) -> str | None:
    """Bu cevap bir devir mi? Değilse None."""
    dusuk = (cevap or "").lower()
    if yontem == "limit":
        # Oturum/ani yük redleri gürültü olur; yalnızca botun günlük kapasitesi
        # dolduğunda haber verilir (o zaman bot gerçekten kapanmış demektir).
        return "limit" if "kapasitemiz doldu" in dusuk else None
    if yontem in YONTEM_SEBEP:
        return YONTEM_SEBEP[yontem]
    for iz, sebep in IZLER:
        if iz in dusuk:
            return sebep
    return None


def kaydet(kanal: str, oturum_id: str | None, sebep: str, soru: str, cevap: str,
           gecmis: list[tuple[str, str]] | None = None) -> int | None:
    """Devri kaydeder ve yetkiliye bildirir. Kayıt id'sini döndürür."""
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "insert into devir_kayitlari (oturum_id, kanal, sebep, soru, cevap, gecmis) "
                "values (?, ?, ?, ?, ?, ?)",
                (oturum_id, kanal, sebep, soru, cevap,
                 json.dumps(gecmis or [], ensure_ascii=False)),
            )
            conn.commit()
            devir_id = cur.lastrowid
    except Exception:
        log.exception("Devir kaydı yazılamadı")
        return None

    _bildir_arkaplan(
        f"[4R Bot] Yanıtlanamayan soru — {SEBEP_ETIKET.get(sebep, sebep)}",
        _metin(devir_id, kanal, sebep, soru, cevap, gecmis),
        geri_cagir=lambda kanallar: _bildirim_isaretle(devir_id, kanallar),
    )
    return devir_id


def iletisim_ekle(devir_id: int, ad: str, telefon: str, eposta: str = "",
                  musteri_not: str = "") -> bool:
    """Müşteri iletişim bıraktığında kaydı tamamlar ve yetkiliye tekrar haber verir."""
    with get_conn() as conn:
        satir = conn.execute(
            "select soru, sebep from devir_kayitlari where id = ?", (devir_id,)
        ).fetchone()
        if not satir:
            return False
        conn.execute(
            "update devir_kayitlari set ad = ?, telefon = ?, eposta = ?, musteri_not = ? "
            "where id = ?",
            (ad, telefon, eposta, musteri_not, devir_id),
        )
        conn.commit()

    soru, sebep = satir
    _bildir_arkaplan(
        f"[4R Bot] GERİ DÖNÜŞ TALEBİ — {ad}",
        f"Müşteri geri dönüş istedi (talep #{devir_id}).\n\n"
        f"Ad     : {ad}\n"
        f"Telefon: {telefon}\n"
        f"E-posta: {eposta or '-'}\n"
        f"Not    : {musteri_not or '-'}\n\n"
        f"Sorusu : {soru}\n"
        f"Sebep  : {SEBEP_ETIKET.get(sebep, sebep)}\n",
    )
    return True


def _metin(devir_id: int | None, kanal: str, sebep: str, soru: str, cevap: str,
           gecmis: list[tuple[str, str]] | None) -> str:
    satirlar = [
        "Bot bir soruyu yanıtlayamadı ve müşteriyi yetkiliye yönlendirdi.",
        "",
        f"Talep no : #{devir_id}",
        f"Kanal    : {kanal}",
        f"Sebep    : {SEBEP_ETIKET.get(sebep, sebep)}",
        "",
        f"SORU:\n{soru}",
        "",
        f"BOTUN CEVABI:\n{cevap}",
    ]
    if gecmis:
        satirlar += ["", "ÖNCEKİ KONUŞMA:",
                     "\n".join(f"  M: {q}\n  B: {a}" for q, a in gecmis)]
    satirlar += ["", f"4R iletişim: {ILETISIM}"]
    return "\n".join(satirlar)


def _bildirim_isaretle(devir_id: int | None, kanallar: list[str]) -> None:
    if not devir_id:
        return
    with get_conn() as conn:
        conn.execute("update devir_kayitlari set bildirim = ? where id = ?",
                     (",".join(kanallar) or "-", devir_id))
        conn.commit()
