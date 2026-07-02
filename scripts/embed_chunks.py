"""chunks tablosundaki embedding'i boş parçaları yerel modelle doldurur (ücretsiz).

Kullanım:
    python scripts/embed_chunks.py
"""

from pgvector.psycopg import register_vector

from app.db import get_conn, pool
from app.embeddings import embed_passages


def main() -> None:
    pool.open()
    with get_conn() as conn:
        register_vector(conn)
        rows = conn.execute(
            "select id, icerik from chunks where embedding is null order by id"
        ).fetchall()
        if not rows:
            print("Doldurulacak parça yok (hepsi embed'li).")
            pool.close()
            return

        print(f"{len(rows)} parça embed ediliyor (model ilk kez ~2.2 GB inebilir)...")
        vektorler = embed_passages([icerik for _id, icerik in rows])
        with conn.cursor() as cur:
            cur.executemany(
                "update chunks set embedding = %s where id = %s",
                [(vec, rid) for (rid, _), vec in zip(rows, vektorler)],
            )
        conn.commit()
    pool.close()
    print(f"Tamam: {len(rows)} parça embed edildi.")


if __name__ == "__main__":
    main()
