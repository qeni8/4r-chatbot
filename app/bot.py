import json
import logging
import re
from functools import partial

from app import devir, limits, llm, router, waste_lookup
from app.config import settings
from app.db import get_conn
from app.sabitler import DEVIR, YOGUNLUK

log = logging.getLogger(__name__)

# Atık adıyla "alıyor musunuz / kabul" niyeti → tablo eşleşmesini modele kaynak olarak ver.
KABUL_INTENT = re.compile(r"al[ıi]yor|al[ıi]r\s*m|kabul|at[ıi]ğ[ıi]|at[ıi]k", re.IGNORECASE)

MAX_INPUT = 1500  # aşırı uzun/kötüye kullanım girdisini kırp (token koruması)
BOS = "Bir sorunuzu yazabilir misiniz? Atık kodu, hizmet veya gönderim hakkında sorabilirsiniz."

# Sadece selam/teşekkür (gerçek soru içermeyen) → modelsiz, anında yanıt.
SELAM = re.compile(
    r"^(merhaba|selam(lar)?|iyi günler|iyi akşamlar|günaydın|kolay gelsin|s\.a)[\s!.]*$",
    re.IGNORECASE,
)
TESEKKUR = re.compile(
    r"^(teşekkür(ler)?|teşekkür ederim|çok teşekkürler|sağ ?ol(un)?|eyvallah)[\s!.]*$",
    re.IGNORECASE,
)
SELAM_CEVAP = ("Merhaba! Size nasıl yardımcı olabilirim? Atık kodu, hizmetlerimiz veya "
               "gönderim hakkında sorabilirsiniz.")
TESEKKUR_CEVAP = "Rica ederim! Başka bir sorunuz olursa buradayım."

# Bu yöntemler hafızaya alınmaz: bilgi taşımaz ya da hatalı cevaptır (promptu kirletir).
HAFIZA_DISI = ("limit", "hata", "yogunluk", "selam", "kod_dogrulama")


def _log(kanal: str, oturum_id: str | None, soru: str, cevap: str,
         yontem: str, kaynaklar: list[str], model: str, istemci: str | None = None) -> None:
    try:
        with get_conn() as conn:
            conn.execute(
                "insert into konusma_loglari "
                "(kanal, oturum_id, istemci, soru, cevap, yontem, kaynaklar, model) "
                "values (?, ?, ?, ?, ?, ?, ?, ?)",
                (kanal, oturum_id, istemci, soru, cevap, yontem,
                 json.dumps(kaynaklar, ensure_ascii=False), model),
            )
            conn.commit()
    except Exception:
        log.exception("Konuşma logu yazılamadı")


def _gecmis(oturum_id: str | None) -> list[tuple[str, str]]:
    if not oturum_id:
        return []
    yer = ",".join("?" * len(HAFIZA_DISI))
    with get_conn() as conn:
        rows = conn.execute(
            f"select soru, cevap from konusma_loglari where oturum_id = ? "
            f"and yontem not in ({yer}) "
            f"and created_at >= datetime('now', ?) order by id desc limit ?",
            (oturum_id, *HAFIZA_DISI, f"-{settings.gecmis_dakika} minutes",
             settings.gecmis_turu),
        ).fetchall()
    return [(s, c) for s, c in reversed(rows)]


def _sonuc(answer: str, method: str, sources: list[str], devir_id: int | None = None) -> dict:
    return {"answer": answer, "method": method, "sources": sources, "devir_id": devir_id}


def reply(mesaj: str, oturum_id: str | None, kanal: str = "web",
          istemci: str | None = None) -> dict:
    mesaj = (mesaj or "").strip()
    if not mesaj:
        return _sonuc(BOS, "bos", [])
    if len(mesaj) > MAX_INPUT:
        mesaj = mesaj[:MAX_INPUT]

    kaydet = partial(_log, kanal, oturum_id, istemci=istemci)
    gecmis = _gecmis(oturum_id)

    def bitir(cevap: str, yontem: str, kaynaklar: list[str], model: str = "-") -> dict:
        """Tek çıkış noktası: logla, gerekiyorsa yetkiliye devir kaydı aç ve bildir."""
        kaydet(mesaj, cevap, yontem, kaynaklar, model)
        sebep = devir.sebep_bul(yontem, cevap)
        devir_id = (devir.kaydet(kanal, oturum_id, sebep, mesaj, cevap, gecmis)
                    if sebep else None)
        return _sonuc(cevap, yontem, kaynaklar, devir_id)

    izin, uyari = limits.check(oturum_id, istemci)
    if not izin:
        return bitir(uyari, "limit", [])

    for kalip, cevap in ((SELAM, SELAM_CEVAP), (TESEKKUR, TESEKKUR_CEVAP)):
        if kalip.match(mesaj):
            return bitir(cevap, "selam", [])

    ek_kaynaklar: list[dict] = []
    kesin = ""

    tur, kod = router.kod_bul(mesaj)
    if tur:
        kesin = waste_lookup.answer(mesaj)
        if kesin and router.sadece_kabul(mesaj):
            # Saf "bu kodu alıyor musunuz" → modele hiç uğramadan kesin cevap.
            return bitir(kesin, "atik_kodu", [])
        if kesin:
            # Kod + başka soru (fiyat/gönderim/süreç) → tablo sonucu modele kaynak olur.
            ek_kaynaklar.append(
                waste_lookup.code_context(kod)
                or {"baslik": "Atık kodu tablosu", "icerik": kesin}
            )
    elif KABUL_INTENT.search(mesaj):
        tablo = waste_lookup.name_context(mesaj)
        if tablo:
            ek_kaynaklar.append(tablo)

    kaynak_adlari = [k["baslik"] for k in ek_kaynaklar] or ["4R web sitesi"]
    try:
        cevap, model = llm.answer(mesaj, ek_kaynaklar, gecmis)
    except llm.LLMRateLimit:
        log.warning("LLM kota limiti — kullanıcı yetkiliye yönlendirildi", exc_info=True)
        return bitir(YOGUNLUK, "yogunluk", kaynak_adlari, settings.llm_provider)
    except Exception:
        log.exception("LLM cevabı üretilemedi")
        return bitir(DEVIR, "hata", kaynak_adlari, settings.llm_provider)

    # Son denetim: model tabloda olmayan bir atık kodu yazdıysa cevabı kullanıcıya gönderme.
    uydurma = waste_lookup.gecersiz_kodlar(cevap)
    if uydurma:
        log.error("Model tabloda olmayan atık kodu üretti: %s | soru: %r", uydurma, mesaj)
        return bitir(kesin or DEVIR, "kod_dogrulama", kaynak_adlari, model)

    return bitir(cevap, "rag", kaynak_adlari, model)
