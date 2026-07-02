from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://4r:4r_dev_pw@localhost:5432/4r_chatbot"

    llm_provider: str = "groq"  # "groq" | "gemini" | "anthropic"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    anthropic_api_key: str = ""
    llm_model_default: str = "claude-haiku-4-5-20251001"
    llm_model_hard: str = "claude-sonnet-4-6"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    embedding_dim: int = 768

    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    app_env: str = "dev"
    log_level: str = "info"

    # Anti-spam / maliyet koruması
    daily_limit: int = 200          # tüm bot, günlük toplam mesaj
    session_daily_limit: int = 25   # tek oturum/kişi, günlük
    burst_limit: int = 5            # tek oturum, son 60 saniye


settings = Settings()
