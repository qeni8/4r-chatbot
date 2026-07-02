create extension if not exists vector;

-- Atık kodu tablosu (Brief Bölüm 5). Kabul/red sorgusu yalnızca 6 haneli kodlar üzerinden.
create table if not exists atik_kodlari (
    id          serial primary key,
    kod         text    not null,            -- orijinal, örn. '01 03 04*'
    kod_temiz   text    not null,            -- yıldızsız + boşluksuz, örn. '010304'
    tanim       text,
    tehlikeli   boolean not null default false,
    merkez      boolean not null default false,
    luleburgaz  boolean not null default false,
    kapakli     boolean not null default false,
    bolum       text,                         -- 2 haneli üst başlık bağlamı
    grup        text,                         -- 4 haneli üst başlık bağlamı
    embedding   vector(768)                   -- tanım vektörü (isimle semantik arama)
);
create index if not exists idx_atik_kod_temiz on atik_kodlari (kod_temiz);
create index if not exists idx_atik_embedding on atik_kodlari using hnsw (embedding vector_cosine_ops);

-- RAG: belge kaynakları + parçalar
create table if not exists documents (
    id          serial primary key,
    kaynak      text not null,                -- URL veya dosya yolu
    baslik      text,
    tur         text,                         -- 'web' | 'pdf' | 'sss'
    created_at  timestamptz not null default now()
);

-- Embedding: ücretsiz yerel model paraphrase-multilingual-mpnet-base-v2 → 768 boyut.
create table if not exists chunks (
    id          serial primary key,
    document_id integer not null references documents(id) on delete cascade,
    icerik      text not null,
    embedding   vector(768),
    token_sayisi integer,
    created_at  timestamptz not null default now()
);
create index if not exists idx_chunks_embedding
    on chunks using hnsw (embedding vector_cosine_ops);

-- Loglama (Brief Bölüm 8). KVKK: oturum_id ham telefon değil, hash'lenmiş kimlik tutar.
create table if not exists konusma_loglari (
    id          serial primary key,
    kanal       text not null,                -- 'web' | 'whatsapp'
    oturum_id   text,
    soru        text not null,
    cevap       text,
    yontem      text,                         -- 'atik_kodu' | 'rag' | 'devir'
    kaynaklar   jsonb,                         -- referans verilen doc/kod id'leri
    model       text,
    guven       text,                         -- confidence / fallback işareti
    created_at  timestamptz not null default now()
);
create index if not exists idx_loglar_created on konusma_loglari (created_at);
