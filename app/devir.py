"""Yetkiliye devir kayıtları: bot cevaplayamadığında talebi kaydet ve haber ver.

Bot müşteriye "sizi yetkilimize aktarayım" diyor; bu modül olmadan bu söz boşta kalır.
"""

import json
import logging

from app import bildirim
from app.db import get_conn
from app.sabitler import ILETISIM

log = logging.getLogger(__name__)

# Cevap metnindeki iz → devir sebebi. Sıra önemli (ilk eşleşen kazanır).
IZLER = [
    ("kesin bilgi veremiyorum", "bilgi_yok"),
    ("listemizde bulamadım", "kod_yok"),
    ("hiçbir tesisimizde kabul edemiyoruz", "kabul_edilmiyor"),
]
YONTEM_SEBEP = {"hata": "hata", "yogunluk": "hata", "limit": "limit",
                "kod_dogrulama": "bilgi_yok"}

SEBEP_ETIKET = {
    "bilgi_yok": "Bot cevabı bilmiyordu",
    "kod_yok": "Sorulan atık kodu listede yok",
    "kabul_edilmiyor": "Atık hiçbir tesiste kabul edilmiyor",
    "hata": "Teknik hata / model erişilemedi",
    "limit": "Mesaj sınırı doldu",
}


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

    bildirim.gonder_arkaplan(
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
            "select soru, sebep, kanal from devir_kayitlari where id = ?", (devir_id,)
        ).fetchone()
        if not satir:
            return False
        conn.execute(
            "update devir_kayitlari set ad = ?, telefon = ?, eposta = ?, musteri_not = ? "
            "where id = ?",
            (ad, telefon, eposta, musteri_not, devir_id),
        )
        conn.commit()

    soru, sebep, _kanal = satir
    govde = (
        f"Müşteri geri dönüş istedi (talep #{devir_id}).\n\n"
        f"Ad     : {ad}\n"
        f"Telefon: {telefon}\n"
        f"E-posta: {eposta or '-'}\n"
        f"Not    : {musteri_not or '-'}\n\n"
        f"Sorusu : {soru}\n"
        f"Sebep  : {SEBEP_ETIKET.get(sebep, sebep)}\n"
    )
    bildirim.gonder_arkaplan(f"[4R Bot] GERİ DÖNÜŞ TALEBİ — {ad}", govde)
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
        onceki = "\n".join(f"  M: {q}\n  B: {a}" for q, a in gecmis)
        satirlar += ["", "ÖNCEKİ KONUŞMA:", onceki]
    satirlar += ["", f"4R iletişim: {ILETISIM}"]
    return "\n".join(satirlar)


def _bildirim_isaretle(devir_id: int | None, kanallar: list[str]) -> None:
    if not devir_id:
        return
    with get_conn() as conn:
        conn.execute("update devir_kayitlari set bildirim = ? where id = ?",
                     (",".join(kanallar) or "-", devir_id))
        conn.commit()
