from pgvector import Vector
from pgvector.psycopg import register_vector

from app.db import get_conn
from app.embeddings import embed_query

RRF_K = 60
FTS = "turkish"


def search(soru: str, k: int = 5, havuz: int = 20) -> list[dict]:
    """Hibrit arama: anlamsal (vektör) + tam kelime (Türkçe FTS), RRF ile birleştirilir."""
    vec = Vector(embed_query(soru))
    with get_conn() as conn:
        register_vector(conn)
        vids = [
            r[0]
            for r in conn.execute(
                "select id from chunks where embedding is not null "
                "order by embedding <=> %s limit %s",
                (vec, havuz),
            ).fetchall()
        ]
        lids = [
            r[0]
            for r in conn.execute(
                f"select id from chunks "
                f"where to_tsvector('{FTS}', icerik) @@ plainto_tsquery('{FTS}', %s) "
                f"order by ts_rank(to_tsvector('{FTS}', icerik), plainto_tsquery('{FTS}', %s)) desc "
                f"limit %s",
                (soru, soru, havuz),
            ).fetchall()
        ]

    skor: dict[int, float] = {}
    for liste in (vids, lids):
        for rank, cid in enumerate(liste):
            skor[cid] = skor.get(cid, 0.0) + 1.0 / (RRF_K + rank)

    top = sorted(skor, key=lambda c: skor[c], reverse=True)[:k]
    if not top:
        return []

    with get_conn() as conn:
        rows = conn.execute(
            "select c.id, d.baslik, d.kaynak, c.icerik from chunks c "
            "join documents d on d.id = c.document_id where c.id = any(%s)",
            (top,),
        ).fetchall()
    detay = {r[0]: r for r in rows}
    return [
        {"baslik": detay[i][1], "kaynak": detay[i][2], "icerik": detay[i][3], "skor": round(skor[i], 4)}
        for i in top
        if i in detay
    ]
