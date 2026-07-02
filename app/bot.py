import json

from app import limits, llm, retrieval, router, waste_lookup
from app.config import settings
from app.db import get_conn

DEVIR = ("Şu an yoğunluktan yanıt veremedim, sizi yetkilimize aktarayım. "
         "İletişim: +90 282 652 30 90, info@4r.com.tr")


def _log(kanal: str, oturum_id: str | None, soru: str, cevap: str,
         yontem: str, kaynaklar: list[str], model: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "insert into konusma_loglari (kanal, oturum_id, soru, cevap, yontem, kaynaklar, model) "
            "values (%s, %s, %s, %s, %s, %s, %s)",
            (kanal, oturum_id, soru, cevap, yontem,
             json.dumps(kaynaklar, ensure_ascii=False), model),
        )
        conn.commit()


def reply(mesaj: str, oturum_id: str | None, kanal: str = "web") -> dict:
    izin, uyari = limits.check(oturum_id)
    if not izin:
        _log(kanal, oturum_id, mesaj, uyari, "limit", [], "-")
        return {"answer": uyari, "method": "limit", "sources": []}

    if router.route(mesaj) == "atik_kodu":
        cevap = waste_lookup.answer(mesaj)
        if cevap:
            _log(kanal, oturum_id, mesaj, cevap, "atik_kodu", [], "-")
            return {"answer": cevap, "method": "atik_kodu", "sources": []}

    kaynaklar = retrieval.search(mesaj)
    basliklar = list(dict.fromkeys(k["baslik"] for k in kaynaklar))
    try:
        cevap = llm.answer(mesaj, kaynaklar)
    except Exception:  # noqa: BLE001 — model/ağ sınırı; güvenli tarafa al
        _log(kanal, oturum_id, mesaj, DEVIR, "rag_hata", basliklar, settings.llm_provider)
        return {"answer": DEVIR, "method": "rag_hata", "sources": basliklar}

    _log(kanal, oturum_id, mesaj, cevap, "rag", basliklar, settings.llm_provider)
    return {"answer": cevap, "method": "rag", "sources": basliklar}
