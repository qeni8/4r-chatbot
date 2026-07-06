import json
import re

from app import limits, llm, retrieval, router, waste_lookup
from app.config import settings
from app.db import get_conn

# Atık adıyla "alıyor musunuz / kabul" niyeti → tablo eşleşmesini modele kaynak olarak ver.
KABUL_INTENT = re.compile(r"al[ıi]yor|al[ıi]r\s*m|kabul|at[ıi]ğ[ıi]", re.IGNORECASE)

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


def _gecmis(oturum_id: str | None, n: int = 3) -> list[tuple[str, str]]:
    if not oturum_id:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            "select soru, cevap from konusma_loglari where oturum_id = %s and yontem <> 'limit' "
            "and created_at > now() - interval '2 hours' order by id desc limit %s",
            (oturum_id, n),
        ).fetchall()
    return [(s, c) for s, c in reversed(rows)]


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
    if KABUL_INTENT.search(mesaj):
        tablo = waste_lookup.name_context(mesaj)
        if tablo:
            kaynaklar = [tablo, *kaynaklar]
    basliklar = list(dict.fromkeys(k["baslik"] for k in kaynaklar))
    try:
        cevap, model = llm.answer(mesaj, kaynaklar, _gecmis(oturum_id))
    except Exception:  # noqa: BLE001 — model/ağ sınırı; güvenli tarafa al
        _log(kanal, oturum_id, mesaj, DEVIR, "rag_hata", basliklar, settings.llm_provider)
        return {"answer": DEVIR, "method": "rag_hata", "sources": basliklar}

    _log(kanal, oturum_id, mesaj, cevap, "rag", basliklar, model)
    return {"answer": cevap, "method": "rag", "sources": basliklar}
