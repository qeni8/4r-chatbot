"""Test setini çalıştırır, otomatik değerlendirir, rapor üretir.

Kullanım:
    python scripts/run_tests.py

PASS   = beklendiği gibi
FAIL   = açık hata (cevap vermesi gerekirken devretti, ya da beklenen bilgi yok)
REVIEW = insan gözü gerekli (isim araması, takip soruları)
HATA   = model/sağlayıcı çağrısı başarısız. GİZLENMEZ: bu sayı 0 değilse ölçüm geçersizdir.
"""

import json
import time
from collections import Counter
from pathlib import Path

from app.bot import reply
from app.db import get_conn, init_db
from app.sabitler import DEVIR

SET = Path("tests/test_set.json")
DEVIR_IZ = DEVIR[:35].lower()
RET_IZLERI = ("yardımcı ol", "yardımcı olam", "atık yönetimi", "konusunda", "üzgün", DEVIR_IZ)
# Model çağrısının başarısız olduğu yöntemler — kalite değil altyapı sorunu.
HATA_YONTEMLERI = {"hata", "yogunluk"}


def degerlendir(item: dict, cevap: str, yontem: str) -> str:
    if yontem in HATA_YONTEMLERI:
        return "HATA"

    dusuk = cevap.lower()
    anahtar = item.get("anahtar", [])
    exp = item["expect"]

    if exp == "review":
        return "REVIEW"
    if exp == "devir":
        return "PASS" if DEVIR_IZ in dusuk else "FAIL"
    if exp == "red":
        # Konu dışı soru: cevaplamamalı. Kibar ret ya da yönlendirme kabul.
        return "PASS" if any(iz in dusuk for iz in RET_IZLERI) else "FAIL"
    if exp == "contains":
        return "PASS" if all(a.lower() in dusuk for a in anahtar) else "FAIL"
    if exp == "cevap":
        if DEVIR_IZ in dusuk:
            return "FAIL"  # cevap vermesi gerekirken insana devretti
        if not anahtar or any(a.lower() in dusuk for a in anahtar):
            return "PASS"
        return "REVIEW"  # cevap verdi ama beklenen anahtar yok
    return "REVIEW"


def main() -> None:
    items = json.loads(SET.read_text(encoding="utf-8"))
    init_db()
    with get_conn() as c:
        c.execute("delete from konusma_loglari")
        c.commit()

    sonuclar = []
    for i, item in enumerate(items):
        sid = item.get("session", f"test-{i}")
        r = reply(item["soru"], sid, "web")
        sonuclar.append((degerlendir(item, r["answer"], r["method"]), item, r))
        if r["method"] == "rag":
            time.sleep(0.5)  # sağlayıcıya nezaket; kota bloklaması için değil

    ozet = Counter(v for v, _, _ in sonuclar)
    kat: dict[str, Counter] = {}
    for v, item, _ in sonuclar:
        kat.setdefault(item["kategori"], Counter())[v] += 1

    print("=" * 80)
    for v, item, r in sonuclar:
        isaret = {"PASS": "✓", "FAIL": "✗", "REVIEW": "?", "HATA": "!"}[v]
        print(f"{isaret} [{v:6}] {item['kategori']:14} | {item['soru']}")
        print(f"        ({r['method']}) {r['answer'][:150].replace(chr(10), ' ')}")
    print("=" * 80)
    print("KATEGORİ BAZINDA:")
    for k, c in kat.items():
        print(f"  {k:14} {dict(c)}")
    print(f"\nTOPLAM: {dict(ozet)}  /  {len(sonuclar)} soru")
    if ozet.get("HATA"):
        print(f"\n⚠️  {ozet['HATA']} soruda model çağrısı başarısız — bu ölçüm GEÇERSİZ. "
              f"API anahtarını/kotayı kontrol edip tekrar çalıştırın.")

    Path("tests/results.txt").write_text(
        "\n".join(f"[{v}] {it['soru']}\n  -> {r['answer']}\n" for v, it, r in sonuclar),
        encoding="utf-8",
    )
    print("Tam çıktı: tests/results.txt")


if __name__ == "__main__":
    main()
