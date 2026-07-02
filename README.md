# 4R Çevre Chatbot

RAG + yapısal atık kodu sorgusu yapan destek chatbot'u (web + WhatsApp).
Mimari ve gereksinimler: [`CLAUDE.md`](./CLAUDE.md).

## Geliştirme kurulumu

```bash
# 1. Veritabanı (lokal, pgvector'lü Postgres)
docker compose up -d

# 2. Python ortamı
python -m venv .venv && source .venv/bin/activate
pip install -e ".[ingest,dev]"

# 3. Ortam değişkenleri
cp .env.example .env   # ANTHROPIC_API_KEY ve embedding key'lerini doldur

# 4. API
uvicorn app.main:app --reload
```

Sağlık kontrolü: `curl localhost:8000/health` → `{"status":"ok"}`

## Yapı

| Yol | İçerik |
|---|---|
| `app/` | FastAPI uygulaması (`main.py`, `config.py`, `db.py`) |
| `db/schema.sql` | Postgres + pgvector şeması (atık kodu, döküman/chunk, log) |
| `scripts/` | Ingestion scriptleri (atık kodu xlsx, site) |
| `data/raw/` | Ham kaynak dosyalar (git'e dahil değil) |

## Yol haritası
`CLAUDE.md` Bölüm 10. Şu an: **Adım 1 — iskelet + şema** tamam, atık kodu xlsx'i bekliyor.
