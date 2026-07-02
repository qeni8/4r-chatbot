"""842 atık kodu tanımını vektöre çevirir (isimle semantik arama için).

Kullanım:
    python scripts/embed_atik_kodlari.py
"""

from app.db import get_conn, pool
from app.embeddings import embed_passages


def main() -> None:
    pool.open()
    with get_conn() as conn:
        conn.execute("alter table atik_kodlari add column if not exists embedding vector(768)")
        conn.execute(
            "create index if not exists idx_atik_embedding on atik_kodlari "
            "using hnsw (embedding vector_cosine_ops)"
        )
        conn.commit()
        rows = conn.execute(
            "select id, tanim from atik_kodlari where embedding is null and tanim is not null "
            "order by id"
        ).fetchall()
        if not rows:
            print("Tüm kodlar zaten embed'li.")
            pool.close()
            return
        print(f"{len(rows)} kod tanımı embed ediliyor...")
        vektorler = embed_passages([tanim for _id, tanim in rows])
        with conn.cursor() as cur:
            cur.executemany(
                "update atik_kodlari set embedding = %s where id = %s",
                [(vec, rid) for (rid, _), vec in zip(rows, vektorler)],
            )
        conn.commit()
    pool.close()
    print(f"Tamam: {len(rows)} kod embed edildi.")


if __name__ == "__main__":
    main()
