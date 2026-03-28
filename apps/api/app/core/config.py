from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
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
    eia_api_key: SecretStr
    eia_base_url: str = "https://api.eia.gov/v2"
    eia_endpoint: str

    request_timeout_seconds: float = 30.0
    page_size: int = 5000
    max_retries: int = 3
    retry_backoff_seconds: float = 1.5

    # Paths
    data_dir: Path = BASE_DIR / "data"
    raw_dir: Path = BASE_DIR / "data" / "raw"
    model_dir: Path = BASE_DIR / "data" / "model"

    # Parquet files
    raw_parquet: str = "nuclear_outages_raw.parquet"
    plants_parquet: str = "plants.parquet"
    generators_parquet: str = "generators.parquet"
    outages_parquet: str = "outages.parquet"

    @field_validator("eia_base_url")
    @classmethod
    def validate_eia_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("eia_endpoint")
    @classmethod
    def validate_eia_endpoint(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("eia_endpoint no puede estar vacío")
        if not value.startswith("/"):
            value = f"/{value}"
        return value

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("page_size debe ser mayor que 0")
        return value

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, value: int) -> int:
        if value < 0:
            raise ValueError("max_retries no puede ser negativo")
        return value

    @property
    def eia_url(self) -> str:
        return f"{self.eia_base_url}{self.eia_endpoint}"

    @property
    def raw_parquet_path(self) -> Path:
        return self.raw_dir / self.raw_parquet

    @property
    def plants_parquet_path(self) -> Path:
        return self.model_dir / self.plants_parquet

    @property
    def generators_parquet_path(self) -> Path:
        return self.model_dir / self.generators_parquet

    @property
    def outages_parquet_path(self) -> Path:
        return self.model_dir / self.outages_parquet

    def create_directories(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.create_directories()
    return settings