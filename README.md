# 4R Çevre Chatbot

Atık yönetimi destek botu (web widget + WhatsApp). Uydurmaz; bilmediğinde insana devreder.
Mimari kararlar: [`CLAUDE.md`](./CLAUDE.md) · Yayın: [`DEPLOY.md`](./DEPLOY.md) ·
Bekleyen veriler: [`EKSIKLER.md`](./EKSIKLER.md)

**Bağımlılık yok denecek kadar az:** Python + SQLite. Docker, Postgres, vektör veritabanı
ve embedding modeli **kullanılmaz** — korpus küçük olduğu için tamamı doğrudan modele verilir.

## Kurulum

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ingest,dev]"

cp .env.example .env            # GEMINI_API_KEY doldur (faturalandırma açık olmalı)

PYTHONPATH=. python scripts/ingest_atik_kodlari.py data/raw/GUNCEL_ATIK_KODLARI_4R.xlsx
uvicorn app.main:app --reload
```

Sağlık: `curl localhost:8000/health` → `{"status":"ok","atik_kodu":842,"belge":17}`
Demo: `localhost:8000/demo`

## Nasıl çalışır

```
Mesaj → limit kontrolü → selam kısayolu → yönlendirme
  ├─ saf atık kodu sorusu ("06 01 01 alıyor musunuz")
  │     → SQLite tablodan deterministik cevap, modele hiç uğramaz
  ├─ kod + başka soru ("06 01 01 fiyatı ne kadar")
  │     → tablo sonucu modele KAYNAK olarak verilir, model tam soruyu cevaplar
  └─ serbest soru
        → tüm site içeriği (17 belge) + varsa isimle eşleşen kodlar → LLM

Cevap gönderilmeden önce: içindeki atık kodları tabloya karşı doğrulanır.
Bilmiyorsa / konu dışıysa / hata → devir kaydı açılır + yetkiliye bildirim gider
                                  + müşteriye "size dönelim mi?" formu gösterilir.
Her mesaj loglanır.
```

- **Neden vektör arama yok:** korpus 17 belge / ~5.000 kelime. Tamamı tek istekte modele
  sığıyor; parçalama ve benzerlik araması yalnızca ıskalama riski ve kurulum yükü ekliyordu.
- **Atık kodu asla modele yorumlatılmaz** — kabul/red bilgisi tablodan gelir (`app/waste_lookup.py`).
  İsimle aramada birden çok aday varsa bot seçmez, **sorar**. Model yine de tabloda olmayan
  bir kod yazarsa cevap gönderilmez (`gecersiz_kodlar` denetimi) — yanlış kodla atık
  göndermek en pahalı hata olduğu için son savunma hattı.
- **Koruma katmanları:** günlük/oturum/IP limitleri (`app/limits.py`), KVKK saklama süresi
  (`LOG_SAKLAMA_GUN`), yapılandırma denetimi (`/health` → `uyarilar`).
- **Devir takibi:** bot cevaplayamadığında talep `devir_kayitlari`'na yazılır ve
  `BILDIRIM_EPOSTA` / `BILDIRIM_WHATSAPP` kanallarına bildirilir (`app/devir.py`).
  Widget müşteriye iletişim formu gösterir → `POST /iletisim`. Kanal ayarlı değilse
  kayıt yine tutulur ve `/health` uyarı verir.
- **LLM:** Gemini (`LLM_PROVIDER=gemini`). Kaliteden memnun kalınmazsa tek satırla Anthropic'e
  geçiş: `LLM_PROVIDER=anthropic` + `pip install -e ".[anthropic]"`.

## Yapı

| Yol | İçerik |
|---|---|
| `app/` | `main.py` (API) · `bot.py` (orkestrasyon) · `router.py` · `waste_lookup.py` · `knowledge.py` · `llm.py` · `limits.py` · `whatsapp.py` · `db.py` · `config.py` · `sabitler.py` |
| `scripts/` | `ingest_atik_kodlari.py` · `fetch_site.py` · `refresh.py` · `run_tests.py` · `log_ozet.py` |
| `data/site/` | Site içeriği (bot bilgisinin kaynağı, düz Markdown) |
| `db/schema.sql` | SQLite şeması: `atik_kodlari` + `konusma_loglari` |
| `web/` | `widget.js` (gömülebilir) · `demo.html` |

## Test & izleme

```bash
pytest -q                       # hermetik regresyon (DB/model gerektirmez)
python scripts/run_tests.py     # 40 soruluk kalite seti — HATA sayısı 0 olmalı
python scripts/log_ozet.py 7    # son 7 gün: hacim, devir oranı, cevapsız sorular
python scripts/refresh.py       # site içeriği değiştiğinde tazele
```

> `scripts/` dosyaları `app` paketini import eder. Editable kurulum yapılmadıysa
> komutların başına `PYTHONPATH=.` ekleyin.
