import re

from app.db import get_conn

TESISLER = [("merkez", "Merkez"), ("luleburgaz", "Lüleburgaz"), ("kapakli", "Kapaklı")]
ILETISIM = "+90 282 652 30 90 / info@4r.com.tr"


def _digits(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")


def by_code(kod_temiz: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "select kod, tanim, tehlikeli, merkez, luleburgaz, kapakli "
            "from atik_kodlari where kod_temiz = %s",
            (kod_temiz,),
        ).fetchone()
    if not row:
        return None
    kod, tanim, tehlikeli, m, l, k = row
    tesisler = [ad for flag, (_, ad) in zip((m, l, k), TESISLER) if flag]
    return {"kod": kod, "tanim": tanim, "tehlikeli": tehlikeli, "tesisler": tesisler}


def by_group(prefix: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "select kod, tanim from atik_kodlari where kod_temiz like %s order by kod_temiz",
            (prefix + "%",),
        ).fetchall()
    return [{"kod": k, "tanim": t} for k, t in rows]


def by_name(term: str, limit: int = 8) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "select kod, tanim, merkez, luleburgaz, kapakli from atik_kodlari "
            "where tanim ilike %s order by kod_temiz limit %s",
            (f"%{term}%", limit),
        ).fetchall()
    return [
        {"kod": k, "tanim": t, "tesisler": [ad for f, (_, ad) in zip((m, l, kp), TESISLER) if f]}
        for k, t, m, l, kp in rows
    ]


_ISIM_STOP = set(
    "atık atığı atığını atıklar alıyor alır alıp kabul ediyor musunuz var hizmet gönder".split()
)


def name_context(mesaj: str, limit: int = 6) -> dict | None:
    """Atık adıyla tabloda eşleşen kodları RAG kaynağı olarak döndürür (modele grounding)."""
    kelimeler = [w for w in re.findall(r"\w+", mesaj.lower()) if len(w) > 3 and w not in _ISIM_STOP]
    if not kelimeler:
        return None
    kosul = " or ".join(["tanim ilike %s"] * len(kelimeler))
    with get_conn() as conn:
        rows = conn.execute(
            f"select kod, tanim, merkez, luleburgaz, kapakli from atik_kodlari where {kosul} limit 40",
            [f"%{w}%" for w in kelimeler],
        ).fetchall()
    if not rows:
        return None

    def skor(tanim: str) -> int:
        return sum(1 for w in kelimeler if w in tanim.lower())

    rows = sorted(rows, key=lambda r: skor(r[1]), reverse=True)[:limit]
    satir = []
    for kod, tanim, m, l, k in rows:
        tes = [ad for f, (_, ad) in zip((m, l, k), TESISLER) if f] or ["hiçbir tesiste kabul edilmiyor"]
        satir.append(f"- {kod} — {tanim} — kabul: {', '.join(tes)}")
    return {
        "baslik": "Atık kodu tablosu (isimle eşleşen kodlar)",
        "kaynak": "atik_kodlari",
        "icerik": "İsimle eşleşen atık kodları ve kabul edildiği tesisler:\n" + "\n".join(satir),
    }


def answer(text: str) -> str:
    """Atık kodu sorusuna deterministik (modelsiz) Türkçe cevap."""
    d = _digits(text)

    if len(d) == 6:
        r = by_code(d)
        if not r:
            return (f"Bu atık kodunu ({d}) listemizde bulamadım. Kodu kontrol edebilir "
                    f"ya da yetkilimize danışabilirsiniz: {ILETISIM}")
        th = " Tehlikeli atık sınıfındadır." if r["tehlikeli"] else ""
        bilgi = f"{r['kod']} — {r['tanim']}."
        if r["tesisler"]:
            yer = " ve ".join(r["tesisler"])
            sonek = "tesislerimizde" if len(r["tesisler"]) > 1 else "tesisimizde"
            return (f"{bilgi}\n\nEvet ✅ bu atığı **{yer}** {sonek} alıyoruz.{th} "
                    f"Göndermek isterseniz süreci anlatabilirim.")
        return (f"{bilgi}\n\nBu atığı şu an hiçbir tesisimizde kabul edemiyoruz.{th} "
                f"Dilerseniz sizi yetkilimize aktarayım: {ILETISIM}")

    if len(d) in (2, 4):
        kodlar = by_group(d)
        if not kodlar:
            return f"{d} grubunda kayıtlı kod bulamadım. Yetkilimize danışabilirsiniz: {ILETISIM}"
        if len(kodlar) > 8:
            return (f"{d} grubunda {len(kodlar)} atık kodu var. Hangi atıktan bahsettiğinizi "
                    f"yazarsanız net cevap verebilirim.")
        satir = "\n".join(f"• {x['kod']} — {x['tanim']}" for x in kodlar)
        return f"{d} grubundaki kodlar:\n{satir}\nHangisini soruyorsunuz?"

    return ""  # kod değil → çağıran katman RAG'e yönlendirir
