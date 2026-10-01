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

    # LLM: any OpenAI-compatible provider (defaults: Groq)
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"
    llm_timeout_s: float = 30.0
    price_in_per_mtok: float = 0.0  # USD per 1M prompt tokens (0 = free tier)
    price_out_per_mtok: float = 0.0

    # retrieval and limits
    top_k: int = 5
    min_score: float = 0.45  # cosine-similarity gate before the LLM is called; tune with the eval
    max_question_chars: int = 1000
    prompt_version: str = "v2"  # "v1" = base rules only; "v2" adds injection-hardening (see EVALUATION.md)
    rate_limit_per_min: int = 10
    rate_limit_per_day: int = 100


settings = Settings()
