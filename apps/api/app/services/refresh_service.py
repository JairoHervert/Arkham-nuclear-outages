from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.schemas.refresh import (
    ExtractSummary,
    RefreshRequest,
    RefreshResponse,
    TransformSummary,
)
from app.services.extract_service import (
    EIAAuthError,
    EIAClientError,
    ExtractService,
)
from app.services.transform_service import (
    TransformService,
    TransformServiceError,
)

"""
Refresh service for the Nuclear Outages pipeline.

Responsibilities:
- orchestrate extract + transform as a single refresh operation
- support either automatic extraction mode selection or forced full extraction
- return a single response object with both extract and transform summaries
"""

logger = logging.getLogger(__name__)


class RefreshServiceError(Exception):
    """Base error for refresh service."""


class RefreshService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.extract_service = ExtractService(settings=self.settings)
        self.transform_service = TransformService(settings=self.settings)

    def run_refresh(self, request: RefreshRequest) -> RefreshResponse:
        logger.info("Starting refresh pipeline. requested_mode=%s", request.mode)

        try:
            # 1. Run extraction
            if request.mode == "full":
                extract_result = self.extract_service.run_full_extract()
            else:
                extract_result = self.extract_service.run_extract()

            logger.info(
                "Extraction finished successfully. mode=%s, valid_rows=%s, invalid_rows=%s, pages_processed=%s, pages_failed=%s",
                extract_result.mode,
                extract_result.total_rows_valid,
                extract_result.total_rows_invalid,
                extract_result.pages_processed,
                extract_result.pages_failed,
            )

            # 2. Run transformation using the refreshed raw parquet
            transform_result = self.transform_service.run_transform()

            logger.info(
                "Transformation finished successfully. raw_rows=%s, facilities_rows=%s, generators_rows=%s, outages_rows=%s",
                transform_result.raw_rows,
                transform_result.facilities_rows,
                transform_result.generators_rows,
                transform_result.outages_rows,
            )

            # 3. Build unified response
            response = RefreshResponse(
                status="success",
                requested_mode=request.mode,
                extract=ExtractSummary(
                    mode=extract_result.mode,
                    total_rows_reported=extract_result.total_rows_reported,
                    total_rows_valid=extract_result.total_rows_valid,
                    total_rows_invalid=extract_result.total_rows_invalid,
                    pages_processed=extract_result.pages_processed,
                    pages_failed=extract_result.pages_failed,
                    raw_parquet_path=str(extract_result.raw_parquet_path),
                    state_path=str(extract_result.state_path),
                    last_successful_period=extract_result.last_successful_period,
                    full_extract_completed=extract_result.full_extract_completed,
                    next_offset=extract_result.next_offset,
                ),
                transform=TransformSummary(
                    raw_rows=transform_result.raw_rows,
                    facilities_rows=transform_result.facilities_rows,
                    generators_rows=transform_result.generators_rows,
                    outages_rows=transform_result.outages_rows,
                    facilities_parquet_path=str(transform_result.facilities_parquet_path),
                    generators_parquet_path=str(transform_result.generators_parquet_path),
                    outages_parquet_path=str(transform_result.outages_parquet_path),
                ),
            )

            logger.info("Refresh pipeline completed successfully.")
            return response

        except (EIAAuthError, EIAClientError, TransformServiceError) as exc:
            logger.exception("Refresh pipeline failed: %s", exc)
            raise RefreshServiceError(str(exc)) from exc

        except Exception as exc:
            logger.exception("Unexpected error during refresh pipeline: %s", exc)
            raise RefreshServiceError(
                "Unexpected error while running refresh pipeline."
            ) from exc