from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, model_validator
from typing import Optional


class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str = "MISSING_GEMINI_API_KEY"
    kaggle_username: Optional[str] = None
    kaggle_key: Optional[str] = None

    # Database
    database_url: Optional[str] = None

    # Security
    secret_key: str = "change-me-in-production"
    enforce_tenant_isolation: bool = True
    allow_code_execution: bool = False
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = Field(default="lax", pattern="^(lax|strict|none)$")

    # Execution limits
    max_execution_time: int = Field(default=45, ge=1, le=3600)
    max_memory_mb: int = Field(default=1536, ge=128, le=16384)
    max_upload_size_mb: int = Field(default=50, ge=1, le=1024)
    max_upload_rows: int = Field(default=1_000_000, ge=1, le=10_000_000)
    max_upload_columns: int = Field(default=500, ge=1, le=10_000)
    max_image_pixels: int = Field(default=25_000_000, ge=1, le=100_000_000)

    # In-memory tenant runtime limits
    max_tenants: int = Field(default=100, ge=1, le=100_000)
    max_datasets_per_tenant: int = Field(default=100, ge=1, le=100_000)
    max_dataset_memory_mb_per_tenant: int = Field(default=512, ge=1, le=1_048_576)
    max_models_per_tenant: int = Field(default=100, ge=1, le=100_000)
    max_preprocessors_per_tenant: int = Field(default=100, ge=1, le=100_000)
    max_chat_sessions_per_tenant: int = Field(default=100, ge=1, le=100_000)
    max_chat_messages_per_session: int = Field(default=1000, ge=1, le=1_000_000)
    tenant_eviction_mode: str = Field(default="lru", pattern="^(lru|ttl)$")
    tenant_ttl_seconds: int = Field(default=3600, ge=1, le=31_536_000)

    # Vector DB
    vector_db_url: Optional[str] = None
    vector_db_api_key: Optional[str] = None

    # Observability
    otel_exporter_otlp_endpoint: Optional[str] = None

    model_config = ConfigDict(env_file=(".env", "backend/.env"), case_sensitive=False)

    @model_validator(mode="after")
    def validate_secrets(self):
        weak_values = {
            "change-me-in-production",
            "dev-secret-key-change-in-production",
            "",
            "MISSING_GEMINI_API_KEY",
        }
        if self.secret_key in weak_values:
            raise ValueError(
                "SECRET_KEY must be explicitly configured for authentication"
            )
        if self.secret_key in weak_values or self.gemini_api_key in weak_values:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Application initialized with a missing or default optional secret"
            )
        return self


settings = Settings()
