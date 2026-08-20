from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = "data/4r_chatbot.db"

    llm_provider: str = "gemini"  # "gemini" | "anthropic"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    # 2.5 Flash "düşünen" bir model; düşünme tokenları çıktı bütçesinden harcanır ve
    # cevabı cümle ortasında kestiriyordu. Bu iş (verilen metinden cevap üretme) düşünme
    # gerektirmiyor → kapalı. Artırmak için >0 bir bütçe verilebilir.
    gemini_thinking_budget: int = 0

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"

    llm_max_tokens: int = 700
    llm_timeout: int = 60

    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_app_secret: str = ""  # gelen webhook imza (X-Hub-Signature-256) doğrulaması

    # --- Devir bildirimi ---
    # Bot cevaplayamayıp yetkiliye devrettiğinde talep buralara bildirilir.
    # Hiçbiri ayarlı değilse kayıt yine tutulur (yönetim panelinden görülür).
    bildirim_eposta: str = ""      # alıcı adres(ler), virgülle
    bildirim_whatsapp: str = ""    # yetkili telefonu, ör. 905321112233
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    smtp_from: str = ""            # boşsa smtp_user kullanılır
    bildirim_arkaplan: bool = True  # testlerde False → eşzamanlı

    # --- Yönetim paneli ---
    # Şifre boşsa panel tamamen kapalıdır (kazara açık kalmasın).
    yonetim_kullanici: str = "4r"
    yonetim_sifre: str = ""

    app_env: str = "dev"
    log_level: str = "info"

    # --- Bakım (scripts/bakim.py, saat başı) ---
    saglik_url: str = "http://localhost:8000/health"
    yedek_saklama_gun: int = 14
    # KVKK: konuşma logları kişisel veridir, süresiz saklanamaz. Açılışta bu yaştan
    # eski kayıtlar silinir (CLAUDE.md Bölüm 9). 0 = temizleme kapalı.
    log_saklama_gun: int = 180
    cors_origins: str = "*"  # prod: "https://4r.com.tr,https://www.4r.com.tr" (virgülle)

    # Konuşma hafızası
    gecmis_turu: int = 3        # modele verilecek önceki soru/cevap çifti sayısı
    gecmis_dakika: int = 120    # bu süreden eski turlar hafızaya alınmaz

    # Anti-spam / maliyet koruması
    daily_limit: int = 200          # tüm bot, günlük toplam mesaj
    session_daily_limit: int = 25   # tek oturum/kişi, günlük
    burst_limit: int = 5            # tek oturum, son 60 saniye
    # oturum_id tarayıcıda üretilir → değiştirilerek oturum limiti aşılabilir.
    # IP bazlı ikinci sınır, tek kişinin günlük bütçeyi bitirmesini engeller.
    ip_daily_limit: int = 60


settings = Settings()


def yapilandirma_uyarilari() -> list[str]:
    """Yayında sessizce bozuk çalışmaya yol açacak ayarları tespit eder.

    Açılışta loglanır ve /health üzerinden görünür; kurulumdaki en sık hatalar burada
    yakalanmazsa bot çalışıyor görünüp her soruda yetkiliye devrediyor olur.
    """
    u: list[str] = []
    prod = settings.app_env != "dev"

    if settings.llm_provider == "gemini" and not settings.gemini_api_key:
        u.append("GEMINI_API_KEY boş — serbest sorular cevaplanamaz, hepsi yetkiliye devredilir.")
    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        u.append("ANTHROPIC_API_KEY boş — serbest sorular cevaplanamaz.")
    if settings.llm_provider not in ("gemini", "anthropic"):
        u.append(f"LLM_PROVIDER tanınmıyor: {settings.llm_provider!r} (gemini | anthropic)")

    if prod:
        if settings.cors_origins.strip() == "*":
            u.append("CORS_ORIGINS='*' — widget her siteden çağrılabilir; 4r.com.tr'ye daraltın.")
        if not settings.whatsapp_app_secret and settings.whatsapp_access_token:
            u.append("WHATSAPP_APP_SECRET boş — gelen webhook istekleri reddedilecek.")
        if settings.log_saklama_gun <= 0:
            u.append("LOG_SAKLAMA_GUN=0 — konuşma logları süresiz saklanır (KVKK riski).")
        if not (settings.bildirim_eposta or settings.bildirim_whatsapp):
            u.append("Bildirim kanalı yok — bot 'yetkiliye aktarıyorum' diyor ama kimseye "
                     "haber gitmiyor. BILDIRIM_EPOSTA veya BILDIRIM_WHATSAPP ayarlayın.")
    return u
