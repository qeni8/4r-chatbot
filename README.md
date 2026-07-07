# 4R Çevre Chatbot

RAG + yapısal atık kodu sorgusu yapan destek chatbot'u (web widget + WhatsApp).
Uydurmaz; bilmediğinde insana devreder. Mimari ve kararlar: [`CLAUDE.md`](./CLAUDE.md).

**Maliyet:** LLM (Groq/Llama) ve embedding (yerel model) ücretsiz — sunucu hariç $0.

## Geliştirme kurulumu

```bash
# 1. Veritabanı (pgvector'lü Postgres, şema otomatik yüklenir)
docker compose up -d

# 2. Python ortamı
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ingest,dev]"

# 3. Ortam değişkenleri
cp .env.example .env        # GROQ_API_KEY doldur (RAG cevapları için gerekli)

# 4. Veri yükle (ilk kurulumda bir kez)
python scripts/ingest_atik_kodlari.py data/raw/GUNCEL_ATIK_KODLARI_4R.xlsx
python scripts/embed_atik_kodlari.py    # 842 tanımı vektörle (isimle arama)
python scripts/refresh.py               # site: çek → parçala → embed

# 5. API
uvicorn app.main:app --reload
```

Sağlık: `curl localhost:8000/health` → `{"status":"ok"}` · Demo: `localhost:8000/demo`

> Not: scriptler `app` paketini import eder. Editable kurulum (`pip install -e .`)
> yapılmadıysa başına `PYTHONPATH=.` ekleyin.

## Nasıl çalışır

```
Mesaj → limit kontrolü → yönlendirme
         ├─ atık kodu (06 01 01 / grup) → tablodan deterministik cevap (modelsiz)
         └─ serbest soru → hibrit arama (vektör+FTS) → Groq LLM (grounding)
                            isimle atık niyeti varsa tablo eşleşmesi de kaynağa eklenir
Bilmiyorsa / limit / hata → insana devir. Her mesaj loglanır.
```

- **LLM:** Groq Llama 3.3 70B; günlük limitte otomatik `llama-3.1-8b-instant`'a düşer (`app/llm.py`).
- **Embedding:** yerel `paraphrase-multilingual-mpnet-base-v2` (768), API'siz (`app/embeddings.py`).
- **Guardrail/limit:** `app/limits.py` (günlük/oturum/ani), grounding sistem promptu `app/llm.py`.

## Yapı

| Yol | İçerik |
|---|---|
| `app/` | `main.py` (API), `bot.py` (orkestrasyon), `router.py`, `waste_lookup.py`, `retrieval.py`, `llm.py`, `limits.py`, `whatsapp.py`, `embeddings.py`, `config.py`, `db.py` |
| `scripts/` | `ingest_atik_kodlari.py`, `fetch_site.py`, `chunk_site.py`, `embed_*.py`, `refresh.py`, `run_tests.py`, `log_ozet.py` |
| `tests/` | pytest (`test_router`, `test_waste_lookup`, `test_bot`) + `test_set.json` |
| `web/` | `widget.js` (gömülebilir), `demo.html` |
| `db/schema.sql` | atık kodu + döküman/chunk + log tabloları (pgvector) |

## Test & izleme

```bash
pytest -q                       # regresyon (router + atık kodu + girdi)
python scripts/run_tests.py     # 40 soruluk kalite seti (Groq çağırır)
python scripts/log_ozet.py 7    # son 7 gün: hacim, devir oranı, cevapsız sorular
python scripts/refresh.py       # site içeriği değiştiğinde havuzu tazele
```

## Durum
`CLAUDE.md` Bölüm 14. Çekirdek + iki kanal + testler tamam. Kalan: yayın (VPS + Meta WhatsApp),
LLM ücretli/seçim kararı, mağaza fiyatları.
