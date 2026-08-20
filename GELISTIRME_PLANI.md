# Geliştirme ve Profesyonelleştirme Planı

**Bugünkü durum:** Bot fonksiyonel olarak tamam ve sağlamlaştırıldı (1.026 satır kod,
84 test, kalite ölçümü 33 PASS / 0 FAIL). Aşağıdaki plan, "çalışan bir bot"tan
"şirketin güvenerek işlettiği bir sistem"e geçişi tarif eder.

Fazlar değer sırasına göre dizildi. Her faz kendi başına yayına alınabilir.

---

## Faz 1 — Botun sözünü tutması ⭐ EN KRİTİK

**Sorun:** Bot günde onlarca kez *"sizi yetkilimize aktarayım"* diyor.
**Kimseye hiçbir bildirim gitmiyor.** Müşteri beklerken kimsenin haberi yok.
Bu, ürünün verdiği sözü tutmaması demek — ve cevapsız kalan her soru kaybedilen bir müşteri.

| # | İş | Ne kazandırır |
|---|---|---|
| 1.1 | **Devir kaydı tablosu** — bot devrettiğinde soru, oturum geçmişi ve zaman kaydedilir | Hiçbir talep kaybolmaz |
| 1.2 | **Bildirim** — devir anında yetkiliye e-posta gider (soru + konuşma özeti) | Aynı gün dönüş yapılabilir |
| 1.3 | **İletişim toplama** — bot "size dönelim mi?" diye sorar, ad + telefon alır | Kayıp talep → satış fırsatı |
| 1.4 | Bildirim testleri + SMTP yoksa panele düşme (bağımlılık kırılmasın) | Kurulum kolaylığı |

**Not:** 1.3 bu botun ticari değerini en çok artıran özellik. Şu an "teklif alın"
deyip müşteriyi siteye yönlendiriyoruz; orada kayboluyor.

---

## Faz 2 — 4R'nin botu yönetebilmesi

**Sorun:** Loglar veritabanında ama bunları görmek için terminale girmek gerekiyor.
Şirkette kimse bunu yapmayacak. Veri var, görünürlük yok.

| # | İş | Ne kazandırır |
|---|---|---|
| 2.1 | **Yönetim paneli** `/yonetim` (şifreli) — son konuşmalar, cevapsız sorular, devir kayıtları, günlük hacim | Botu şirket işletebilir |
| 2.2 | **Günlük özet e-postası** — dün kaç soru, kaç devir, hangi sorular cevapsız | Pasif izleme |
| 2.3 | **Bilgi boşluğu raporu** — en çok devredilen konular listesi | Havuzu neyle besleyeceğini söyler |

---

## Faz 3 — Yayında güvenilirlik

**Sorun:** Bot ofis PC'sinde bir terminal penceresinde çalışacak. Pencere kapanırsa,
PC yeniden başlarsa ya da uykuya girerse bot ölür ve kimse fark etmez.

| # | İş | Ne kazandırır |
|---|---|---|
| 3.1 | **Windows servisi** (NSSM) + otomatik başlangıç | PC yeniden başlasa bot ayakta |
| 3.2 | **Kalıcı tünel** `bot.4r.com.tr` | Adres bir daha değişmez, site script'i sabit |
| 3.3 | **Otomatik yedekleme** — SQLite dosyasının günlük kopyası | Konuşma geçmişi kaybolmaz |
| 3.4 | **Ayakta mı kontrolü** — bot düşerse haber ver | Sessiz ölüm olmaz |

---

## Faz 4 — Kalitenin zamanla korunması

**Sorun:** Bugün kalite iyi. Ama içerik değişince, prompt güncellenince ya da model
sürümü değişince sessizce bozulabilir. Şu an bunu yalnızca elle fark ederiz.

| # | İş | Ne kazandırır |
|---|---|---|
| 4.1 | **Otomatik test (CI)** — her değişiklikte 84 test koşar | Bozuk kod fark edilmeden ilerlemez |
| 4.2 | **Test setini büyütme** 40 → 100 soru (gerçek SSS ile) | Ölçüm gerçeği yansıtır |
| 4.3 | **Aylık kalite raporu** — set otomatik koşar, sonuç kaydedilir | Kalite düşüşü erken görülür |

---

## Senden veri bekleyenler (paralel ilerler)

`EKSIKLER.md` — mağaza fiyatları · lisans bilgileri · SSS · "Merkez" tesisi belirsizliği.
Bunlar gelmeden bot bu konularda cevap veremez (uydurmuyor, devrediyor — doğru davranış).

---

## Önerilen sıra

1. **Faz 1** (bugün) — sözünü tutmayan bir bot yayına çıkmamalı
2. **Faz 3** (yayın günü) — servis + kalıcı adres
3. **Faz 2** (yayından hemen sonra) — ilk gerçek verilerle panel anlam kazanır
4. **Faz 4** (sürekli)
