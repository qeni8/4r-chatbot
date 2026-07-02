# 4R Çevre — Chatbot Projesi (Kickoff Brief)

> Bu dosya Claude Code oturumuna başlarken bağlam olarak verilmek üzere hazırlanmıştır.
> İdeali: repo kök dizinine `CLAUDE.md` adıyla koymak.

## 1. Amaç
4R Çevre ve Enerji için, hem **web sitesine gömülü** hem de **WhatsApp** üzerinden çalışan,
müşteri sorularını yanıtlayan bir destek chatbot'u. Bot, şirketin kendi belgelerine
(hizmetler, lisanslar, SSS) ve atık kodu veritabanına dayanarak cevap verir.
Hedef hacim: ~1.000–2.000 mesaj/ay. Öncelik: **kalite** (uydurma yok), maliyet ikincil.

## 2. Mimari Karar: RAG + Yapısal Sorgu Hibriti
- **Belgeler/SSS için RAG** (Retrieval-Augmented Generation): belgeler parçalanıp vektör
  veritabanında tutulur; soru gelince ilgili parçalar getirilip modele "yalnızca buna
  dayan" talimatıyla verilir. Fine-tuning YOK.
- **Atık kodları için yapısal sorgu**: modele uğramadan, doğrudan veritabanı eşleşmesiyle
  cevaplanır. Uydurma riskini sıfırlar. (Detay: Bölüm 5)
- Yönlendirme: gelen mesaj atık kodu sorgusu mu (örn. "06 01 01 alıyor musunuz") yoksa
  serbest soru mu — buna göre yapısal sorgu ya da RAG devreye girer.

## 3. Teknik Stack
| Katman | Seçim | Not |
|---|---|---|
| Backend | Python + FastAPI | Tek endpoint, iki kanal adaptörü (web + WhatsApp) |
| Veritabanı | Postgres + pgvector (Supabase) | Vektörler + atık kodu tablosu + loglar tek yerde |
| Embedding | Çok dilli model (Voyage / Cohere multilingual) | Türkçe kalitesi kritik; İngilizce-ağırlıklı modellerden kaçın |
| LLM | Claude Haiku 4.5 (varsayılan) → Sonnet 4.6 (zor sorular) | Prompt caching ile sabit bağlamda ~%90 tasarruf |
| Web | Basit JS sohbet widget'ı | Backend'e bağlanır |
| WhatsApp | Meta WhatsApp Cloud API (doğrudan, BSP'siz) | Webhook → aynı backend |
| Barındırma | Küçük VPS / Railway / Render | KVKK için bölge bilinçli seçilir |

## 4. Maliyet Beklentisi
- Model (LLM): ~$15–25/ay (Haiku ağırlıklı, caching ile daha az).
- WhatsApp: müşteri-başlatmalı destek "servis penceresi" içinde **ücretsiz**. Para yalnızca
  proaktif template (kampanya/bildirim) gönderilirse başlar; Türkiye oranları çok düşük.
- Vektör DB / embedding: bu hacimde ücretsiz katman ya da birkaç dolar.
- **Toplam gerçekçi: ~$15–60/ay.** Geliştirme maliyeti yok (kullanıcı + Claude Code).

## 5. Atık Kodu Tablosu — KESİNLEŞMİŞ ŞEMA
**Kaynak dosya:** `GU_NCEL_ATIK_KODLARI_4R.xlsx` (tek sayfa, 974 satır, 842 adet 6-haneli kod).

**Tablo şeması:**
| Alan | Tip | Açıklama |
|---|---|---|
| `kod` | text | Orijinal, örn. `01 03 04*` |
| `kod_temiz` | text | Yıldızsız + boşluksuz, örn. `010304` — kelime/tam eşleşme araması için |
| `tanim` | text | Atık tanımı |
| `tehlikeli` | bool | Koddaki `*` işaretinden türetilir |
| `merkez` | bool | İşaretliyse true |
| `luleburgaz` | bool | İşaretliyse true |
| `kapakli` | bool | İşaretliyse true |
| `bolum` / `grup` | text | Üst başlık bağlamı (2 ve 4 haneli) |

**İşleme kuralları:**
- Excel'deki **AÇIKLAMA (A/M) sütununu YOK SAY** — kullanılmayacak.
- Tesis işaretleri "x" ve "X" karışık → tek formata normalize et (büyük/küçük fark etmez = true).
- **İşaretli = o tesiste kabul edilir. Boş = o tesiste KABUL EDİLMEZ.**
- 6 haneli olmayan satırlar (bölüm/grup başlıkları) hiyerarşi bağlamı için ayrı tutulabilir,
  ama "kabul/red" sorgusu yalnızca 6 haneli kodlar üzerinden çalışır.

**Botun bu tablodan cevapladığı tipik soru:**
"Şu atık kodunu alıyor musunuz, hangi tesiste?" → kodu bul → hangi tesis(ler)de true →
tehlikeli mi → düz, kesin cevap (modele uğramadan).

## 6. Web Sitesi İçerik Kaynakları (ingestion listesi)
Aşağıdaki sayfalar otomatik script'le çekilip temizlenecek ve RAG havuzuna yüklenecek.
**Elle kopyalama değil — scriptle.**

**Kurumsal:** `/hakkimizda/`, `/lisanslar/`, `/kisisel-verilerin-korunmasi-aydinlatma-metni/`
**Hizmetler (11):** `/entegre-atik-yonetimi/`, `/tehlikeli-ve-tehlikesiz-atik-ara-depolama/`,
`/tehlikeli-ve-tehlikesiz-atik-geri-kazanim/`, `/atik-su-aritma-tesisi/`,
`/atiktan-turetilmis-yakit-aty-uretimi/`, `/elektrikli-ve-elektronik-atik-isleme/`,
`/akumulator-gecici-depolama/`, `/tehlikeli-atik-tasimaciligi/`, `/lisansli-vidanjor-hizmeti/`,
`/ibc-tank-alim-satim-yikama-rebottle/`, `/solvent-geri-kazanimi-solvent-distilasyonu/`
**Diğer:** `/hizmetlerimiz/`, `/iletisim/`, `/blog/` (yazılar), `/50-kg-alti-atik-gonderimi-kilavuzu/`
**Mağaza/fiyat:** `/magaza/` — 50 kg altı atık için fiyatlı ürün var (bot küçük gönderimde
fiyat söyleyebilir); 50 kg üstü "teklif al" akışına yönlendirilir.

## 7. Şirket Künyesi (botun temel bilgisi)
- **Unvan:** 4R Çevre ve Enerji San. ve Tic. A.Ş. (Nadir Metal Grup şirketi)
- **Adres:** Fatih Mah. 73. Sok. No:18, 59510 Kapaklı, Tekirdağ
- **Tel:** +90 282 652 30 90 — **E-posta:** info@4r.com.tr
- **Kuruluş:** 2018
- **Tesisler / şubeler:** Kapaklı, Lüleburgaz, Merkez (bu üçü atık kodu tablosundaki
  sütunlarla birebir örtüşür)
- **Sosyal:** Instagram @4r_env.energy, LinkedIn, YouTube

## 8. Kalite & Guardrail Gereksinimleri (pazarlık konusu değil)
- **Grounding:** Model yalnızca getirilen belgelere/tablo sonucuna dayanır. Bilgi yoksa uydurmaz.
- **"Bilmiyorum" → insana devir:** Emin olunamayan durumda "kesin bilgi veremiyorum, sizi
  yetkilimize aktarayım" der. Kendinden emin yanlış cevap = en büyük risk.
- **Atık kodu & mevzuat modele yorumlatılmaz.** Kod sorgusu tablodan döner. Mevzuat/hukuki
  yorumda bot hüküm vermez, "bağlayıcı bilgi için yetkilimize danışın" der.
- **Kaynak gösterme:** Cevabın hangi belgeden/koddan geldiği izlenebilir olmalı.
- **Konu sınırı:** Fiyat taahhüdü vermez (mağaza fiyatları hariç), alakasız sorulara girmez.
- **Loglama:** Tüm sorular/cevaplar loglanır → eksikleri görüp havuzu iyileştirmek için.

## 9. KVKK Notları
- Müşteri konuşmaları kişisel veridir. Barındırma bölgesi ve saklama süresi bilinçli seçilir.
- Geçmiş yazışmalar bota verilecekse, isim/telefon gibi kişisel bilgiler ayıklanır.
- Sitedeki KVKK aydınlatma metniyle tutarlı bir gizlilik bildirimi botta da gösterilir.

## 10. Yol Haritası
0. **Veri toplama** *(kullanıcı)* — devam ediyor (bkz. Bölüm 11).
1. **Atık kodu tablosu** — xlsx → temiz Postgres tablosu (şema Bölüm 5).
2. **Site ingestion** — sayfaları scriptle çek → temizle → parçala → embed → pgvector.
3. **RAG çekirdeği + yapısal sorgu** — yönlendirme + grounding'li cevap üretimi (önce web).
4. **Test seti** — 50–100 gerçek soru + doğru cevap; çalıştır, saçmaladığı yerleri düzelt.
5. **Guardrail + insana devir + loglama.**
6. **Web widget** → siteye gömme.
7. **WhatsApp** — Meta Cloud API webhook → aynı backend.
8. **İzle & iyileştir** *(çoğu kullanıcı)*.

> Adım 1–3 "ayağa kaldırma", 4–5 "kaliteyi garanti altına alma", 6–7 "yayın".

## 11. Hâlâ Toplanacak Veriler (build sırasında paralel ilerleyebilir)
- [ ] Lisans / sertifika **PDF'leri** (sitede link var; geçerlilik tarihleriyle toplu bir yerde).
- [ ] **SSS** ve en sık sorulan **10–15 soru** (hem içerik hem test setinin çekirdeği).
- [ ] Fiyat politikası netliği: hangi durumda mağaza fiyatı, hangi durumda "teklif al".

## 13. Alınan Kararlar (oturum notları)
- **İsimle arama:** Müşteri kod yerine atık adı yazarsa desteklenir. Kademeli:
  (1) tablo tanımında kelime araması, (2) ileride semantik arama (RAG embedding altyapısı
  yeniden kullanılır). Birden çok eşleşmede bot **sorar**, koda asla model karar vermez.
- **Grup sorgusu:** 2/4 haneli prefix sorgusu hafifçe desteklenir; 8-10'dan fazla sonuçta
  liste dökülmez, özetlenip soru sorulur.
- **Cevap tonu:** Kısa + yönlendirici. Önce net cevap, sonra sonraki adım. "Siz" dili,
  jargonsuz. Tehlikeli sınıf bilgisi eklenir (taşıma/işlem ona göre değişir).
- **Köprü:** "Alıyoruz" sonrası müşteri "nasıl gönderirim / fiyat" sorar →
  50 kg altı mağaza fiyatı, 50 kg üstü "teklif al". Site içeriğine bağlı (Adım 2).

## 14. İlerleme
- [x] **Adım 1 — Atık kodu tablosu** tamam: 842 kod Postgres'e yüklendi, yapısal sorgu
  test edildi (format toleransı, tehlikeli/tesis bilgisi, olmayan kodda "yetkiliye devir").
- [x] **Adım 2 — Site ingestion** tamam: 18 sayfa çekildi+temizlendi → 43 parça (başlık dahil)
  → ücretsiz yerel embedding → **hibrit arama** (anlamsal + Türkçe FTS, RRF). Test edildi, kaliteli.
- **Canonical istatistik (Bölüm 12 çözüldü):** +5900 firma · 92.000 ton/yıl (anasayfa doğru).
  Hakkımızda'daki eski 2.500/85.000 düzeltildi.
- **Embedding kararı (güncellendi):** ücretsiz yerel model
  `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, **768 boyut**. Voyage iptal.
  (e5-large denendi → fastembed/onnxruntime harici-veri hatası; mpnet'e geçildi.)
- **Retrieval kararı:** tek başına anlamsal arama Türkçe'de zayıf kaldı → hibrit (vektör + `to_tsvector('turkish')`)
  RRF ile birleştirildi. Varsayılan k=5.
- **LLM kararı:** önce Gemini Flash (ücretsiz), tatmin olunmazsa Anthropic'e geçiş (`LLM_PROVIDER` ile). Sağlayıcıdan bağımsız kuruldu.
- [x] **Adım 3 — Bot beyni** çalışıyor: yönlendirici (`router.py`) + yapısal cevap (`waste_lookup.py`) +
  hibrit RAG (`retrieval.py`) + model cevabı (`llm.py`, Gemini/Anthropic) + `/chat` orkestrasyon + loglama.
  Canlı test: grounding doğru (5900 firma, solvent listesi, adres), bilmediğinde uydurmadan yetkiliye devir,
  fiyat taahhüdü yok. Gemini ücretsiz katman 429'a karşı retry + güvenli fallback eklendi.
- [x] **Anti-spam / maliyet koruması** (`limits.py`): günlük 200 (tüm bot) + oturum 25/gün +
  ani 5/60sn. Sınır aşımı modele gitmeden nazik mesajla durur. Test edildi.
- **Maliyet tavanı:** Google tarafında $10/ay bütçe uyarısı (kurulacak). Asıl sert tavan
  uygulama içi günlük 200 limit (maks ~$5/ay senaryosu).
- [x] **Adım 6 — Web widget**: `web/widget.js` (gömülebilir), `/widget.js` + `/demo`, CORS. Tarayıcıda canlı test edildi.
- [x] **Adım 7 — WhatsApp**: `whatsapp.py` + webhook (verify/POST), ortak `bot.py`. Lokal test edildi.
  Canlı için Meta token + genel webhook URL (yayın) gerekir.
- **Barındırma:** şu an lokal (dev). Yayın için küçük VPS (TR/EU), ~$5-10/ay — EN SON.
- **Yayın öncesi açık iş:** test seti (Adım 4), isimle atık arama (Bölüm 13).
- **Yayın (en son):** VPS deploy + widget script URL + Meta WhatsApp kurulumu + Google ücretli plan & $10 tavan.

## 12. Çözülecek Tutarsızlık (önemli not)
Sitede iki farklı istatistik var: anasayfa "+5900 firma / 92.000 ton" derken, hakkımızda
sayfası "2.500+ tesis / 85.000 ton/yıl" diyor. **Çelişen bilgi = botun çelişmesi.**
Hangisi güncel/doğruysa o sabitlenmeli, diğeri havuzdan çıkarılmalı.
