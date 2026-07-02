"""Test setini çalıştırır, otomatik değerlendirir, rapor üretir (Adım 4).

Kullanım:
    python scripts/run_tests.py

PASS  = beklendiği gibi
FAIL  = açık hata (ör. cevap vermesi gerekirken devir etti, ya da yanlış kod bilgisi)
REVIEW = insan gözü gerekli (isim araması, selam, takip soruları)
"""

import json
import time
from collections import Counter
from pathlib import Path

from app.bot import reply
from app.db import get_conn, pool

DEVIR = "kesin bilgi veremiyorum"
SET = Path("tests/test_set.json")


def degerlendir(item: dict, cevap: str) -> str:
    dusuk = cevap.lower()
    anahtar = item.get("anahtar", [])
    exp = item["expect"]

    if exp == "review":
        return "REVIEW"
    if exp == "devir":
        return "PASS" if DEVIR in dusuk else "FAIL"
    if exp == "contains":
        return "PASS" if all(a.lower() in dusuk for a in anahtar) else "FAIL"
    if exp == "cevap":
        if DEVIR in dusuk:
            return "FAIL"  # cevap vermesi gerekirken insana devretti
        if any(a.lower() in dusuk for a in anahtar):
            return "PASS"
        return "REVIEW"  # cevap verdi ama beklenen anahtar yok
    return "REVIEW"


def main() -> None:
    items = json.loads(SET.read_text(encoding="utf-8"))
    pool.open()
    with get_conn() as c:
        c.execute("truncate konusma_loglari restart identity")
        c.commit()

    sonuclar = []
    for i, item in enumerate(items):
        sid = item.get("session", f"test-{i}")
        r = reply(item["soru"], sid, "web")
        verdikt = degerlendir(item, r["answer"])
        sonuclar.append((verdikt, item, r))
        if r["method"] in ("rag", "rag_hata"):
            time.sleep(2)  # Groq ücretsiz limitine saygı
    pool.close()

    ozet = Counter(v for v, _, _ in sonuclar)
    kat = {}
    for v, item, _ in sonuclar:
        kat.setdefault(item["kategori"], Counter())[v] += 1

    print("=" * 80)
    for v, item, r in sonuclar:
        isaret = {"PASS": "✓", "FAIL": "✗", "REVIEW": "?"}[v]
        print(f"{isaret} [{v:6}] {item['kategori']:14} | {item['soru']}")
        print(f"        ({r['method']}) {r['answer'][:150].replace(chr(10), ' ')}")
    print("=" * 80)
    print("KATEGORİ BAZINDA:")
    for k, c in kat.items():
        print(f"  {k:14} {dict(c)}")
    print(f"\nTOPLAM: {dict(ozet)}  /  {len(sonuclar)} soru")

    Path("tests/results.txt").write_text(
        "\n".join(f"[{v}] {it['soru']}\n  -> {r['answer']}\n" for v, it, r in sonuclar),
        encoding="utf-8",
    )
    print("Tam çıktı: tests/results.txt")


if __name__ == "__main__":
    main()
