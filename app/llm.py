import time

import httpx

from app.config import settings

SISTEM = (
    "Sen 4R Çevre ve Enerji'nin müşteri destek asistanısın. SADECE sana verilen KAYNAKLAR "
    "bölümündeki bilgilere dayanarak cevap ver. Kaynaklarda olmayan hiçbir bilgiyi uydurma. "
    "Bilgi kaynaklarda yoksa veya emin değilsen aynen şunu söyle: 'Bu konuda kesin bilgi "
    "veremiyorum, sizi yetkilimize aktarayım. İletişim: +90 282 652 30 90, info@4r.com.tr'. "
    "Mevzuat/hukuki yorum yapma, 'bağlayıcı bilgi için yetkilimize danışın' de. "
    "Cevabın kısa, net, sıcak ve 'siz' dilinde olsun: önce net cevap, sonra varsa bir sonraki "
    "adım. Fiyat taahhüdü verme (mağaza/kılavuz fiyatı kaynakta varsa söyleyebilirsin)."
)


def _kaynak_blok(kaynaklar: list[dict]) -> str:
    return "\n\n".join(f"[{k['baslik']}]\n{k['icerik']}" for k in kaynaklar)


def _user_prompt(soru: str, kaynaklar: list[dict]) -> str:
    return f"KAYNAKLAR:\n{_kaynak_blok(kaynaklar)}\n\nSORU: {soru}"


def _gemini(soru: str, kaynaklar: list[dict]) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": SISTEM}]},
        "contents": [{"parts": [{"text": _user_prompt(soru, kaynaklar)}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.2},
    }
    for deneme, bekle in enumerate((0, 3, 8)):
        if bekle:
            time.sleep(bekle)
        r = httpx.post(
            url, headers={"x-goog-api-key": settings.gemini_api_key}, json=body, timeout=60
        )
        if r.status_code == 429 and deneme < 2:
            continue
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _anthropic(soru: str, kaynaklar: list[dict]) -> str:
    import anthropic

    cl = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = cl.messages.create(
        model=settings.llm_model_default,
        max_tokens=500,
        system=SISTEM,
        messages=[{"role": "user", "content": _user_prompt(soru, kaynaklar)}],
    )
    return msg.content[0].text.strip()


def answer(soru: str, kaynaklar: list[dict]) -> str:
    if settings.llm_provider == "anthropic":
        return _anthropic(soru, kaynaklar)
    return _gemini(soru, kaynaklar)
