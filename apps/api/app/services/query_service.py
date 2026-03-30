from __future__ import annotations

import logging
import math

import polars as pl

from app.core.config import Settings, get_settings
from app.schemas.outage import (
    DataQueryParams,
    FacilityOutageItem,
    GeneratorOutageItem,
    PaginatedDataResponse,
)

"""
Query service for the Nuclear Outages model.

Responsibilities:
- read modeled parquet tables
- build generator and facility views
- apply filters, sorting, and pagination
- return typed response objects for the /data endpoint
"""

logger = logging.getLogger(__name__)


class QueryServiceError(Exception):
    """Base error for query service."""


class QueryValidationError(QueryServiceError):
    """Raised when query parameters are invalid for the selected view."""


class QueryService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _load_model_tables(self) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        facilities_path = self.settings.facilities_parquet_path
        generators_path = self.settings.generators_parquet_path
        outages_path = self.settings.outages_parquet_path

        for path in (facilities_path, generators_path, outages_path):
            if not path.exists():
                raise QueryServiceError(f"Model parquet does not exist: {path}")

        logger.info(
            "Loading model parquet files. facilities=%s, generators=%s, outages=%s",
            facilities_path,
            generators_path,
            outages_path,
        )

        facilities_df = pl.read_parquet(facilities_path)
        generators_df = pl.read_parquet(generators_path)
        outages_df = pl.read_parquet(outages_path)

        return facilities_df, generators_df, outages_df

    def _build_generator_view(
        self,
        facilities_df: pl.DataFrame,
        generators_df: pl.DataFrame,
        outages_df: pl.DataFrame,
    ) -> pl.DataFrame:
        return (
            outages_df
            .join(generators_df, on="generator_id", how="inner")
            .join(facilities_df, on="facility_id", how="inner")
            .select(
                [
                    "period_date",
                    "generator_id",
                    "generator_code",
                    "facility_id",
                    "facility_name",
                    "capacity_mw",
                    "outage_mw",
                    "percent_outage",
                ]
            )
        )

    def _build_facility_view(
        self,
        facilities_df: pl.DataFrame,
        generators_df: pl.DataFrame,
        outages_df: pl.DataFrame,
    ) -> pl.DataFrame:
        return (
            outages_df
            .join(generators_df, on="generator_id", how="inner")
            .join(facilities_df, on="facility_id", how="inner")
            .group_by(["period_date", "facility_id", "facility_name"])
            .agg(
                [
                    pl.col("capacity_mw").sum().alias("total_capacity_mw"),
                    pl.col("outage_mw").sum().alias("total_outage_mw"),
                ]
            )
            .with_columns(
                pl.when(pl.col("total_capacity_mw") == 0)
                .then(0.0)
                .otherwise(
                    (pl.col("total_outage_mw") / pl.col("total_capacity_mw")) * 100
                )
                .alias("percent_outage")
            )
            .select(
                [
                    "period_date",
                    "facility_id",
                    "facility_name",
                    "total_capacity_mw",
                    "total_outage_mw",
                    "percent_outage",
                ]
            )
        )

    def _apply_filters(self, df: pl.DataFrame, params: DataQueryParams) -> pl.DataFrame:
        if params.date is not None:
            df = df.filter(pl.col("period_date") == params.date)

        if params.search:
            search_value = params.search.lower()

            searchable_columns = [
                column
                for column in ("facility_name", "facility_id", "generator_id", "generator_code")
                if column in df.columns
            ]

            if searchable_columns:
                search_condition = None

                for column in searchable_columns:
                    expr = (
                        pl.col(column)
                        .cast(pl.Utf8)
                        .str.to_lowercase()
                        .str.contains(search_value, literal=True)
                    )
                    search_condition = expr if search_condition is None else (search_condition | expr)

                df = df.filter(search_condition)

        return df

    def _apply_sorting(self, df: pl.DataFrame, params: DataQueryParams) -> pl.DataFrame:
        allowed_sort_columns = {
            "generator": {
                "period_date",
                "generator_id",
                "generator_code",
                "facility_id",
                "facility_name",
                "capacity_mw",
                "outage_mw",
                "percent_outage",
            },
            "facility": {
                "period_date",
                "facility_id",
                "facility_name",
                "total_capacity_mw",
                "total_outage_mw",
                "percent_outage",
            },
        }

        default_sort_by = "period_date"
        sort_by = params.sort_by or default_sort_by

        if sort_by not in allowed_sort_columns[params.view]:
            raise QueryValidationError(
                f"Invalid sort_by='{sort_by}' for view='{params.view}'"
            )

        descending = params.sort_order == "desc"

        # Secondary ordering keeps results stable when multiple rows share the same sort value.
        secondary_columns = {
            "generator": ["facility_name", "generator_id"],
            "facility": ["facility_name"],
        }

        sort_columns = [sort_by] + [
            column for column in secondary_columns[params.view] if column != sort_by
        ]
        descending_flags = [descending] + [False] * (len(sort_columns) - 1)

        return df.sort(sort_columns, descending=descending_flags)

    def _apply_pagination(
        self,
        df: pl.DataFrame,
        params: DataQueryParams,
    ) -> tuple[pl.DataFrame, int, int]:
        total_items = df.height
        total_pages = max(1, math.ceil(total_items / params.page_size))

        offset = (params.page - 1) * params.page_size
        paginated_df = df.slice(offset, params.page_size)

        return paginated_df, total_items, total_pages

    def query_data(self, params: DataQueryParams) -> PaginatedDataResponse:
        logger.info(
            "Running data query. view=%s, date=%s, search=%s, page=%s, page_size=%s, sort_by=%s, sort_order=%s",
            params.view,
            params.date,
            params.search,
            params.page,
            params.page_size,
            params.sort_by,
            params.sort_order,
        )

        facilities_df, generators_df, outages_df = self._load_model_tables()

        if params.view == "generator":
            df = self._build_generator_view(
                facilities_df=facilities_df,
                generators_df=generators_df,
                outages_df=outages_df,
            )
            item_model = GeneratorOutageItem
        else:
            df = self._build_facility_view(
                facilities_df=facilities_df,
                generators_df=generators_df,
                outages_df=outages_df,
            )
            item_model = FacilityOutageItem

        df = self._apply_filters(df, params)
        df = self._apply_sorting(df, params)
        df, total_items, total_pages = self._apply_pagination(df, params)

        items = [
            item_model.model_validate(row)
            for row in df.to_dicts()
        ]

        response = PaginatedDataResponse(
            view=params.view,
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

        logger.info(
            "Query finished successfully. returned_items=%s, total_items=%s, total_pages=%s",
            len(items),
            total_items,
            total_pages,
        )

        return response