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


def answer(text: str) -> str:
    """Atık kodu sorusuna deterministik (modelsiz) Türkçe cevap."""
    d = _digits(text)

    if len(d) == 6:
        r = by_code(d)
        if not r:
            return (f"Bu atık kodunu ({d}) listemizde bulamadım. Kodu kontrol edebilir "
                    f"ya da yetkilimize danışabilirsiniz: {ILETISIM}")
        th = " (Tehlikeli atık sınıfında.)" if r["tehlikeli"] else ""
        if r["tesisler"]:
            yer = " ve ".join(r["tesisler"])
            return (f"Evet ✅ {r['kod']} kodlu atığı **{yer}** tesisimizde alıyoruz.{th} "
                    f"Göndermek isterseniz süreci anlatabilirim.")
        return (f"{r['kod']} kodlu atığı şu an hiçbir tesisimizde kabul edemiyoruz.{th} "
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
