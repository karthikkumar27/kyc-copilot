"""Typed settings. Every cloud-specific choice is an env var, never a code change."""

from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "staging", "production"] = "local"
    auth_mode: Literal["dev", "oidc"] = "dev"
    default_tenant: str = "limaupay"

    # Database: either a full URL (local) or parts (Cloud SQL unix socket on Cloud Run)
    database_url: str | None = None
    db_user: str = "kyc"
    db_password: str = ""
    db_name: str = "kyc"
    db_host: str = "localhost"
    db_socket_dir: str | None = None  # e.g. /cloudsql/PROJECT:REGION:INSTANCE
    redis_url: str = "redis://localhost:6379/0"

    # AI gateway (LiteLLM, OpenAI-compatible)
    llm_base_url: str = "http://localhost:4000/v1"
    llm_api_key: str = "sk-local-change-me"
    chat_model: str = "chat-default"
    embed_model: str = "embed-default"
    embedding_dim: int = 1536
    embed_batch_size: int = 16
    llm_timeout_s: float = 30.0

    # Adapter selection
    storage_provider: str = "local"
    queue_provider: str = "arq"
    ocr_provider: str = "local"
    pii_provider: str = "presidio"
    kyc_status_provider: str = "mock"

    # Local
    local_storage_dir: str = "/srv/var/uploads"
    kyc_mock_data_path: str = "data/synthetic/customers.json"

    # GCP
    gcp_project: str | None = None
    gcp_region: str = "asia-southeast1"
    gcs_bucket: str | None = None
    docai_location: str = "us"
    docai_processor_id: str | None = None
    dlp_location: str = "global"
    tasks_location: str | None = None
    tasks_queue: str | None = None
    worker_url: str | None = None
    tasks_service_account: str | None = None

    # Limits and tuning
    max_upload_mb: int = 20
    retrieval_k: int = 20
    retrieval_top_n: int = 6
    chunk_max_chars: int = 1500
    chunk_overlap_chars: int = 200

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        if self.environment == "production" and self.auth_mode == "dev":
            raise ValueError("AUTH_MODE=dev is not allowed when ENVIRONMENT=production")
        return self

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        pw = quote_plus(self.db_password)
        if self.db_socket_dir:
            return f"postgresql+asyncpg://{self.db_user}:{pw}@/{self.db_name}?host={self.db_socket_dir}"
        return f"postgresql+asyncpg://{self.db_user}:{pw}@{self.db_host}:5432/{self.db_name}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
