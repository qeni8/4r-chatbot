# Yayına Alma — Windows Ofis PC Kılavuzu

> Bu dosya, ofis Windows bilgisayarında **Claude Code**'un adım adım uygulaması için yazıldı.
> Kullanıcı non-tekniktir: her adımı sade dille açıkla, hata çıkarsa dur ve çöz, atlama.
>
> **Docker / WSL2 / BIOS ayarı GEREKMİYOR.** Veritabanı tek dosyalık SQLite, embedding modeli yok.
> Gereken tek şey Python.

## 0. Claude Code ile başlangıç

Ofis bilgisayarında **PowerShell'i Yönetici olarak** aç ve sırayla:

```powershell
winget install -e --id Anthropic.ClaudeCode
```

PowerShell'i **kapat, yeniden aç**. Sonra `claude` yazıp giriş yap.

Ardından Claude'a şunu söyle:

> github.com/qeni8/4r-chatbot reposunu klonla ve DEPLOY.md'yi baştan sona uygula.
> Her adımda ne yaptığını sade dille anlat, hata çıkarsa dur ve çöz.

Kurulum sırasında senden **üç şey** isteyecek:
1. **Gemini API anahtarı** — aistudio.google.com → Get API key (`4r_chatbot`, `...QX1g`)
2. **Yönetim paneli şifresi** — sen belirleyeceksin
3. **WordPress girişi** — en son adımda, widget'ı siteye eklerken

---

## 1. Önkoşullar

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
winget install -e --id Cloudflare.cloudflared
```

PowerShell'i kurulumdan sonra **kapatıp yeniden aç** (PATH güncellensin).
Doğrula: `python --version` (>=3.11), `git --version`, `cloudflared --version`.

> ⚠️ **Windows tuzağı:** `python --version` hiçbir şey yazmaz ya da Microsoft Store'u
> açarsa, Windows'un sahte `python` kısayolu devrededir. Bu durumda **`py -3.12`**
> kullan (`py -3.12 -m venv .venv`). Kalıcı çözüm: Ayarlar → Uygulamalar →
> "Uygulama yürütme diğer adları" → `python.exe` ve `python3.exe` **kapat**.

## 2. Repo

```powershell
git clone https://github.com/qeni8/4r-chatbot.git
cd 4r-chatbot
```

## 3. Python ortamı

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -U pip
.venv\Scripts\pip install -e ".[ingest,dev]"
```

## 4. Ortam değişkenleri

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
- `BILDIRIM_EPOSTA` + `SMTP_*` — varsa doldur (varsayılan alıcı `lojistik@4r.com.tr`;
  virgülle çoğaltılabilir). Yoksa talepler yalnızca panelde görünür — bot yine
  "yetkiliye aktarıyorum" der ama kimseye anlık haber gitmez.
- Diğerleri varsayılan kalır.

## 5. Atık kodu verisini yükle (ilk kurulumda bir kez)

```powershell
$env:PYTHONPATH="."
.venv\Scripts\python scripts\ingest_atik_kodlari.py data\raw\GUNCEL_ATIK_KODLARI_4R.xlsx
```

Beklenen çıktı — **birebir bu rakamlar olmalı**:
```
Ayrıştırılan 6-haneli kod: 842 | tehlikeli: 408 | en az bir tesiste kabul: 375
Yüklendi: 842 kayıt → atik_kodlari
```

## 6. Testler (yayından önce zorunlu doğrulama)

```powershell
.venv\Scripts\python -m pytest -q
```
Tamamı geçmeli. Geçmiyorsa **yayına alma**, önce hatayı çöz.

Kalite ölçümü (Gemini'yi gerçekten çağırır, ~1 dk):
```powershell
.venv\Scripts\python scripts\run_tests.py
```
Sonuçta **HATA sayısı 0 olmalı**. 0 değilse API anahtarı/kota sorunludur ve ölçüm geçersizdir.

## 7. Uygulamayı çalıştır

```powershell
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Bu terminal açık kalmalı. Kontrol: tarayıcıda `http://localhost:8000/health`
→ `{"status":"ok","atik_kodu":842,"belge":17}`

## 8. Cloudflare Tunnel → herkese açık HTTPS adres

Yeni bir PowerShell penceresinde:
```powershell
cloudflared tunnel --url http://localhost:8000
```
Çıktıdaki `https://xxxx.trycloudflare.com` adresini **not al**.

Test: `https://xxxx.trycloudflare.com/demo` → widget'ı dene.

---

> ## ⛔ BURADA DUR — kullanıcı onayı olmadan devam etme
>
> Bu nokta **"2. kademe test"in sonudur**. Kullanıcı botu siteye koymadan önce ekiple
> denemek istiyor. Yapılacak: yukarıdaki `/demo` adresini kullanıcıya ver ve dur.
>
> Adres internete açıktır ama **site henüz işin içinde değildir** — 4r.com.tr'de hiçbir
> değişiklik yapılmamıştır. Kullanıcı ve ekibi telefonlarından bu adresi deneyecek.
>
> Denenecekler:
> | Soru | Beklenen |
> |---|---|
> | `06 01 01 alıyor musunuz` | Merkez ve Kapaklı, tehlikeli — anında |
> | `boya çamuru alıyor musunuz` | Hangi tür olduğunu **sorar** |
> | `vidanjör hizmetiniz var mı` | Siteden cevap |
> | `50 kg altında atığım var nasıl gönderirim` | Kargo süreci |
> | `bugün hava nasıl` | Kibarca reddeder |
> | `lisans belgeniz ne zamana kadar geçerli` | Bilmiyor → iletişim formu çıkar |
> | Sonra `/yonetim` | Talep listede görünür |
>
> Bölüm 9 ve sonrası (WordPress'e ekleme) **ancak kullanıcı açıkça "devam" dediğinde**
> yapılır. Tünel penceresi kapanırsa adres ölür — o pencere açık kalmalı.

---

## 9. WordPress'e widget'ı ekle

4r.com.tr yönetim panelinde `</body>` öncesine (tema footer ya da "WPCode" /
"Insert Headers and Footers" eklentisi):

```html
<script src="https://xxxx.trycloudflare.com/widget.js"></script>
```

> ⚠️ Hızlı tünel adresi PC/tünel yeniden başlayınca **değişir** ve widget ölür.
> Bugün launch için kabul; hemen ardından Bölüm 11'deki kalıcı tünelle sabitlenmeli.

## 10. Canlı doğrulama

4r.com.tr'yi aç → sağ altta balon → sırayla dene:
1. `06 01 01 alıyor musunuz` → Merkez ve Kapaklı, tehlikeli (modelsiz, anında)
2. `boya çamuru alıyor musunuz` → 08 01 1x kodları
3. `vidanjör hizmetiniz var mı` → site içeriğinden cevap
4. `bugün hava nasıl` → kibarca reddetmeli

Panel altında KVKK notu görünür olmalı.

Ayrıca **yönetim panelini** kontrol et: `https://xxxx.trycloudflare.com/yonetim`
(kullanıcı `4r`, şifre `.env`'deki `YONETIM_SIFRE`). Bekleyen talepler burada görünür.

---

## 11. Yayından sonra — kalıcı kurulum (aynı gün yapılmalı)

Bugüne kadarki kurulumda bot **terminal açık kaldığı sürece** çalışır ve tünel adresi her
yeniden başlatmada değişir. İkisini de kalıcı hale getirmek tek script'le yapılır.

**Önce kalıcı tünel** (adres bir daha değişmez → WordPress'teki script satırı sabitlenir):
```powershell
cloudflared tunnel login
cloudflared tunnel create 4r-bot
cloudflared tunnel route dns 4r-bot bot.4r.com.tr
```

**Sonra — Yönetici olarak açılmış PowerShell'de:**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows_kur.ps1 -Tunel 4r-bot
```

> Windows varsayılan olarak `.ps1` dosyalarını çalıştırmaz ("betik çalıştırma bu sistemde
> devre dışı"). Yukarıdaki `-ExecutionPolicy Bypass` bunu **yalnızca o komut için** aşar;
> sistem ayarı değişmez.

Kurduğu üç Görev Zamanlayıcı görevi:

| Görev | Ne zaman | Ne yapar |
|---|---|---|
| `4R Bot` | Bilgisayar açılınca | Botu başlatır; çökerse 1 dk içinde yeniden kaldırır |
| `4R Tunel` | Bilgisayar açılınca | `bot.4r.com.tr` tünelini açar |
| `4R Bakim` | Saat başı | Bot yanıt vermiyorsa **yetkiliye uyarı gönderir**; veritabanını yedekler |

Ayrıca bilgisayarın uyku moduna girmesini kapatır. Yedekler `data\yedek\` altında
tarihle adlandırılır, `YEDEK_SAKLAMA_GUN` (varsayılan 14) günden eskiler silinir.

Kurulum sonrası WordPress'teki script satırını kalıcı adrese çevirin:
```html
<script src="https://bot.4r.com.tr/widget.js"></script>
```

**Haftalık tek iş:** yönetim panelini aç (`https://bot.4r.com.tr/yonetim`) — bekleyen
talepler ve botun cevaplayamadığı sorular orada.

## 12. Bitiş kontrol listesi

Kurulum ancak bu maddelerin **hepsi** doğrulandığında tamamlanmış sayılır:

```powershell
.venv\Scripts\python -m pytest -q                    # 123 test geçmeli
.venv\Scripts\python scripts\run_tests.py           # HATA sayısı 0 olmalı
curl.exe https://bot.4r.com.tr/health                 # atik_kodu 842, belge 17
```

| # | Kontrol | Beklenen |
|---|---|---|
| 1 | `/health` → `uyarilar` | **boş liste** — dolu ise ayar eksik, listeyi oku ve gider |
| 2 | `/health` → `atik_kodu` | `842` |
| 3 | `pytest` | 123 geçti |
| 4 | `run_tests.py` | HATA `0` — değilse ölçüm geçersizdir |
| 5 | Panel şifresiz | `401` verir (açık kalmamalı) |
| 6 | 4r.com.tr'de balon | açılıyor, `06 01 01` sorusuna cevap veriyor |
| 7 | `bugün hava nasıl` | kibarca reddediyor, yetkiliye aktarmıyor |
| 8 | Görev Zamanlayıcı | `4R Bot`, `4R Tunel`, `4R Bakim` — üçü de "Hazır" |
| 9 | Bilgisayarı yeniden başlat | 2 dk içinde `/health` yine cevap veriyor |
| 10 | `data\yedek\` | içinde bugünün tarihli `.db` dosyası var |

**1. madde en önemlisi:** `uyarilar` listesi botun kendi öz denetimi.

Yayını **bloklayan** uyarılar: `GEMINI_API_KEY boş` · `CORS_ORIGINS='*'` ·
`LOG_SAKLAMA_GUN=0` · `WHATSAPP_APP_SECRET boş`. Bunlardan biri varsa yayına alma.

Tek **kabul edilebilir** uyarı: *"Bildirim kanalı yok"* — SMTP bilgisi henüz gelmediyse
normaldir. Bu hâlde talepler kaybolmaz, yönetim panelinde birikir; ama kimseye anlık
haber gitmez, o yüzden **panel günde bir kez açılmalı**. SMTP gelince uyarı kaybolur.

## Sorun giderme

| Belirti | Sebep / çözüm |
|---|---|
| `/health` açılmıyor | uvicorn terminali kapanmış; Bölüm 7'yi tekrar çalıştır |
| Widget cevap vermiyor | Tünel adresi değişmiş → Bölüm 9'daki script satırını güncelle |
| Cevaplar "yoğunluk" diyor | Gemini kotası doldu → faturalandırma açık mı kontrol et |
| `ModuleNotFoundError` | `.venv\Scripts\pip install -e ".[ingest,dev]"` tekrar çalıştır |
| Widget siteye eklendi ama açılmıyor | `CORS_ORIGINS` 4r.com.tr'yi içeriyor mu, `.env` kaydedildi mi |
| `python` komutu Store açıyor | Windows sahte kısayolu → `py -3.12` kullan (Bölüm 1 notu) |
| `.ps1 çalıştırılamıyor` | `powershell -ExecutionPolicy Bypass -File ...` ile çağır |
| Görev Zamanlayıcı görevi "Çalışıyor" ama site ölü | Görev geçmişine bak; `.env` yolu göreli olduğu için görev **çalışma klasörü** proje kökü olmalı |
