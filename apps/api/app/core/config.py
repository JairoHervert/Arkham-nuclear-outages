from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

"""
Settings for the aplication (backend) service.

This module centralizes:
- environment-based configuration
- local project paths
- EIA connector settings
- log and state management settings

It does not contain extraction data
"""


BASE_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    # Load settings from the project-level .env file and ignore unrelated
    # environment variables that may exist in the local machine.
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Arkham Nuclear Outages API"
    log_level: str = "INFO"

    # EIA
    # The API key is stored as SecretStr to avoid exposing it accidentally in logs
    eia_api_key: SecretStr
    eia_base_url: str = "https://api.eia.gov/v2"
    eia_endpoint: str

    # Request behavior
    request_timeout_seconds: float = 30.0
    page_size: int = 5000
    max_retries: int = 3
    retry_backoff_seconds: float = 1.5

    # Paths
    data_dir: Path = BASE_DIR / "data"
    raw_dir: Path = BASE_DIR / "data" / "raw"
    model_dir: Path = BASE_DIR / "data" / "model"

    # State management directory and files
    state_dir: Path = BASE_DIR / "data" / "state"
    extract_state_file: str = "extract_state.json"

    # logging settings
    logs_dir: Path = BASE_DIR / "logs"
    log_retention_days: int = 14

    # Parquet files
    raw_parquet: str = "nuclear_outages_raw.parquet"
    facilities_parquet: str = "facilities.parquet"
    generators_parquet: str = "generators.parquet"
    outages_parquet: str = "outages.parquet"

    @field_validator("eia_base_url")
    @classmethod
    def validate_eia_base_url(cls, value: str) -> str:
        # Normalize the base URL so the final composed endpoint does not contain accidental double slashes.
        return value.rstrip("/")

    @field_validator("eia_endpoint")
    @classmethod
    def validate_eia_endpoint(cls, value: str) -> str:
        # Ensure the endpoint is non-empty and always starts with "/"
        value = value.strip()
        if not value:
            raise ValueError("eia_endpoint cannot be empty")
        if not value.startswith("/"):
            value = f"/{value}"
        return value

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("page_size must be greater than 0")
        return value

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, value: int) -> int:
        if value < 0:
            raise ValueError("max_retries cannot be negative")
        return value

    @property
    def eia_url(self) -> str:
        return f"{self.eia_base_url}{self.eia_endpoint}"

    @property
    def raw_parquet_path(self) -> Path:
        return self.raw_dir / self.raw_parquet

    @property
    def facilities_parquet_path(self) -> Path:
        return self.model_dir / self.facilities_parquet

    @property
    def generators_parquet_path(self) -> Path:
        return self.model_dir / self.generators_parquet

    @property
    def outages_parquet_path(self) -> Path:
        return self.model_dir / self.outages_parquet

    @property
    def extract_state_path(self) -> Path:
        return self.state_dir / self.extract_state_file

    def create_directories(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.create_directories()
    return settings