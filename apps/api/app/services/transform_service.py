from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from app.core.config import Settings, get_settings

"""
Transformation service for the Nuclear Outages dataset.

Responsibilities:
- read the persisted raw parquet produced by ExtractService
- validate the minimum required raw columns
- normalize the dataset into 3 model tables
- persist those model tables as parquet files

This service does not:
- call the external API
- run analytical queries
- serve HTTP responses

Its only goal is to convert the raw dataset into a simple relational model.
"""

logger = logging.getLogger(__name__)


# Minimum raw columns required to build the model tables
REQUIRED_RAW_FIELDS = (
    "period",
    "facility",
    "facilityName",
    "generator",
    "capacity",
    "outage",
    "percentOutage",
)

# Structured result of the transform process for logging and testing purposes
@dataclass
class TransformResult:
    raw_rows: int
    plants_rows: int
    generators_rows: int
    outages_rows: int
    facilities_parquet_path: Path
    generators_parquet_path: Path
    outages_parquet_path: Path

# General and especially validation errors during the transform process
class TransformServiceError(Exception):
    """Base error for transform service."""

class TransformValidationError(TransformServiceError):
    """Raised when raw data cannot be transformed safely."""


class TransformService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _load_raw_df(self) -> pl.DataFrame:
        raw_path = self.settings.raw_parquet_path

        if not raw_path.exists():
            raise TransformServiceError(
                f"Raw parquet does not exist: {raw_path}"
            )

        logger.info("Loading raw parquet from %s", raw_path)
        return pl.read_parquet(raw_path)

    def _validate_required_columns(self, df: pl.DataFrame) -> None:
        missing_fields = [
            field for field in REQUIRED_RAW_FIELDS if field not in df.columns
        ]

        if missing_fields:
            raise TransformValidationError(
                "Raw parquet is missing required columns: "
                f"{', '.join(missing_fields)}"
            )

    def _prepare_base_df(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Normalize column names and cast types required by the model (intermediate base_df).

        Output columns:
        - period_date
        - facility_id
        - facility_name
        - generator_code
        - generator_id
        - capacity_mw
        - outage_mw
        - percent_outage
        """
        try:
            base_df = (
                df.select(
                    [
                        pl.col("period").cast(pl.Utf8).str.strip_chars().alias("period_raw"),
                        pl.col("facility").cast(pl.Utf8).str.strip_chars().alias("facility_id"),
                        pl.col("facilityName").cast(pl.Utf8).str.strip_chars().alias("facility_name"),
                        pl.col("generator").cast(pl.Utf8).str.strip_chars().alias("generator_code"),
                        pl.col("capacity").cast(pl.Float64).alias("capacity_mw"),
                        pl.col("outage").cast(pl.Float64).alias("outage_mw"),
                        pl.col("percentOutage").cast(pl.Float64).alias("percent_outage"),
                    ]
                )
                .with_columns(
                    [
                        pl.col("period_raw")
                        .str.strptime(pl.Date, "%Y-%m-%d", strict=True)
                        .alias("period_date"),
                    ]
                )
                .with_columns(
                    [
                        (
                            pl.col("facility_id")
                            + pl.lit("_")
                            + pl.col("generator_code")
                        ).alias("generator_id"),
                    ]
                )
                .drop("period_raw")
            )
        except Exception as exc:
            raise TransformValidationError(
                "Failed to cast raw parquet columns into the model schema."
            ) from exc

        return base_df

    # After casting and basic transformations, we need to validate that there are no null values in required fields
    def _validate_required_values(self, df: pl.DataFrame) -> None:
        required_columns = [
            "period_date",
            "facility_id",
            "facility_name",
            "generator_code",
            "generator_id",
            "capacity_mw",
            "outage_mw",
            "percent_outage",
        ]

        null_counts = df.select(
            [pl.col(column).is_null().sum().alias(column) for column in required_columns]
        ).to_dicts()[0]

        invalid_columns = {
            column: count
            for column, count in null_counts.items()
            if count > 0
        }

        if invalid_columns:
            raise TransformValidationError(
                "Transformed base data contains null/invalid values after casting: "
                f"{invalid_columns}"
            )

    def _validate_model_consistency(self, df: pl.DataFrame) -> None:
        # A facility_id should map to a single facility_name
        duplicated_plants = (
            df.group_by("facility_id")
            .agg(pl.col("facility_name").n_unique().alias("facility_name_count"))
            .filter(pl.col("facility_name_count") > 1)
        )

        if duplicated_plants.height > 0:
            raise TransformValidationError(
                "Found facility_id values associated with multiple facility_name values."
            )

        # A generator_id should map to a single (facility_id, generator_code)
        duplicated_generators = (
            df.group_by("generator_id")
            .agg(
                [
                    pl.col("facility_id").n_unique().alias("facility_id_count"),
                    pl.col("generator_code").n_unique().alias("generator_code_count"),
                ]
            )
            .filter(
                (pl.col("facility_id_count") > 1)
                | (pl.col("generator_code_count") > 1)
            )
        )

        if duplicated_generators.height > 0:
            raise TransformValidationError(
                "Found generator_id values associated with inconsistent generator mappings."
            )

    def _build_plants_df(self, df: pl.DataFrame) -> pl.DataFrame:
        return (
            df.select(["facility_id", "facility_name"])
            .unique()
            .sort("facility_id")
        )

    def _build_generators_df(self, df: pl.DataFrame) -> pl.DataFrame:
        return (
            df.select(["generator_id", "facility_id", "generator_code"])
            .unique()
            .sort(["facility_id", "generator_code"])
        )

    def _build_outages_df(self, df: pl.DataFrame) -> pl.DataFrame:
        return (
            df.select(
                [
                    "period_date",
                    "generator_id",
                    "capacity_mw",
                    "outage_mw",
                    "percent_outage",
                ]
            )
            .unique(subset=["period_date", "generator_id"], keep="last")
            .sort(["period_date", "generator_id"])
        )

    def _write_model_tables(
        self,
        plants_df: pl.DataFrame,
        generators_df: pl.DataFrame,
        outages_df: pl.DataFrame,
    ) -> None:
        plants_path = self.settings.facilities_parquet_path
        generators_path = self.settings.generators_parquet_path
        outages_path = self.settings.outages_parquet_path

        logger.info("Writing plants parquet to %s", plants_path)
        plants_df.write_parquet(plants_path)

        logger.info("Writing generators parquet to %s", generators_path)
        generators_df.write_parquet(generators_path)

        logger.info("Writing outages parquet to %s", outages_path)
        outages_df.write_parquet(outages_path)

    # Main method to run the full transform process
    def run_transform(self) -> TransformResult:
        logger.info("Starting model transformation from raw parquet.")

        raw_df = self._load_raw_df()
        self._validate_required_columns(raw_df)

        logger.info("Raw parquet loaded successfully. rows=%s", raw_df.height)

        base_df = self._prepare_base_df(raw_df)
        self._validate_required_values(base_df)
        self._validate_model_consistency(base_df)

        plants_df = self._build_plants_df(base_df)
        generators_df = self._build_generators_df(base_df)
        outages_df = self._build_outages_df(base_df)

        self._write_model_tables(
            plants_df=plants_df,
            generators_df=generators_df,
            outages_df=outages_df,
        )

        logger.info(
            "Transformation finished successfully. raw_rows=%s, plants_rows=%s, generators_rows=%s, outages_rows=%s",
            raw_df.height,
            plants_df.height,
            generators_df.height,
            outages_df.height,
        )

        return TransformResult(
            raw_rows=raw_df.height,
            plants_rows=plants_df.height,
            generators_rows=generators_df.height,
            outages_rows=outages_df.height,
            facilities_parquet_path=self.settings.facilities_parquet_path,
            generators_parquet_path=self.settings.generators_parquet_path,
            outages_parquet_path=self.settings.outages_parquet_path,
        )