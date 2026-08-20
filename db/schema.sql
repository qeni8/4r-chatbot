-- 4R Chatbot — SQLite şeması. Uygulama açılışında otomatik uygulanır (app/db.py).
-- Site içeriği burada tutulmaz; data/site/*.md dosyalarından okunur (app/knowledge.py).

-- Atık kodu tablosu (CLAUDE.md Bölüm 5). Kabul/red yalnızca 6 haneli kodlar üzerinden.
create table if not exists atik_kodlari (
    id          integer primary key autoincrement,
    kod         text    not null,            -- orijinal, örn. '01 03 04*'
    kod_temiz   text    not null,            -- yıldızsız + boşluksuz, örn. '010304'
    tanim       text,
    tehlikeli   integer not null default 0,
    merkez      integer not null default 0,
    luleburgaz  integer not null default 0,
    kapakli     integer not null default 0,
    bolum       text,                        -- 2 haneli üst başlık bağlamı
    grup        text                         -- 4 haneli üst başlık bağlamı
);
create index if not exists idx_atik_kod_temiz on atik_kodlari (kod_temiz);

-- Loglama (CLAUDE.md Bölüm 8). KVKK: oturum_id ham telefon değil, hash'lenmiş kimlik.
create table if not exists konusma_loglari (
    id          integer primary key autoincrement,
    kanal       text not null,               -- 'web' | 'whatsapp'
    oturum_id   text,                        -- istemci üretir (taklit edilebilir)
    istemci     text,                        -- KVKK: ham IP değil, hash'lenmiş kimlik
    soru        text not null,
    cevap       text,
    yontem      text,                        -- 'atik_kodu' | 'rag' | 'selam' | 'limit' | 'hata'
    kaynaklar   text,                        -- JSON: referans verilen belge/kod listesi
    model       text,
    created_at  text not null default (datetime('now'))
);
create index if not exists idx_loglar_created on konusma_loglari (created_at);
create index if not exists idx_loglar_oturum on konusma_loglari (oturum_id, created_at);
