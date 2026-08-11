import re

# 6-haneli atık kodu: 06 01 01 / 060101 / 06.01.01 / 06 01 01*
CODE6 = re.compile(r"(?<!\d)(\d{2})[ .]?(\d{2})[ .]?(\d{2})\*?(?!\d)")
# 2 çift = 4 haneli grup: 06 01 (bitişik "0601" bilinçli olarak hariç — telefon vb. karışmasın)
CODE4 = re.compile(r"(?<!\d)(\d{2})[ .](\d{2})(?!\d)")

# Tarih ve uzun rakam dizileri koda benziyor (01.05.2024 → "052024"). Önce maskelenir.
# Yıl 4 haneli aranır: "06.01.01" iki haneli tarih değil, geçerli bir atık kodudur.
TARIH = re.compile(
    r"\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{4}|\d{4}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{1,2}"
)
UZUN_SAYI = re.compile(r"(?<!\d)\d{7,}(?!\d)")
TELEFON = re.compile(r"(\+90|0)?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}")

# Atık kodunun yanında başka bir niyet varsa cevabı model üretmeli (kabul + süreç/fiyat).
DIGER_NIYET = re.compile(
    r"fiyat|ücret|ucret|kaç para|kac para|maliyet|ne kadar|teklif|"
    r"nasıl|nasil|gönder|gonder|taşı|tasi|sevk|nakl|"
    r"evrak|belge|form|uatf|motat|süreç|surec|prosedür|prosedur|"
    r"konteyner|vidanjör|vidanjor|randevu|adres|iletişim|iletisim",
    re.IGNORECASE,
)

# 2 haneli bölüm kodları 01-20 aralığında (CLAUDE.md Bölüm 5).
_BOLUMLER = {f"{i:02d}" for i in range(1, 21)}


def _maskele(mesaj: str) -> str:
    for kalip in (TARIH, TELEFON, UZUN_SAYI):
        mesaj = kalip.sub(" ", mesaj)
    return mesaj


def _tekil(kalip: re.Pattern, temiz: str, gecerli_bolum: bool) -> list[str]:
    out, gorulen = [], set()
    for m in kalip.findall(temiz):
        k = "".join(m)
        if k in gorulen or (gecerli_bolum and k[:2] not in _BOLUMLER):
            continue
        gorulen.add(k)
        out.append(k)
    return out


def kodlar_bul(mesaj: str) -> tuple[list[str], list[str]]:
    """(6-haneli kodlar, 4-haneli gruplar). Tarih/telefon maskelenmiş metin üzerinden."""
    temiz = _maskele(mesaj or "")
    return _tekil(CODE6, temiz, False), _tekil(CODE4, temiz, True)


def kod_bul(mesaj: str) -> tuple[str | None, str]:
    """İlk eşleşme: ('kod6', '060101') | ('grup4', '0601') | (None, '')."""
    kodlar, gruplar = kodlar_bul(mesaj)
    if kodlar:
        return "kod6", kodlar[0]
    if gruplar:
        return "grup4", gruplar[0]
    return None, ""


def route(mesaj: str) -> str:
    """'atik_kodu' (yapısal tabloya gider) ya da 'rag' (site + model)."""
    tur, _ = kod_bul(mesaj)
    return "atik_kodu" if tur else "rag"


def sadece_kabul(mesaj: str) -> bool:
    """Mesaj yalnızca 'bu kodu alıyor musunuz' mu, yoksa başka bir soru da mı içeriyor?"""
    return not DIGER_NIYET.search(mesaj or "")
