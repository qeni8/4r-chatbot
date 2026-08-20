# Yayına Alma — Windows Ofis PC Kılavuzu

> Bu dosya, ofis Windows bilgisayarında **Claude Code**'un adım adım uygulaması için yazıldı.
> Kullanıcı non-tekniktir: her adımı sade dille açıkla, hata çıkarsa dur ve çöz, atlama.
>
> **Docker / WSL2 / BIOS ayarı GEREKMİYOR.** Veritabanı tek dosyalık SQLite, embedding modeli yok.
> Gereken tek şey Python.

## 0. Önkoşullar

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
winget install -e --id Cloudflare.cloudflared
```

Doğrula: `python --version` (>=3.11), `git --version`, `cloudflared --version`.
PowerShell'i kurulumdan sonra **kapatıp yeniden aç** (PATH güncellensin).

## 1. Repo

```powershell
git clone https://github.com/qeni8/4r-chatbot.git
cd 4r-chatbot
```

## 2. Python ortamı

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -U pip
.venv\Scripts\pip install -e ".[ingest,dev]"
```

## 3. Ortam değişkenleri

```powershell
copy .env.example .env
notepad .env
```

Doldurulacaklar:
- `GEMINI_API_KEY=...` — kullanıcıdan al.
  **Faturalandırma açık olmalı** (aistudio.google.com → Get API key → Set up Billing).
  Ücretsiz katmanın günlük kotası yoğun günde biter ve bot "yoğunluk" mesajına düşer.
  Bu hacimde gerçek maliyet ~$2-5/ay; Google Cloud'da $10 bütçe uyarısı kurulu.
- `CORS_ORIGINS=https://4r.com.tr,https://www.4r.com.tr` — widget yalnızca siteden çağrılsın.
- `APP_ENV=prod`
- `YONETIM_SIFRE=...` — yönetim panelinin şifresi (kullanıcıdan al). Boş bırakılırsa
  panel kapalı olur ve bekleyen talepler görülemez.
- `BILDIRIM_EPOSTA` + `SMTP_*` — varsa doldur. Yoksa talepler yalnızca panelde görünür
  (bot yine "yetkiliye aktarıyorum" der ama kimseye anlık haber gitmez).
- Diğerleri varsayılan kalır.

## 4. Atık kodu verisini yükle (ilk kurulumda bir kez)

```powershell
$env:PYTHONPATH="."
.venv\Scripts\python scripts\ingest_atik_kodlari.py data\raw\GUNCEL_ATIK_KODLARI_4R.xlsx
```

Beklenen çıktı — **birebir bu rakamlar olmalı**:
```
Ayrıştırılan 6-haneli kod: 842 | tehlikeli: 408 | en az bir tesiste kabul: 375
Yüklendi: 842 kayıt → atik_kodlari
```

## 5. Testler (yayından önce zorunlu doğrulama)

```powershell
.venv\Scripts\python -m pytest -q
```
Tamamı geçmeli. Geçmiyorsa **yayına alma**, önce hatayı çöz.

Kalite ölçümü (Gemini'yi gerçekten çağırır, ~1 dk):
```powershell
.venv\Scripts\python scripts\run_tests.py
```
Sonuçta **HATA sayısı 0 olmalı**. 0 değilse API anahtarı/kota sorunludur ve ölçüm geçersizdir.

## 6. Uygulamayı çalıştır

```powershell
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Bu terminal açık kalmalı. Kontrol: tarayıcıda `http://localhost:8000/health`
→ `{"status":"ok","atik_kodu":842,"belge":17}`

## 7. Cloudflare Tunnel → herkese açık HTTPS adres

Yeni bir PowerShell penceresinde:
```powershell
cloudflared tunnel --url http://localhost:8000
```
Çıktıdaki `https://xxxx.trycloudflare.com` adresini **not al**.

Test: `https://xxxx.trycloudflare.com/demo` → widget'ı dene.

## 8. WordPress'e widget'ı ekle

4r.com.tr yönetim panelinde `</body>` öncesine (tema footer ya da "WPCode" /
"Insert Headers and Footers" eklentisi):

```html
<script src="https://xxxx.trycloudflare.com/widget.js"></script>
```

> ⚠️ Hızlı tünel adresi PC/tünel yeniden başlayınca **değişir** ve widget ölür.
> Bugün launch için kabul; hemen ardından Bölüm 10'daki kalıcı tünelle sabitlenmeli.

## 9. Canlı doğrulama

4r.com.tr'yi aç → sağ altta balon → sırayla dene:
1. `06 01 01 alıyor musunuz` → Merkez ve Kapaklı, tehlikeli (modelsiz, anında)
2. `boya çamuru alıyor musunuz` → 08 01 1x kodları
3. `vidanjör hizmetiniz var mı` → site içeriğinden cevap
4. `bugün hava nasıl` → kibarca reddetmeli

Panel altında KVKK notu görünür olmalı.

Ayrıca **yönetim panelini** kontrol et: `https://xxxx.trycloudflare.com/yonetim`
(kullanıcı `4r`, şifre `.env`'deki `YONETIM_SIFRE`). Bekleyen talepler burada görünür.

---

## 10. Yayından sonra — sağlamlaştırma (aynı gün yapılmalı)

1. **Kalıcı tünel + alt alan adı** (`bot.4r.com.tr`) — adres bir daha değişmez,
   WordPress'teki script satırı sabitlenir. `cloudflared tunnel login` → `tunnel create` →
   DNS kaydı → `tunnel run`.
2. **Windows servisi** (NSSM ya da Görev Zamanlayıcı) — PC yeniden başlayınca bot kendiliğinden
   ayağa kalksın, terminal açık kalmak zorunda olmasın.
3. **Güç ayarları** — PC uyku moduna girmesin (Denetim Masası → Güç Seçenekleri → Uyku: Asla).
4. **Yedek** — `data\4r_chatbot.db` tek dosya; günlük kopyası alınsın (konuşma logları burada).
5. **İzleme** — haftada bir: `.venv\Scripts\python scripts\log_ozet.py 7`
   (cevapsız kalan sorular = havuza eklenecek içerik).

## Sorun giderme

| Belirti | Sebep / çözüm |
|---|---|
| `/health` açılmıyor | uvicorn terminali kapanmış; Bölüm 6'yı tekrar çalıştır |
| Widget cevap vermiyor | Tünel adresi değişmiş → Bölüm 8'deki script satırını güncelle |
| Cevaplar "yoğunluk" diyor | Gemini kotası doldu → faturalandırma açık mı kontrol et |
| `ModuleNotFoundError` | `.venv\Scripts\pip install -e ".[ingest,dev]"` tekrar çalıştır |
| Widget siteye eklendi ama açılmıyor | `CORS_ORIGINS` 4r.com.tr'yi içeriyor mu, `.env` kaydedildi mi |
