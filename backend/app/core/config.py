from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
        secrets_dir="/run/secrets" if Path("/run/secrets").is_dir() else None,
    )

    app_env: Literal["development", "test", "production"] = "development"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "politica"
    db_user: str = "politica"
    db_password: SecretStr  # Sem senha implícita; fornecida pelo ambiente.
    frontend_url: str = "http://localhost:3000"
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "test", "testserver"]
    rate_limit_per_minute: int = Field(default=60, ge=1, le=6000)
    rate_limit_burst: int = Field(default=20, ge=1, le=1000)
    rate_limit_max_clients: int = Field(default=10000, ge=1, le=100000)
    export_limit_per_minute: int = Field(default=6, ge=1, le=60)
    export_limit_burst: int = Field(default=2, ge=1, le=10)
    db_statement_timeout_ms: int = Field(default=15000, ge=100, le=120000)
    analytics_enabled: bool = False
    analytics_admin_token: SecretStr | None = None
    content_admin_token: SecretStr | None = None
    citizen_explanation_provider: Literal["disabled", "openai"] = "disabled"
    openai_api_key: SecretStr | None = None
    openai_citizen_generation_model: str | None = None
    openai_citizen_verification_model: str | None = None
    citizen_explanation_interval_minutes: int = Field(default=30, ge=1)
    citizen_explanation_batch_size: int = Field(default=10, ge=1, le=100)
    analytics_retention_days: int = Field(default=90, ge=1, le=366)
    scheduler_enabled: bool = True
    scheduler_run_on_startup: bool = True
    deputies_import_interval_minutes: int = Field(default=1440, ge=1)
    deputy_profiles_import_enabled: bool = True
    deputy_profiles_import_interval_minutes: int = Field(default=43200, ge=1)
    senators_import_interval_minutes: int = Field(default=1440, ge=1)
    senate_legislation_import_interval_minutes: int = Field(default=360, ge=1)
    legislation_import_interval_minutes: int = Field(default=60, ge=1)
    camara_expenses_import_enabled: bool = False
    camara_expenses_import_interval_minutes: int = Field(default=1440, ge=1)
    camara_expenses_year: int = 2026
    camara_remuneration_import_enabled: bool = False
    camara_remuneration_import_interval_minutes: int = Field(default=43200, ge=1)
    camara_staff_import_enabled: bool = False
    camara_staff_import_interval_minutes: int = Field(default=43200, ge=1)
    portal_transparencia_api_token: SecretStr | None = None
    portal_amendments_import_enabled: bool = False
    portal_amendments_import_interval_minutes: int = Field(default=1440, ge=1)
    portal_amendments_year: int = 2026
    portal_amendments_request_interval_seconds: float = Field(
        default=0.25, ge=0, allow_inf_nan=False
    )
    camara_votes_import_enabled: bool = False
    camara_votes_import_interval_minutes: int = Field(default=10080, ge=1)
    camara_votes_year: int = 2026
    election_results_import_enabled: bool = False
    election_results_year: int = 2022
    election_results_import_interval_minutes: int = Field(default=525600, ge=1)

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        origin = urlsplit(self.frontend_url)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.username is not None
            or origin.password is not None
            or origin.path not in {"", "/"}
            or origin.query
            or origin.fragment
        ):
            raise ValueError("FRONTEND_URL must be an HTTP(S) origin")
        self.frontend_url = self.frontend_url.rstrip("/")
        if not self.allowed_hosts or any(
            not host
            or "*" in host
            or "/" in host
            or ":" in host
            or any(char.isspace() for char in host)
            for host in self.allowed_hosts
        ):
            raise ValueError("ALLOWED_HOSTS requires explicit hostnames without ports or wildcards")
        if self.app_env == "production":
            if origin.scheme != "https":
                raise ValueError("Production requires an HTTPS FRONTEND_URL")
            if len(self.db_password.get_secret_value()) < 24:
                raise ValueError("Production requires a DB_PASSWORD of at least 24 characters")
            if not set(self.allowed_hosts) - {"localhost", "127.0.0.1", "test", "testserver"}:
                raise ValueError("Production requires explicit ALLOWED_HOSTS")
            if self.content_admin_token and len(self.content_admin_token.get_secret_value()) < 24:
                raise ValueError(
                    "Production requires CONTENT_ADMIN_TOKEN of at least 24 characters"
                )
            if self.analytics_admin_token and len(self.analytics_admin_token.get_secret_value()) < 24:
                raise ValueError("Production requires ANALYTICS_ADMIN_TOKEN of at least 24 characters")
            if self.citizen_explanation_provider == "openai" and (
                not self.openai_api_key
                or not self.openai_citizen_generation_model
                or not self.openai_citizen_verification_model
            ):
                raise ValueError(
                    "Autonomous citizen explanations require OPENAI_API_KEY, "
                    "OPENAI_CITIZEN_GENERATION_MODEL and OPENAI_CITIZEN_VERIFICATION_MODEL"
                )
        return self

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
