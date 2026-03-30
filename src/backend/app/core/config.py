from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    ui_url: str = Field(default="http://localhost:3000", alias="UI_URL")

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_access_expires_minutes: int = Field(default=30, alias="JWT_ACCESS_EXPIRES_MINUTES")
    jwt_refresh_expires_minutes: int = Field(default=10080, alias="JWT_REFRESH_EXPIRES_MINUTES")
    auth_refresh_cookie_name: str = Field(default="notebooklm_refresh", alias="AUTH_REFRESH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="AUTH_COOKIE_SAMESITE")

    database_url: str = Field(
        default="sqlite:///./notebooklm_dev.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_key_prefix: str = Field(default="notebooklm", alias="REDIS_KEY_PREFIX")
    rq_queue_name_core: str = Field(default="notebooklm-core", alias="RQ_QUEUE_NAME_CORE")
    rq_queue_name_podcast: str = Field(default="notebooklm-podcast", alias="RQ_QUEUE_NAME_PODCAST")
    rq_strict_mode: bool = Field(default=True, alias="RQ_STRICT_MODE")
    rq_worker_role: str = Field(default="core", alias="RQ_WORKER_ROLE")
    rq_worker_queues: str = Field(default="", alias="RQ_WORKER_QUEUES")
    job_max_retries_ingestion: int = Field(default=2, alias="JOB_MAX_RETRIES_INGESTION")
    job_max_retries_podcast: int = Field(default=2, alias="JOB_MAX_RETRIES_PODCAST")

    milvus_uri: str = Field(default="http://localhost:19530", alias="MILVUS_URI")
    milvus_collection: str = Field(default="notebooklm_chunks", alias="MILVUS_COLLECTION")
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")

    cors_origins: str = Field(default="", alias="CORS_ORIGINS")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_chat_model: str = Field(default="qwen3:8b", alias="OLLAMA_CHAT_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBED_MODEL")
    ollama_request_timeout_seconds: int = Field(default=180, alias="OLLAMA_REQUEST_TIMEOUT_SECONDS")
    ollama_podcast_timeout_seconds: int = Field(default=180, alias="OLLAMA_PODCAST_TIMEOUT_SECONDS")
    ollama_disable_thinking: bool = Field(default=True, alias="OLLAMA_DISABLE_THINKING")
    ollama_prewarm_on_startup: bool = Field(default=True, alias="OLLAMA_PREWARM_ON_STARTUP")
    ollama_prewarm_timeout_seconds: int = Field(default=30, alias="OLLAMA_PREWARM_TIMEOUT_SECONDS")

    enable_cross_encoder_rerank: bool = Field(default=False, alias="ENABLE_CROSS_ENCODER_RERANK")
    cross_encoder_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        alias="CROSS_ENCODER_MODEL",
    )

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )

    zep_api_key: str = Field(default="", alias="ZEP_API_KEY")
    zep_project_id: str = Field(default="", alias="ZEP_PROJECT_ID")
    enable_zep_memory: bool = Field(default=False, alias="ENABLE_ZEP_MEMORY")

    assemblyai_api_key: str = Field(default="", alias="ASSEMBLYAI_API_KEY")
    firecrawl_api_key: str = Field(default="", alias="FIRECRAWL_API_KEY")

    enable_audio_parsing: bool = Field(default=True, alias="ENABLE_AUDIO_PARSING")
    enable_youtube_parsing: bool = Field(default=True, alias="ENABLE_YOUTUBE_PARSING")
    enable_web_scraping: bool = Field(default=True, alias="ENABLE_WEB_SCRAPING")

    max_upload_bytes: int = Field(default=52428800, alias="MAX_UPLOAD_BYTES")
    max_sources_per_user: int = Field(default=200, alias="MAX_SOURCES_PER_USER")
    idempotency_ttl_seconds: int = Field(default=7200, alias="IDEMPOTENCY_TTL_SECONDS")
    oauth_state_ttl_seconds: int = Field(default=600, alias="OAUTH_STATE_TTL_SECONDS")
    oauth_exchange_code_ttl_seconds: int = Field(default=180, alias="OAUTH_EXCHANGE_CODE_TTL_SECONDS")
    podcast_tts_provider: str = Field(default="kokoro", alias="PODCAST_TTS_PROVIDER")
    kokoro_repo_id: str = Field(default="hexgrad/Kokoro-82M", alias="KOKORO_REPO_ID")
    kokoro_spacy_model: str = Field(default="en_core_web_sm", alias="KOKORO_SPACY_MODEL")
    kokoro_voice_host: str = Field(default="af_heart", alias="KOKORO_VOICE_HOST")
    kokoro_voice_analyst: str = Field(default="am_adam", alias="KOKORO_VOICE_ANALYST")
    kokoro_prewarm_on_startup: bool = Field(default=True, alias="KOKORO_PREWARM_ON_STARTUP")
    podcast_context_max_chars: int = Field(default=4500, alias="PODCAST_CONTEXT_MAX_CHARS")
    podcast_chunks_per_source: int = Field(default=3, alias="PODCAST_CHUNKS_PER_SOURCE")
    podcast_chunk_excerpt_chars: int = Field(default=420, alias="PODCAST_CHUNK_EXCERPT_CHARS")
    podcast_tts_timeout_seconds: int = Field(default=600, alias="PODCAST_TTS_TIMEOUT_SECONDS")
    podcast_mix_timeout_seconds: int = Field(default=60, alias="PODCAST_MIX_TIMEOUT_SECONDS")
    usage_cost_per_1k_prompt: float = Field(default=0.0, alias="USAGE_COST_PER_1K_PROMPT")
    usage_cost_per_1k_response: float = Field(default=0.0, alias="USAGE_COST_PER_1K_RESPONSE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


def validate_required_runtime_settings(settings: Settings) -> None:
    import logging

    _logger = logging.getLogger(__name__)

    # S2: Reject insecure JWT secret in production
    if settings.environment == "production" and settings.jwt_secret in ("change-me", ""):
        raise RuntimeError(
            "JWT_SECRET must be set to a strong random value in production. "
            "Cannot start with the default 'change-me' secret."
        )

    # S3: Reject localhost/wildcard CORS origins in production
    if settings.environment == "production":
        origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] if settings.cors_origins else [settings.ui_url]
        for origin in origins:
            if "localhost" in origin or origin == "*":
                raise RuntimeError(
                    f"CORS origin '{origin}' is not allowed in production. "
                    "Set CORS_ORIGINS to your production domain(s)."
                )

    if not settings.enable_zep_memory:
        _logger.info("Zep memory disabled — using local DB summaries only.")
        return

    if not settings.zep_api_key or not settings.zep_project_id:
        _logger.warning(
            "Zep credentials missing — memory will use local DB fallback. "
            "Set ZEP_API_KEY and ZEP_PROJECT_ID for full memory features."
        )
        return

    try:
        UUID(settings.zep_project_id)
    except ValueError:
        _logger.warning("ZEP_PROJECT_ID is not a valid UUID — Zep integration disabled.")
