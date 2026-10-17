from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "AI Construction Takeoff API"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1"
    OPENAI_PDF_DETAIL: str = "high"
    MAX_UPLOAD_SIZE_MB: int = 45

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_openai_configured(self) -> bool:
        key = self.OPENAI_API_KEY.strip()
        return bool(key and not key.lower().startswith("your_") and len(key) >= 20)


settings = Settings()
