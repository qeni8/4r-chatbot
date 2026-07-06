"""Konuşma loglarını özetler (Adım 8 — izle & iyileştir).

Ne soruluyor, ne kadar insana devrediliyor, hangi sorular cevapsız kalıyor?
Cevapsız kalan sorular = havuza eklenecek içerik / iyileştirme fırsatı.

Kullanım:
    python scripts/log_ozet.py [gün]     # varsayılan son 30 gün
"""

import sys

from app.db import get_conn, pool

DEVIR = "kesin bilgi veremiyorum"


def main() -> None:
    gun = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    pool.open()
    with get_conn() as conn:
        aralik = f"created_at > now() - interval '{gun} days'"
        toplam = conn.execute(f"select count(*) from konusma_loglari where {aralik}").fetchone()[0]
        if not toplam:
            print(f"Son {gun} günde log yok.")
            pool.close()
            return

        print(f"=== Son {gun} gün — {toplam} mesaj ===\n")

        print("Kanal:")
        for k, n in conn.execute(
            f"select kanal, count(*) from konusma_loglari where {aralik} group by kanal order by 2 desc"
        ).fetchall():
            print(f"  {k or '-':10} {n}")

        print("\nYöntem:")
        for y, n in conn.execute(
            f"select yontem, count(*) from konusma_loglari where {aralik} group by yontem order by 2 desc"
        ).fetchall():
            print(f"  {y or '-':10} {n}")

        print("\nKullanılan model:")
        for m, n in conn.execute(
            f"select model, count(*) from konusma_loglari where {aralik} group by model order by 2 desc"
        ).fetchall():
            print(f"  {m or '-':28} {n}")

        devir = conn.execute(
            f"select count(*) from konusma_loglari where {aralik} and cevap ilike %s",
            (f"%{DEVIR}%",),
        ).fetchone()[0]
        print(f"\nİnsana devir / cevapsız: {devir} (%{100 * devir // toplam})")

        print("\nCevapsız kalan son sorular (havuz iyileştirme için):")
        for (soru,) in conn.execute(
            f"select soru from konusma_loglari where {aralik} and cevap ilike %s "
            "order by id desc limit 15",
            (f"%{DEVIR}%",),
        ).fetchall():
            print(f"  • {soru}")
    pool.close()


if __name__ == "__main__":
    main()
