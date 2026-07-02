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


def _gemini(soru: str, kaynaklar: list[dict], gecmis: list[tuple[str, str]]) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    contents = []
    for q, a in gecmis:
        contents.append({"role": "user", "parts": [{"text": q}]})
        contents.append({"role": "model", "parts": [{"text": a}]})
    contents.append({"role": "user", "parts": [{"text": _user_prompt(soru, kaynaklar)}]})
    body = {
        "system_instruction": {"parts": [{"text": SISTEM}]},
        "contents": contents,
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


def _groq(soru: str, kaynaklar: list[dict], gecmis: list[tuple[str, str]]) -> str:
    mesajlar = [{"role": "system", "content": SISTEM}]
    for q, a in gecmis:
        mesajlar.append({"role": "user", "content": q})
        mesajlar.append({"role": "assistant", "content": a})
    mesajlar.append({"role": "user", "content": _user_prompt(soru, kaynaklar)})
    body = {
        "model": settings.groq_model,
        "messages": mesajlar,
        "max_tokens": 500,
        "temperature": 0.2,
    }
    for deneme, bekle in enumerate((0, 3, 8)):
        if bekle:
            time.sleep(bekle)
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json=body,
            timeout=60,
        )
        if r.status_code == 429 and deneme < 2:
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _anthropic(soru: str, kaynaklar: list[dict], gecmis: list[tuple[str, str]]) -> str:
    import anthropic

    cl = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    mesajlar = []
    for q, a in gecmis:
        mesajlar.append({"role": "user", "content": q})
        mesajlar.append({"role": "assistant", "content": a})
    mesajlar.append({"role": "user", "content": _user_prompt(soru, kaynaklar)})
    msg = cl.messages.create(
        model=settings.llm_model_default, max_tokens=500, system=SISTEM, messages=mesajlar
    )
    return msg.content[0].text.strip()


def answer(soru: str, kaynaklar: list[dict], gecmis: list[tuple[str, str]] | None = None) -> str:
    gecmis = gecmis or []
    if settings.llm_provider == "anthropic":
        return _anthropic(soru, kaynaklar, gecmis)
    if settings.llm_provider == "gemini":
        return _gemini(soru, kaynaklar, gecmis)
    return _groq(soru, kaynaklar, gecmis)
