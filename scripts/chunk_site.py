"""data/site/*.md → documents + chunks (embedding NULL bırakılır).

Embedding ayrı adımda (scripts/embed_chunks.py) doldurulur — bu script key gerektirmez.

Kullanım:
    python scripts/chunk_site.py
"""

import re
from pathlib import Path

from app.db import get_conn, pool

SRC = Path("data/site")
MAX_CHARS = 1200
OVERLAP = 150


def parse_md(path: Path) -> tuple[str, str, str]:
    text = path.read_text(encoding="utf-8")
    url_m = re.search(r"<!-- url: (.*?) -->", text)
    url = url_m.group(1) if url_m else str(path)
    title_m = re.search(r"^# (.+)$", text, re.MULTILINE)
    baslik = title_m.group(1).strip() if title_m else path.stem
    body = re.sub(r"<!--.*?-->", "", text)
    body = re.sub(r"^# .+$", "", body, count=1, flags=re.MULTILINE).strip()
    return url, baslik, body


def chunk(body: str) -> list[str]:
    paras = [p.strip() for p in body.split("\n") if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if len(cur) + len(p) + 1 <= MAX_CHARS:
            cur = f"{cur}\n{p}" if cur else p
        else:
            if cur:
                chunks.append(cur)
            cur = (cur[-OVERLAP:] + "\n" + p) if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def main() -> None:
    pool.open()
    files = sorted(SRC.glob("*.md"))
    toplam_chunk = 0
    with get_conn() as conn:
        conn.execute("truncate documents restart identity cascade")
        for path in files:
            url, baslik, body = parse_md(path)
            parts = [f"{baslik}\n{p}" for p in chunk(body)]
            doc_id = conn.execute(
                "insert into documents (kaynak, baslik, tur) values (%s, %s, 'web') returning id",
                (url, baslik),
            ).fetchone()[0]
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into chunks (document_id, icerik, token_sayisi) values (%s, %s, %s)",
                    [(doc_id, c, len(c.split())) for c in parts],
                )
            toplam_chunk += len(parts)
            print(f"{len(parts):>2} parça | {baslik[:45]}")
        conn.commit()
    pool.close()
    print(f"\nToplam: {len(files)} belge, {toplam_chunk} parça → documents/chunks "
          f"(embedding henüz boş)")


if __name__ == "__main__":
    main()
