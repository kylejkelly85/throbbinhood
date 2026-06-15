from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class AppConfig(BaseSettings):
    database_url: str = Field("sqlite+aiosqlite:///data/pipeline.db", env="DATABASE_URL")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    download_dir: str = Field("downloads/", env="DOWNLOAD_DIR")
    confidence_threshold: float = Field(0.7, env="CONFIDENCE_THRESHOLD")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

config = AppConfig()
