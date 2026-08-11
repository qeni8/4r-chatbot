"""4r.com.tr sayfalarını çek → temizle → data/site/*.md (Brief Bölüm 6).

Embedding/parçalama AYRI adım; bu script yalnızca ham temiz metni üretir.

Kullanım:
    python scripts/fetch_site.py            # tüm liste
    python scripts/fetch_site.py --only entegre-atik-yonetimi hakkimizda
"""

import argparse
import re
import sys
from pathlib import Path

import httpx
import trafilatura

BASE = "https://4r.com.tr"
OUT = Path("data/site")

PATHS = [
    "/",
    "/hakkimizda/",
    "/lisanslar/",
    "/kisisel-verilerin-korunmasi-aydinlatma-metni/",
    "/entegre-atik-yonetimi/",
    "/tehlikeli-ve-tehlikesiz-atik-ara-depolama/",
    "/tehlikeli-ve-tehlikesiz-atik-geri-kazanim/",
    "/atik-su-aritma-tesisi/",
    "/atiktan-turetilmis-yakit-aty-uretimi/",
    "/elektrikli-ve-elektronik-atik-isleme/",
    "/akumulator-gecici-depolama/",
    "/tehlikeli-atik-tasimaciligi/",
    "/lisansli-vidanjor-hizmeti/",
    "/ibc-tank-alim-satim-yikama-rebottle/",
    "/solvent-geri-kazanimi-solvent-distilasyonu/",
    "/hizmetlerimiz/",
    "/iletisim/",
    "/50-kg-alti-atik-gonderimi-kilavuzu/",
    # NOT: /magaza/ ürünleri JS ile yükleniyor; basit çekme yalnızca menü/çerez getiriyor.
    # Fiyatlar için ürün yapısı ayrıca incelenmeli ya da manuel fiyat listesi eklenmeli.
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 4R-Bot/1.0"


def slug(path: str) -> str:
    return path.strip("/").replace("/", "_") or "anasayfa"


# Çerez/onay banner'ı bazı sayfalarda gövdenin tamamını kaplıyor (iletisim, lisanslar).
# Temizlenmezse RAG havuzuna çöp girer ve bot bu sayfalara "bilgi var" sanır.
COP_SATIR = re.compile(
    r"teknik depolama veya erişim|çerez|abone veya kullanıcı tarafından|"
    r"yalnızca istatistiksel amaçlar|pazarlama profilleri oluşturmak",
    re.IGNORECASE,
)
MIN_KELIME = 25


def temizle(text: str) -> str:
    """Çerez banner'ı satırlarını ve tekrar eden slider artıklarını atar."""
    goruldu: set[str] = set()
    satirlar = []
    for ham in text.splitlines():
        s = ham.strip()
        if not s or COP_SATIR.search(s):
            continue
        if s in goruldu:  # anasayfa slider'ı aynı cümleyi 3 kez veriyor
            continue
        goruldu.add(s)
        satirlar.append(s)
    return "\n".join(satirlar)


def fetch_one(client: httpx.Client, path: str) -> tuple[str, int, str]:
    url = BASE + path
    try:
        r = client.get(url, follow_redirects=True, timeout=30)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001 — external network sınırı
        return url, 0, f"HATA: {e}"

    text = trafilatura.extract(
        r.text,
        favor_recall=True,
        include_tables=True,
        target_language="tr",
        url=url,
    )
    if not text:
        return url, 0, "BOŞ (içerik çıkarılamadı)"

    text = temizle(text)
    if len(text.split()) < MIN_KELIME:
        return url, 0, "ATLANDI (temizlik sonrası içerik kalmadı)"

    title = trafilatura.extract_metadata(r.text)
    baslik = getattr(title, "title", None) or path
    OUT.mkdir(parents=True, exist_ok=True)
    body = f"<!-- url: {url} -->\n# {baslik}\n\n{text.strip()}\n"
    (OUT / f"{slug(path)}.md").write_text(body, encoding="utf-8")
    return url, len(text.split()), "OK"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="sadece bu slug'lar")
    args = parser.parse_args()

    paths = PATHS
    if args.only:
        wanted = set(args.only)
        paths = [p for p in PATHS if slug(p) in wanted]
        if not paths:
            print("Eşleşen yol yok. Mevcut slug'lar:", [slug(p) for p in PATHS], file=sys.stderr)
            sys.exit(1)

    with httpx.Client(headers={"User-Agent": UA}) as client:
        toplam = 0
        for path in paths:
            url, words, durum = fetch_one(client, path)
            print(f"{durum:>28} | {words:>5} kelime | {url}")
            toplam += words
        print(f"\nToplam: {toplam} kelime, {len(paths)} sayfa → {OUT}/")


if __name__ == "__main__":
    main()
