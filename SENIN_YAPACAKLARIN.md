# Senin Yapman Gerekenler — Tek Liste

Kod tarafında yapılacakları ben hallediyorum. Aşağıdakiler yalnızca **senin**
erişebildiğin hesaplar / bilgiler olduğu için sende kalıyor.

Sıralama önem sırasına göre. Acelesi yok — her biri geldiğinde ben bağlarım.

---

## 🔴 1. Yayına almak için zorunlu (bunlar olmadan bot canlıya çıkamaz)

### 1.1 GitHub'a gönderme onayı
Windows ofis bilgisayarının güncel kodu çekebilmesi için değişiklikleri GitHub'a
yüklemem gerekiyor. **Tek yapman gereken "gönder" demek.**

### 1.2 Ofis bilgisayarına kurulum
Windows PC'de Claude Code'u aç ve şunu yaz:
> `https://github.com/qeni8/4r-chatbot` reposunu klonla ve DEPLOY.md'yi izleyerek botu canlıya al.

Gerisini oradaki Claude yapar. Sana yalnızca onay ve Gemini anahtarını soracak.

### 1.3 Gemini faturalandırması
`aistudio.google.com` → Get API key → **Set up Billing** → kart ekle.
Ücretsiz katmanın günlük kotası yoğun günde biter ve bot "yoğunluk" mesajına düşer.
Gerçek maliyet bu hacimde **~$2-5/ay**. Google Cloud'da $10 bütçe uyarısı da kur.

### 1.4 Widget'ı siteye ekleme
Kurulum bitince sana bir adres verilecek. WordPress yöneticisinde `</body>` öncesine:
```html
<script src="https://VERILEN-ADRES/widget.js"></script>
```

---

## 🟡 2. Botun "yetkiliye aktarıyorum" sözünü tutması için

Bot cevaplayamadığı soruları kaydediyor ama **kimseye haber gidemiyor** — kanal yok.
(Yönetim panelinden görülebiliyor, ama kimse anlık haberdar olmuyor.)

### 2.1 Bildirim kime gidecek
Varsayılan: **lojistik@4r.com.tr**. Virgülle çoğaltılabilir, hepsine aynı anda gider:
```
BILDIRIM_EPOSTA=lojistik@4r.com.tr,info@4r.com.tr
```
Kaç kişi olacağını sen söyle, ben yazarım.

### 2.2 E-posta göndermek için SMTP bilgileri
Botun postayı hangi kutudan yollayacağı. `lojistik@4r.com.tr` olabilir — alıcıyla aynı
olması sorun değil. Hosting/e-posta panelinden alınır:
- Sunucu adresi (ör. `mail.4r.com.tr`)
- Port (genelde `587`)
- Kullanıcı adı (genelde e-posta adresinin kendisi)
- Şifre

> Bilmiyorsan hosting firmasına *"lojistik@4r.com.tr için SMTP giden posta ayarları"*
> diye sorman yeterli.

### 2.3 Telefon bildirimi (isteğe bağlı)
WhatsApp üzerinden gider, o da virgülle çoğaltılabilir: `905321112233,905339998877`.
**Meta WhatsApp hesabı canlıya alınmadan çalışmaz** — o yüzden şimdilik e-posta tek kanal.

### 2.4 Yönetim paneli şifresi
Talepleri göreceğin panel için belirleyeceğin bir şifre. Sen söyle, ben ayarlarım.

---

## 🟢 3. Botun daha çok soruyu cevaplayabilmesi için (içerik)

Bunlar gelmeden bot bu konularda **uydurmuyor, yetkiliye devrediyor** — doğru davranış,
ama cevaplayabilse daha iyi.

### 3.1 Mağaza fiyatları — en çok sorulan
`4r.com.tr/magaza/` sayfası JavaScript ile yüklendiği için otomatik çekilemiyor.
Ürün adı + fiyat + neyi kapsadığı yeterli:
```
- 50 kg altı tehlikeli atık kutusu — 1.250 TL — kutu + kargo + bertaraf dahil
```

### 3.2 Lisans bilgileri
Site sayfasından yalnızca çerez metni geliyor, lisans bilgisi yok.
Her lisans için: ad + numara + veren kurum + kapsam + geçerlilik tarihi.

### 3.3 SSS — en sık sorulan 10-15 soru
**En yüksek getirili madde.** Müşterilerin telefonda/e-postada en çok sorduğu şeyler,
senin verdiğin cevaplarla birlikte. Hem botun bilgisi hem kalite testinin çekirdeği olur.

### 3.4 "Merkez" tesisi neresi?
Atık kodu tablosunda üç tesis var (Merkez / Lüleburgaz / Kapaklı) ama sitede yalnızca
Kapaklı ve Lüleburgaz anlatılıyor. Müşteri "hangi tesise getireyim" dediğinde bot
bu ayrımı net yapamıyor. **Merkez ayrı bir tesis mi, Kapaklı'nın kendisi mi?**

### 3.5 Blog yazıları — opsiyonel
`4r.com.tr/blog/` şu an havuzda yok. İçinde müşteri sorusu cevaplayan bilgi varsa
"eklensin" de, scripti güncellerim.

---

## Nasıl ilerleyelim

Sen bunları toplarken ben geliştirmeye devam ediyorum (CLAUDE.md Bölüm 5).
Hangisi hazır olursa bana ilet — her biri bağlanması dakikalar süren işler.

**Hiçbiri hazır olmasa bile bot çalışır durumda:** talepler kaydedilir, panelden
görülür, bot uydurmaz. Yukarıdakiler botu "çalışır"dan "tam donanımlı"ya taşır.
