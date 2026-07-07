import re

from app.db import get_conn
from app.router import CODE4, CODE6

TESISLER = [("merkez", "Merkez"), ("luleburgaz", "Lüleburgaz"), ("kapakli", "Kapaklı")]
ILETISIM = "+90 282 652 30 90 / info@4r.com.tr"


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


def name_context(mesaj: str, limit: int = 6, havuz: int = 20) -> dict | None:
    """Atık adıyla eşleşen kodları RAG kaynağı olarak döndürür (semantik + kelime, RRF)."""
    from pgvector import Vector
    from pgvector.psycopg import register_vector

    from app.embeddings import embed_query

    kelimeler = [w for w in re.findall(r"\w+", mesaj.lower()) if len(w) > 3 and w not in _ISIM_STOP]
    vec = Vector(embed_query(mesaj))
    with get_conn() as conn:
        register_vector(conn)
        sem = [
            r[0]
            for r in conn.execute(
                "select id from atik_kodlari where embedding is not null "
                "order by embedding <=> %s limit %s",
                (vec, havuz),
            ).fetchall()
        ]
        lex = []
        if kelimeler:
            kosul = " or ".join(["tanim ilike %s"] * len(kelimeler))
            lex = [
                r[0]
                for r in conn.execute(
                    f"select id from atik_kodlari where {kosul} limit %s",
                    [f"%{w}%" for w in kelimeler] + [havuz],
                ).fetchall()
            ]

    skor: dict[int, float] = {}
    for liste in (sem, lex):
        for rank, cid in enumerate(liste):
            skor[cid] = skor.get(cid, 0.0) + 1.0 / (60 + rank)
    top = sorted(skor, key=lambda c: skor[c], reverse=True)[:limit]
    if not top:
        return None

    with get_conn() as conn:
        rows = conn.execute(
            "select kod, tanim, merkez, luleburgaz, kapakli from atik_kodlari where id = any(%s)",
            (top,),
        ).fetchall()
    satir = []
    for kod, tanim, m, l, k in rows:
        tes = [ad for f, (_, ad) in zip((m, l, k), TESISLER) if f] or ["hiçbir tesiste kabul edilmiyor"]
        satir.append(f"- {kod} — {tanim} — kabul: {', '.join(tes)}")
    return {
        "baslik": "Atık kodu tablosu (isimle eşleşen kodlar)",
        "kaynak": "atik_kodlari",
        "icerik": "İsimle eşleşen atık kodları ve kabul edildiği tesisler:\n" + "\n".join(satir),
    }


def _answer_code(kod_temiz: str) -> str:
    r = by_code(kod_temiz)
    if not r:
        return (f"Bu atık kodunu ({kod_temiz}) listemizde bulamadım. Kodu kontrol edebilir "
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


def _answer_group(prefix: str) -> str:
    kodlar = by_group(prefix)
    if not kodlar:
        return ""
    if len(kodlar) > 8:
        return (f"{prefix} grubunda {len(kodlar)} atık kodu var. Hangi atıktan bahsettiğinizi "
                f"yazarsanız net cevap verebilirim.")
    satir = "\n".join(f"• {x['kod']} — {x['tanim']}" for x in kodlar)
    return f"{prefix} grubundaki kodlar:\n{satir}\nHangisini soruyorsunuz?"


def _kodlar6(text: str) -> list[str]:
    out, seen = [], set()
    for m in CODE6.findall(text):
        k = "".join(m)
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _gruplar4(text: str) -> list[str]:
    out, seen = [], set()
    for m in CODE4.findall(text):
        k = "".join(m)
        if k not in seen and 1 <= int(k[:2]) <= 20:  # geçerli atık bölümü 01-20 (telefon vb. eler)
            seen.add(k)
            out.append(k)
    return out


def answer(text: str) -> str:
    """Atık kodu sorusuna deterministik (modelsiz) cevap; çoklu kod ve gürültü toleranslı."""
    kodlar = _kodlar6(text)
    if kodlar:
        return "\n\n".join(_answer_code(k) for k in kodlar[:3])
    for grup in _gruplar4(text):
        cevap = _answer_group(grup)
        if cevap:
            return cevap
    return ""  # kod yok → çağıran katman RAG'e (isimle arama) yönlendirir
