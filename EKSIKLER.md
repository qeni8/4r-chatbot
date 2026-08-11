# Eksik Veriler — Senden Bekleyenler

Bot bu konularda şu an **cevap veremiyor** ve "yetkilimize aktarayım" diyor.
Bu doğru davranış (uydurmuyor), ama veriyi verirsen doğrudan cevaplayabilir.

Aşağıya yazman yeterli — biçim önemli değil, ben düzenlerim.

---

## 1. Mağaza fiyatları (50 kg altı gönderim) — ÖNCELİKLİ

**Durum:** `4r.com.tr/magaza/` sayfası ürünleri JavaScript ile yüklüyor, otomatik çekilemiyor.
**Etki:** "50 kg altı atık göndermek kaç para", "tehlikeli atık taşıma ücreti ne kadar" gibi
sorular cevapsız kalıyor (test setindeki 3 fiyat sorusu).

Lazım olan: ürün adı + fiyat + neyi kapsadığı.

```
Örnek:
- 50 kg altı tehlikeli atık kutusu (30x30x40) — 1.250 TL — kutu + kargo + bertaraf dahil
- ...
```

**Not:** Bot yalnızca burada yazan fiyatları söyler; 50 kg üstünde "teklif al" akışına yönlendirir.

---

## 2. Lisans bilgileri

**Durum:** `4r.com.tr/lisanslar/` sayfasından yalnızca çerez metni geliyor, lisans bilgisi yok.
Sayfa havuzdan çıkarıldı (çöp veri botun kafasını karıştırıyordu).

Lazım olan: her lisans için ad + numara + veren kurum + kapsam + geçerlilik tarihi.

```
Örnek:
- Çevre İzin ve Lisans Belgesi — No: ... — Tekirdağ Çevre ve Şehircilik İl Md. —
  Kapsam: Ara depolama, geri kazanım — Geçerlilik: ../../....
- ...
```

---

## 3. SSS — en sık sorulan 10-15 soru

**En yüksek getirili eksik.** Hem botun bilgisi hem test setinin çekirdeği olur.
Müşterilerin telefonda/e-postada en çok sorduğu şeyleri, verdiğin cevaplarla birlikte yaz.

```
Örnek:
S: Atığı siz mi geliyorsunuz alıyorsunuz, biz mi getiriyoruz?
C: ...
```

---

## 4. "Merkez" tesisi neresi? — KISA AMA ÖNEMLİ

Atık kodu tablosunda üç tesis var: **Merkez / Lüleburgaz / Kapaklı**.
Ama site içeriğinde yalnızca Kapaklı (2018) ve Lüleburgaz (2020) anlatılıyor.

**Soru:** "Merkez" ayrı bir tesis mi, yoksa Kapaklı'nın kendisi mi?
Müşteri "hangi tesise getireyim" diye sorduğunda bot şu an bu ayrımı net yapamıyor.

Lazım olan: Merkez tesisin adresi (ya da "Kapaklı ile aynı" bilgisi).

---

## 5. Blog yazıları — opsiyonel

`4r.com.tr/blog/` şu an çekilmiyor. İçinde müşteri sorusu cevaplayan bilgi varsa
havuza eklenebilir. Sen "eklensin" dersen scripti güncellerim.

---

## Hazır olunca

Bilgileri bana yaz; `data/site/` altına düzenli birer belge olarak eklerim ve
bot aynı gün cevaplamaya başlar (yeniden başlatma yeterli, kod değişikliği gerekmez).
