# Yayına Alma — Windows Ofis PC Kılavuzu

> Bu dosya, ofis Windows bilgisayarında **Claude Code**'un adım adım uygulaması için yazıldı.
> Hedef: botu bu PC'de çalıştırıp Cloudflare Tunnel ile `https://` adres alıp 4r.com.tr'ye gömmek.
> Kullanıcı non-tekniktir: her adımı açıkla, hata çıkarsa dur ve çöz, baştan savma.

## 0. Önkoşullar (Claude bunları kurar/doğrular)
Windows'ta yoksa `winget` ile kur:
```powershell
winget install -e --id Docker.DockerDesktop
winget install -e --id Python.Python.3.12
winget install -e --id Cloudflare.cloudflared
```
- Docker Desktop kurulduktan sonra **açılmalı ve çalışır durumda** olmalı (WSL2 gerekebilir;
  BIOS'ta sanallaştırma kapalıysa Docker açılmaz → kullanıcıya BIOS'tan "Virtualization" açtır).
- Doğrula: `docker info`, `python --version` (>=3.11), `cloudflared --version`.

## 1. Repo (zaten klonlanmadıysa)
```powershell
git clone https://github.com/qeni8/4r-chatbot.git
cd 4r-chatbot
```

## 2. Ortam değişkenleri (.env)
```powershell
copy .env.example .env
```
`.env` içinde şunları ayarla:
- `GROQ_API_KEY=gsk_...` — kullanıcıdan al (Mac'teki .env'de mevcut; yoksa console.groq.com'dan).
- `CORS_ORIGINS=https://4r.com.tr,https://www.4r.com.tr` — widget yalnızca siteden çağrılsın.
- Diğerleri varsayılan kalır (DATABASE_URL localhost'u gösterir, doğru).

## 3. Veritabanı (Docker)
```powershell
docker compose up -d
```
pgvector'lü Postgres kalkar, `db/schema.sql` otomatik yüklenir. `docker ps` ile "healthy" doğrula.

## 4. Python ortamı
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -U pip
.venv\Scripts\pip install -e ".[ingest,dev]"
```

## 5. Veriyi yükle (ilk kurulumda bir kez)
```powershell
$env:PYTHONPATH="."
.venv\Scripts\python scripts\ingest_atik_kodlari.py data\raw\GUNCEL_ATIK_KODLARI_4R.xlsx
.venv\Scripts\python scripts\embed_atik_kodlari.py      # 842 tanım (ilk kez model ~500MB-1GB iner)
.venv\Scripts\python scripts\refresh.py                 # site: çek→parçala→embed
```

## 6. Testler (yayından önce doğrulama)
```powershell
.venv\Scripts\python -m pytest -q                       # 33 test yeşil olmalı
```
Canlı bir soru dene:
```powershell
.venv\Scripts\python -c "from app.db import pool; from app.bot import reply; pool.open(); print(reply('06 01 01 aliyor musunuz','t','web')['answer']); pool.close()"
```

## 7. Uygulamayı çalıştır (açık kalacak)
```powershell
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Bu terminal **açık kalmalı** (bugünlük). Kalıcı servis (NSSM/Task Scheduler) + PC uyku kapatma
= yayından sonra yapılacak sağlamlaştırma.

## 8. Cloudflare Tunnel → HTTPS adres
Yeni bir terminalde:
```powershell
cloudflared tunnel --url http://localhost:8000
```
Çıktıdaki `https://xxxx.trycloudflare.com` adresini **not al** (widget bunu kullanacak).
> Bugün için hızlı tünel yeterli. Kalıcı `bot.4r.com.tr` alt alan adı + isimli tünel sonra kurulur.

## 9. Test: tünel adresi çalışıyor mu
Tarayıcıda `https://xxxx.trycloudflare.com/demo` aç → widget'ı dene. `06 01 01` doğru cevap
vermeli. Sonra `.../health` → `{"status":"ok"}`.

## 10. WordPress'e widget'ı ekle
4r.com.tr WordPress yöneticisinde, `</body>` öncesine tek satır (tema footer ya da "WPCode" /
"Insert Headers and Footers" eklentisiyle):
```html
<script src="https://xxxx.trycloudflare.com/widget.js"></script>
```
> Not: hızlı tünel adresi PC/tünel yeniden başlayınca **değişir**. Kalıcı alt alan adı kurulunca
> (bot.4r.com.tr) bu satır bir daha değişmez. Bugün launch için hızlı tünel kabul; ardından sabitle.

## 11. Canlı doğrulama
4r.com.tr'yi aç → sağ altta balon → "vidanjör hizmetiniz var mı", "06 01 01", "boya çamuru"
sorularını dene. Cevaplar doğru + KVKK notu görünür olmalı.

---
## Yayından sonra (sağlamlaştırma — deadline değil)
- Kalıcı tünel + `bot.4r.com.tr` (adres sabitlenir, script bir daha değişmez)
- Uygulamayı Windows servisi yap (NSSM) + PC uyku/otomatik başlat ayarı
- Groq ücretli/limit kararı, WhatsApp (Meta Cloud API), mağaza fiyatları
