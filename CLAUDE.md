# 4R Çevre Chatbot — Proje Belleği

Web sitesine gömülü ve WhatsApp'tan çalışan müşteri destek botu.
Hedef hacim ~1.000-2.000 mesaj/ay. **Öncelik kalite: bot asla uydurmaz.**

---

## 1. Mimari

```
Mesaj → limit → selam kısayolu → yönlendirme
  ├─ saf atık kodu ("06 01 01 alıyor musunuz")
  │     → SQLite tablodan kesin cevap, modele HİÇ gitmez
  ├─ kod + başka soru ("06 01 01 fiyatı ne kadar")
  │     → tablo sonucu modele kaynak olur, model tam soruyu cevaplar
  └─ serbest soru
        → tüm site içeriği (17 belge) + varsa isimle eşleşen kodlar → LLM

Cevap gönderilmeden: içindeki atık kodları tabloya karşı doğrulanır.
Cevaplanamazsa → devir kaydı + yetkiliye bildirim + müşteriye iletişim formu.
```

**Neden vektör arama yok:** korpus 17 belge / ~5.000 kelime. Tamamı tek istekte modele
sığıyor. Parçalama + benzerlik araması yalnızca ıskalama riski ve kurulum yükü (Docker,
pgvector, 1 GB embedding modeli) getiriyordu. Kaldırıldı.

**Neden SQLite:** tek dosya, sunucu kurulumu yok. Windows kurulumu "Python kur → çalıştır".

**LLM:** Gemini (`LLM_PROVIDER`). Ücretsiz katman yoğun günde çöktüğü için faturalandırma
açık olmalı. Kalite yetmezse tek satırla `anthropic`.

---

## 2. Pazarlık konusu olmayan kurallar

1. **Grounding** — model yalnızca verilen kaynaklara dayanır. Bilmiyorsa uydurmaz.
2. **Atık kodu modele yorumlatılmaz** — kabul/red tablodan gelir. İsimle aramada birden
   çok aday varsa bot **sorar**, model seçmez. Cevaptaki kodlar tabloya karşı doğrulanır.
3. **Emin değilse insana devreder** — kendinden emin yanlış cevap en büyük risk.
4. **Mevzuat/hukuki yorum yapmaz**, fiyat taahhüdü vermez (kaynaktaki mağaza fiyatı hariç).
5. **Konu dışı soruda** kibarca reddeder, yetkiliye aktarmaz (hava durumu için insan meşgul edilmez).
6. **Her mesaj loglanır**, KVKK saklama süresi uygulanır.

---

## 3. Atık kodu tablosu

Kaynak: `data/raw/GUNCEL_ATIK_KODLARI_4R.xlsx` → **842 adet 6-haneli kod**
(408 tehlikeli, 375 en az bir tesiste kabul). Yükleme sonrası bu rakamlar birebir tutmalı.

| Alan | Not |
|---|---|
| `kod` / `kod_temiz` | `01 03 04*` / `010304` |
| `tehlikeli` | koddaki `*` işaretinden |
| `merkez` / `luleburgaz` / `kapakli` | işaretli = o tesiste kabul; **boş = kabul edilmez** |
| `bolum` / `grup` | 2 ve 4 haneli üst başlık bağlamı |

Excel'deki AÇIKLAMA (A/M) sütunu yok sayılır. Kabul/red yalnızca 6 haneli kodlardan.

---

## 4. Şirket künyesi

**4R Çevre ve Enerji San. ve Tic. A.Ş.** (Nadir Metal Grup) · Kuruluş 2018
Fatih Mah. 73. Sok. No:18, 59510 Kapaklı, Tekirdağ
+90 282 652 30 90 · info@4r.com.tr
Tesisler: Kapaklı · Lüleburgaz · Merkez *(bkz. açık soru: "Merkez" neresi?)*
Canonical istatistik: **+5900 firma · 92.000 ton/yıl** (anasayfa doğru; hakkımızda'daki
eski 2.500/85.000 düzeltildi).

---

## 5. Durum

**Tamam:** atık kodu tablosu · site içeriği · bot çekirdeği · guardrail'ler · web widget ·
WhatsApp adaptörü · limitler (günlük/oturum/IP) · KVKK saklama · devir kaydı + bildirim +
müşteri iletişim toplama · yönetim paneli (`/yonetim`).

**Ölçüm:** 40 soruluk kalite seti → 33 PASS / 7 REVIEW / 0 FAIL / 0 HATA.
112 hermetik pytest. `scripts/run_tests.py` HATA sayısı 0 değilse ölçüm geçersizdir.

**Kalan (kod):** Windows servisi + kalıcı tünel + yedekleme (yayın günü) · otomatik test (CI) ·
test setini gerçek SSS ile büyütme.

**Kalan (kullanıcıdan):** `SENIN_YAPACAKLARIN.md` — GitHub push onayı, Windows kurulumu,
Gemini faturalandırma, SMTP/WhatsApp bildirim bilgileri, panel şifresi, mağaza fiyatları,
lisans bilgileri, SSS, "Merkez" tesisi belirsizliği.

---

## 6. Çözülmüş tuzaklar (tekrar açmayın)

- Tarih `01.05.2024` içindeki `05.2024` atık kodu sanılıyordu → tarih/telefon maskeleniyor.
- "kod + fiyat" sorusunda sorunun geri kalanı yutuluyordu → tablo sonucu modele kaynak olur.
- Her LLM hatası sessizce "yoğunluk" mesajına çevriliyordu → kalite hiç ölçülememişti.
  Artık `LLMRateLimit` / `LLMError` ayrı, traceback loglanır, test HATA'yı gizlemez.
- Gemini 2.5 Flash düşünme tokenları çıktı bütçesini yiyip cevabı kesiyordu →
  `thinkingBudget=0`.
- Gemini geçici 503 ("high demand") döndüğünde bot düşüyordu → üstel beklemeyle 3 deneme.
- Prod'da boş `WHATSAPP_APP_SECRET` webhook'u herkese açık bırakıyordu.
- `oturum_id` tarayıcıda üretiliyor, taklit edilebilir → IP bazlı limit eklendi.
