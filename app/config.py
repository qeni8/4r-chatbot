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

    app_env: str = "dev"
    log_level: str = "info"
    cors_origins: str = "*"  # prod: "https://4r.com.tr,https://www.4r.com.tr" (virgülle)

    # Konuşma hafızası
    gecmis_turu: int = 3        # modele verilecek önceki soru/cevap çifti sayısı
    gecmis_dakika: int = 120    # bu süreden eski turlar hafızaya alınmaz

    # Anti-spam / maliyet koruması
    daily_limit: int = 200          # tüm bot, günlük toplam mesaj
    session_daily_limit: int = 25   # tek oturum/kişi, günlük
    burst_limit: int = 5            # tek oturum, son 60 saniye


settings = Settings()
