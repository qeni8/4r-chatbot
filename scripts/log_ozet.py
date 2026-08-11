"""Konuşma loglarını özetler (izle & iyileştir).

Ne soruluyor, ne kadar insana devrediliyor, hangi sorular cevapsız kalıyor?
Cevapsız kalan sorular = havuza eklenecek içerik / iyileştirme fırsatı.

Kullanım:
    python scripts/log_ozet.py [gün]     # varsayılan son 30 gün
"""

import sys

from app.db import get_conn
from app.sabitler import DEVIR

DEVIR_IZ = DEVIR[:35]


def main() -> None:
    gun = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    aralik = "created_at > datetime('now', ?)"
    param = (f"-{gun} days",)

    with get_conn() as conn:
        toplam = conn.execute(
            f"select count(*) from konusma_loglari where {aralik}", param
        ).fetchone()[0]
        if not toplam:
            print(f"Son {gun} günde log yok.")
            return

        print(f"=== Son {gun} gün — {toplam} mesaj ===\n")

        for baslik, sutun, genislik in (
            ("Kanal", "kanal", 10), ("Yöntem", "yontem", 10), ("Kullanılan model", "model", 28)
        ):
            print(f"{baslik}:")
            for ad, n in conn.execute(
                f"select {sutun}, count(*) from konusma_loglari where {aralik} "
                f"group by {sutun} order by 2 desc",
                param,
            ).fetchall():
                print(f"  {ad or '-':{genislik}} {n}")
            print()

        hata = conn.execute(
            f"select count(*) from konusma_loglari where {aralik} "
            f"and yontem in ('hata','yogunluk')", param
        ).fetchone()[0]
        if hata:
            print(f"⚠️  Model çağrısı başarısız: {hata} (%{100 * hata // toplam}) — "
                  f"kota/anahtar kontrol edin.\n")

        devir = conn.execute(
            f"select count(*) from konusma_loglari where {aralik} and cevap like ?",
            (*param, f"%{DEVIR_IZ}%"),
        ).fetchone()[0]
        print(f"İnsana devir / cevapsız: {devir} (%{100 * devir // toplam})")

        print("\nCevapsız kalan son sorular (havuz iyileştirme için):")
        for (soru,) in conn.execute(
            f"select soru from konusma_loglari where {aralik} and cevap like ? "
            "order by id desc limit 15",
            (*param, f"%{DEVIR_IZ}%"),
        ).fetchall():
            print(f"  • {soru}")


if __name__ == "__main__":
    main()
