from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str  # required: no insecure default
    jwt_expire_minutes: int = 60
    max_upload_mb: int = 10
    max_docs_per_user: int = 50
    queue_sync: bool = False  # tests/dev only: run ingestion inline instead of via RQ
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 800
    chunk_overlap: int = 120


settings = Settings()
