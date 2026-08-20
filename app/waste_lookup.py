"""Atık kodu tablosu — deterministik sorgu (modele uğramaz, uydurma riski sıfır).

CLAUDE.md Bölüm 5 + 13: kabul/red yalnızca 6 haneli kodlardan; isimle aramada
birden çok eşleşme varsa bot SORAR, koda model karar vermez.
"""

import difflib
import re
from functools import lru_cache

from app.db import get_conn
from app.sabitler import ILETISIM, TESISLER

# Türkçe harf katlaması — yazım hatası ve şapkalı harf toleransı için.
_KATLA = str.maketrans("çğıöşüâîû", "cgiosuaiu")

_ISIM_STOP = {
    "alıyor", "aliyor", "alır", "alir", "musunuz", "misiniz", "kabul", "ediyor",
    "atık", "atik", "atığı", "atigi", "atığım", "var", "yok", "için", "icin",
    "nedir", "hangi", "nasıl", "nasil", "bana", "bir", "olan", "eder", "misin",
}
BENZERLIK_ESIGI = 0.72


def normalize(s: str) -> str:
    return (s or "").casefold().translate(_KATLA)


def _kokler(mesaj: str) -> list[str]:
    """Sorgu kelimelerini kaba köklere indirger (Türkçe ek toleransı)."""
    kokler = []
    for w in re.findall(r"\w+", normalize(mesaj)):
        if len(w) < 4 or w in _ISIM_STOP:
            continue
        kokler.append(w[: max(4, len(w) - 2)])
    return kokler


def digits(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")


def _tesisler(m: int, l: int, k: int) -> list[str]:
    return [ad for bayrak, (_, ad) in zip((m, l, k), TESISLER) if bayrak]


@lru_cache(maxsize=1)
def _tum_kodlar() -> list[dict]:
    """842 satır — isimle arama için bellekte tutulur (tablo küçük)."""
    with get_conn() as conn:
        rows = conn.execute(
            "select kod, tanim, tehlikeli, merkez, luleburgaz, kapakli from atik_kodlari"
        ).fetchall()
    return [
        {
            "kod": kod,
            "tanim": tanim or "",
            "tehlikeli": bool(teh),
            "tesisler": _tesisler(m, l, k),
            "norm": normalize(tanim or ""),
        }
        for kod, tanim, teh, m, l, k in rows
    ]


def by_code(kod_temiz: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "select kod, tanim, tehlikeli, merkez, luleburgaz, kapakli "
            "from atik_kodlari where kod_temiz = ?",
            (kod_temiz,),
        ).fetchone()
    if not row:
        return None
    kod, tanim, teh, m, l, k = row
    return {"kod": kod, "tanim": tanim, "tehlikeli": bool(teh), "tesisler": _tesisler(m, l, k)}


def by_group(prefix: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "select kod, tanim from atik_kodlari where kod_temiz like ? order by kod_temiz",
            (prefix + "%",),
        ).fetchall()
    return [{"kod": k, "tanim": t} for k, t in rows]


def by_name(mesaj: str, limit: int = 8) -> list[dict]:
    """İsimle aday kod listesi: önce kök eşleşmesi, bulunamazsa benzerlik (yazım hatası)."""
    kokler = _kokler(mesaj)
    if not kokler:
        return []
    kodlar = _tum_kodlar()

    skorlu = []
    for k in kodlar:
        kelimeler = k["norm"].split()
        vurus = sum(1 for kok in kokler if any(w.startswith(kok) for w in kelimeler))
        if vurus:
            skorlu.append((vurus, k))
    if skorlu:
        skorlu.sort(key=lambda x: (-x[0], len(x[1]["tanim"])))
        return [k for _, k in skorlu[:limit]]

    # Kök tutmadı → yazım hatası olabilir; kelime bazlı benzerlik ara.
    yakin = []
    for k in kodlar:
        en_iyi = 0.0
        for w in k["norm"].split():
            for kok in kokler:
                en_iyi = max(en_iyi, difflib.SequenceMatcher(None, kok, w).ratio())
        if en_iyi >= BENZERLIK_ESIGI:
            yakin.append((en_iyi, k))
    yakin.sort(key=lambda x: -x[0])
    return [k for _, k in yakin[:limit]]


def _satir(k: dict) -> str:
    tes = ", ".join(k["tesisler"]) if k["tesisler"] else "hiçbir tesiste kabul edilmiyor"
    teh = " (TEHLİKELİ)" if k.get("tehlikeli") else ""
    return f"- {k['kod']}{teh} — {k['tanim']} — kabul: {tes}"


def name_context(mesaj: str, limit: int = 8) -> dict | None:
    """Atık ADIYLA eşleşen kodları modele kaynak olarak verir (karar modelin değil)."""
    adaylar = by_name(mesaj, limit)
    if not adaylar:
        return None
    return {
        "baslik": "Atık kodu tablosu (isimle eşleşen kodlar)",
        "icerik": "İsimle eşleşen atık kodları ve kabul edildiği tesisler:\n"
                  + "\n".join(_satir(k) for k in adaylar),
    }


def code_context(kod_temiz: str) -> dict | None:
    """Tam kod sonucunu modele kaynak olarak verir (kod + başka soru birlikte geldiğinde)."""
    r = by_code(kod_temiz)
    if not r:
        return None
    return {"baslik": f"Atık kodu tablosu ({r['kod']})", "icerik": _satir(r)}


def _answer_code(kod_temiz: str) -> str:
    r = by_code(kod_temiz)
    if not r:
        return (f"Bu atık kodunu ({kod_temiz}) listemizde bulamadım. Kodu kontrol edebilir "
                f"ya da yetkilimize danışabilirsiniz: {ILETISIM}")
    bilgi = f"{r['kod']} — {r['tanim']}.\n\n" if r["tanim"] else ""
    teh = " Tehlikeli atık sınıfındadır." if r["tehlikeli"] else ""
    if r["tesisler"]:
        yer = " ve ".join(r["tesisler"])
        sonek = "tesislerimizde" if len(r["tesisler"]) > 1 else "tesisimizde"
        return (f"{bilgi}Evet ✅ bu atığı **{yer}** {sonek} alıyoruz.{teh} "
                f"Göndermek isterseniz süreci anlatabilirim.")
    return (f"{bilgi}Bu atığı şu an hiçbir tesisimizde kabul edemiyoruz.{teh} "
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


def gecersiz_kodlar(metin: str) -> list[str]:
    """Metinde geçip tabloda BULUNMAYAN 6-haneli kodlar.

    Son savunma hattı: modele tablo kaynak olarak verilse bile yanlış kod yazabilir.
    Müşterinin atığını hatalı kodla göndermesi en pahalı hata olduğu için cevap
    kullanıcıya gitmeden önce burada denetlenir. Telefon/tarih maskelenmiş metin kullanılır.
    """
    from app.router import kodlar_bul

    kodlar, _ = kodlar_bul(metin)
    if not kodlar:
        return []
    yer = ",".join("?" * len(kodlar))
    with get_conn() as conn:
        var = {
            r[0]
            for r in conn.execute(
                f"select kod_temiz from atik_kodlari where kod_temiz in ({yer})", kodlar
            ).fetchall()
        }
    return [k for k in kodlar if k not in var]


def answer(text: str) -> str:
    """Deterministik Türkçe cevap; çoklu kod ve gürültü toleranslı. Kod yoksa boş dize."""
    from app.router import kodlar_bul

    kodlar, gruplar = kodlar_bul(text)
    if kodlar:
        return "\n\n".join(_answer_code(k) for k in kodlar[:3])
    for grup in gruplar:
        if cevap := _answer_group(grup):
            return cevap
    return ""
