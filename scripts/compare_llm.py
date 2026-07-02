"""Aynı soruları Claude Haiku ve Gemini Flash'a sorup cevapları yan yana gösterir.

Amaç: grounding/uydurmama/Türkçe/ton kalitesini göz kararıyla kıyaslamak.
Retrieval şimdilik basit kelime eşleşmesi (kıyas için adil — iki modele de aynı kaynak gider).
Embedding/semantik arama karardan sonra kurulacak.

Kullanım:
    python scripts/compare_llm.py
"""

import re
import sys
import textwrap

import httpx

sys.path.insert(0, ".")
from app.config import settings
from app.db import get_conn, pool

SORULAR = [
    "Lisanslı vidanjör hizmetiniz var mı?",
    "50 kg altı atık nasıl gönderilir, fiyatı ne kadar?",
    "Solvent geri kazanımı yapıyor musunuz?",
    "Hangi şehirlerde tesisiniz var?",
    "Kaç firmaya hizmet veriyorsunuz?",
    "Atık su arıtma hizmetiniz nasıl çalışıyor?",
    "Lisans belgeleriniz neler?",
    "Cumartesi günü açık mısınız?",
]

SISTEM = (
    "Sen 4R Çevre ve Enerji'nin müşteri destek asistanısın. SADECE sana verilen "
    "KAYNAKLAR bölümündeki bilgilere dayanarak cevap ver. Kaynaklarda olmayan hiçbir "
    "bilgiyi uydurma. Bilgi kaynaklarda yoksa veya emin değilsen aynen şunu söyle: "
    "'Bu konuda kesin bilgi veremiyorum, sizi yetkilimize aktarayım. "
    "İletişim: +90 282 652 30 90, info@4r.com.tr'. "
    "Cevabın kısa, net, sıcak ve 'siz' dilinde olsun: önce net cevap, sonra varsa bir "
    "sonraki adım. Fiyat taahhüdü verme (mağaza/kılavuz fiyatı kaynakta varsa söyleyebilirsin)."
)

STOP = set("ve ile mi mı mu mü var yok ne nasıl kaç hangi için bir bu şu o da de".split())


def kelimeler(s: str) -> set[str]:
    return {w for w in re.findall(r"\w+", s.lower()) if len(w) > 3 and w not in STOP}


def getir(soru: str, k: int = 4) -> list[tuple[str, str]]:
    qk = kelimeler(soru)
    with get_conn() as conn:
        rows = conn.execute(
            "select d.baslik, c.icerik from chunks c join documents d on d.id = c.document_id"
        ).fetchall()
    skorlu = sorted(rows, key=lambda r: len(qk & kelimeler(r[1])), reverse=True)
    return [(b, i) for b, i in skorlu if qk & kelimeler(i)][:k] or skorlu[:1]


def prompt_user(soru: str, kaynaklar: list[tuple[str, str]]) -> str:
    blok = "\n\n".join(f"[{b}]\n{i}" for b, i in kaynaklar)
    return f"KAYNAKLAR:\n{blok}\n\nSORU: {soru}"


def claude(soru: str, kaynaklar: list[tuple[str, str]]) -> str:
    if not settings.anthropic_api_key:
        return "(ANTHROPIC_API_KEY yok — atlandı)"
    import anthropic

    cl = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = cl.messages.create(
        model=settings.llm_model_default,
        max_tokens=400,
        system=SISTEM,
        messages=[{"role": "user", "content": prompt_user(soru, kaynaklar)}],
    )
    return msg.content[0].text.strip()


def gemini(soru: str, kaynaklar: list[tuple[str, str]]) -> str:
    if not settings.gemini_api_key:
        return "(GEMINI_API_KEY yok — atlandı)"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": SISTEM}]},
        "contents": [{"parts": [{"text": prompt_user(soru, kaynaklar)}]}],
        "generationConfig": {"maxOutputTokens": 400},
    }
    r = httpx.post(url, headers={"x-goog-api-key": settings.gemini_api_key}, json=body, timeout=60)
    if r.status_code != 200:
        return f"(Gemini hata {r.status_code}: {r.text[:200]})"
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def main() -> None:
    pool.open()
    for i, soru in enumerate(SORULAR, 1):
        kaynaklar = getir(soru)
        kayn = ", ".join(b for b, _ in kaynaklar)
        print(f"\n{'='*78}\nSORU {i}: {soru}\n  (kaynak: {kayn})\n{'-'*78}")
        for ad, fn in (("CLAUDE HAIKU", claude), ("GEMINI FLASH", gemini)):
            try:
                cevap = fn(soru, kaynaklar)
            except Exception as e:  # noqa: BLE001
                cevap = f"(hata: {e})"
            print(f"\n▶ {ad}:\n{textwrap.indent(cevap, '   ')}")
    pool.close()


if __name__ == "__main__":
    main()
