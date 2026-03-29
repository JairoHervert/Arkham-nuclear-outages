from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

from app.connectors.eia_client import EIAAuthError, EIAClient, EIAClientError
from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


# Minimum fields required for a row to be considered valid for raw storage.
REQUIRED_RAW_FIELDS = (
    "period",
    "facility",
    "facilityName",
    "generator",
    "capacity",
    "outage",
    "percentOutage",
)

# Natural key used to deduplicate raw rows after merges.
RAW_DEDUP_KEYS = (
    "period",
    "facility",
    "generator",
)

DEFAULT_STATE = {
    "full_extract_completed": False,
    "next_offset": None,
    "last_successful_period": None,
    "last_run_at": None,
}


@dataclass
class ExtractResult:
    mode: str
    total_rows_reported: int
    total_rows_valid: int
    total_rows_invalid: int
    pages_processed: int
    pages_failed: int
    raw_parquet_path: Path
    state_path: Path
    last_successful_period: str | None
    full_extract_completed: bool
    next_offset: int | None


class ExtractService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _validate_row(self, row: dict[str, Any]) -> tuple[bool, list[str]]:
        missing_fields: list[str] = []

        for field in REQUIRED_RAW_FIELDS:
            value = row.get(field)

            if value is None:
                missing_fields.append(field)
                continue

            if isinstance(value, str) and not value.strip():
                missing_fields.append(field)

        return len(missing_fields) == 0, missing_fields

    # Validate a page of rows and keep only the valid ones.
    def _filter_valid_rows(
        self,
        rows: list[dict[str, Any]],
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        valid_rows: list[dict[str, Any]] = []
        invalid_count = 0

        for index, row in enumerate(rows):
            is_valid, missing_fields = self._validate_row(row)

            if not is_valid:
                invalid_count += 1
                logger.warning(
                    "Skipping invalid row at offset=%s, index=%s. Missing fields: %s",
                    offset,
                    index,
                    ", ".join(missing_fields),
                )
                continue

            valid_rows.append(row)

        return valid_rows, invalid_count

    def _rows_to_df(self, rows: list[dict[str, Any]]) -> pl.DataFrame:
        return pl.DataFrame(rows)

    # Overwrite raw parquet from scratch.
    def _write_full_raw(self, rows: list[dict[str, Any]]) -> Path:
        df = (
            self._rows_to_df(rows)
            .unique(subset=list(RAW_DEDUP_KEYS), keep="last")
            .sort(
                by=["period", "facility", "generator"],
                descending=[True, False, False],
            )
        )

        df.write_parquet(self.settings.raw_parquet_path)
        return self.settings.raw_parquet_path

    # Merge newly extracted rows into the existing raw parquet.
    def _merge_and_write_raw(self, rows: list[dict[str, Any]]) -> Path:
        new_df = self._rows_to_df(rows)

        if self.settings.raw_parquet_path.exists():
            existing_df = pl.read_parquet(self.settings.raw_parquet_path)

            merged_df = (
                pl.concat([existing_df, new_df], how="vertical_relaxed")
                .unique(subset=list(RAW_DEDUP_KEYS), keep="last")
                .sort(
                    by=["period", "facility", "generator"],
                    descending=[True, False, False],
                )
            )
        else:
            merged_df = (
                new_df
                .unique(subset=list(RAW_DEDUP_KEYS), keep="last")
                .sort(
                    by=["period", "facility", "generator"],
                    descending=[True, False, False],
                )
            )

        merged_df.write_parquet(self.settings.raw_parquet_path)
        return self.settings.raw_parquet_path

    def _load_state(self) -> dict[str, Any]:
        state_path = self.settings.extract_state_path

        if not state_path.exists():
            return DEFAULT_STATE.copy()

        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                logger.warning(
                    "State file is not a JSON object. Default state will be used: %s",
                    state_path,
                )
                return DEFAULT_STATE.copy()

            return {**DEFAULT_STATE, **payload}

        except json.JSONDecodeError:
            logger.warning(
                "State file exists but does not contain valid JSON. Default state will be used: %s",
                state_path,
            )
            return DEFAULT_STATE.copy()

    def _save_state(
        self,
        *,
        full_extract_completed: bool,
        next_offset: int | None,
        last_successful_period: str | None,
    ) -> Path:
        state_payload = {
            "full_extract_completed": full_extract_completed,
            "next_offset": next_offset,
            "last_successful_period": last_successful_period,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }

        self.settings.extract_state_path.write_text(
            json.dumps(state_payload, indent=2),
            encoding="utf-8",
        )
        return self.settings.extract_state_path

    def _get_latest_period_from_rows(self, rows: list[dict[str, Any]]) -> str | None:
        if not rows:
            return None

        periods = [row["period"] for row in rows if row.get("period")]
        return max(periods) if periods else None

    def _get_latest_period_from_raw(self) -> str | None:
        if not self.settings.raw_parquet_path.exists():
            return None

        df = pl.read_parquet(self.settings.raw_parquet_path)

        if "period" not in df.columns or df.height == 0:
            return None

        return df.select(pl.col("period").max()).item()

    # Save partial progress for a full extraction.
    # If the extraction started from offset 0, the partial raw should replace any current raw.
    # If the extraction is resuming from a later offset, partial rows should be merged into the existing raw.
    def _persist_full_progress(
        self,
        *,
        extracted_rows: list[dict[str, Any]],
        start_offset: int,
        next_offset: int,
    ) -> tuple[Path, Path, str | None]:
        if extracted_rows:
            if start_offset == 0:
                raw_parquet_path = self._write_full_raw(extracted_rows)
            else:
                raw_parquet_path = self._merge_and_write_raw(extracted_rows)
        else:
            raw_parquet_path = self.settings.raw_parquet_path

        last_successful_period = self._get_latest_period_from_raw()

        state_path = self._save_state(
            full_extract_completed=False,
            next_offset=next_offset,
            last_successful_period=last_successful_period,
        )

        return raw_parquet_path, state_path, last_successful_period

    # Save partial progress for an incremental extraction.
    # Incremental progress is always merged into the current raw parquet.
    def _persist_incremental_progress(
        self,
        *,
        extracted_rows: list[dict[str, Any]],
        fallback_period: str,
    ) -> tuple[Path, Path, str | None]:
        if extracted_rows:
            raw_parquet_path = self._merge_and_write_raw(extracted_rows)
        else:
            raw_parquet_path = self.settings.raw_parquet_path

        last_successful_period = self._get_latest_period_from_raw() or fallback_period

        state_path = self._save_state(
            full_extract_completed=True,
            next_offset=None,
            last_successful_period=last_successful_period,
        )

        return raw_parquet_path, state_path, last_successful_period

    # Internal full extraction that can optionally resume from a saved offset.
    def _run_full_extract(self, start_offset: int = 0) -> ExtractResult:
        logger.info("Starting full extraction from EIA. start_offset=%s", start_offset)

        total_valid_rows = 0
        total_invalid_rows = 0
        pages_processed = 0
        pages_failed = 0
        extracted_rows: list[dict[str, Any]] = []

        with EIAClient(settings=self.settings) as client:
            total_rows_reported = client.get_total_rows()
            page_size = self.settings.page_size

            logger.info(
                "EIA reported %s total rows. Page size=%s",
                total_rows_reported,
                page_size,
            )

            # If the saved offset is already at or past the end, mark the full extract as complete.
            if start_offset >= total_rows_reported:
                raw_parquet_path = self.settings.raw_parquet_path
                last_successful_period = self._get_latest_period_from_raw()
                state_path = self._save_state(
                    full_extract_completed=True,
                    next_offset=None,
                    last_successful_period=last_successful_period,
                )

                logger.info(
                    "No remaining pages for full extraction. The full extract is now marked as complete."
                )

                return ExtractResult(
                    mode="full",
                    total_rows_reported=total_rows_reported,
                    total_rows_valid=0,
                    total_rows_invalid=0,
                    pages_processed=0,
                    pages_failed=0,
                    raw_parquet_path=raw_parquet_path,
                    state_path=state_path,
                    last_successful_period=last_successful_period,
                    full_extract_completed=True,
                    next_offset=None,
                )

            for offset in range(start_offset, total_rows_reported, page_size):
                try:
                    rows = client.get_rows(offset=offset, length=page_size)
                    pages_processed += 1

                    valid_rows, invalid_count = self._filter_valid_rows(rows, offset=offset)

                    extracted_rows.extend(valid_rows)
                    total_valid_rows += len(valid_rows)
                    total_invalid_rows += invalid_count

                    logger.info(
                        "Processed page successfully. offset=%s, received=%s, valid=%s, invalid=%s",
                        offset,
                        len(rows),
                        len(valid_rows),
                        invalid_count,
                    )

                except EIAAuthError:
                    logger.error(
                        "Full extraction aborted because of authentication failure. Retrying the same page will not help."
                    )
                    raise

                except EIAClientError as exc:
                    pages_failed += 1

                    logger.error(
                        "Full extraction failed at offset=%s after exhausting retries. Error: %s",
                        offset,
                        exc,
                    )

                    raw_parquet_path, state_path, last_successful_period = self._persist_full_progress(
                        extracted_rows=extracted_rows,
                        start_offset=start_offset,
                        next_offset=offset,
                    )

                    logger.warning(
                        "Partial full-extraction progress saved. raw=%s, next_offset=%s, last_successful_period=%s",
                        raw_parquet_path,
                        offset,
                        last_successful_period,
                    )

                    raise EIAClientError(
                        "Full extraction aborted after a page failed and retries were exhausted. "
                        "Partial progress was saved and the next run can resume from the saved offset."
                    ) from exc

        if start_offset == 0 and not extracted_rows:
            logger.error("Full extraction finished without any valid rows.")
            raise EIAClientError("Full extraction finished without any valid rows to store.")

        if start_offset == 0:
            raw_parquet_path = self._write_full_raw(extracted_rows)
        elif extracted_rows:
            raw_parquet_path = self._merge_and_write_raw(extracted_rows)
        else:
            raw_parquet_path = self.settings.raw_parquet_path

        last_successful_period = self._get_latest_period_from_raw()
        state_path = self._save_state(
            full_extract_completed=True,
            next_offset=None,
            last_successful_period=last_successful_period,
        )

        logger.info(
            "Full extraction completed. reported=%s, valid=%s, invalid=%s, pages_ok=%s, pages_failed=%s, raw=%s, last_period=%s",
            total_rows_reported,
            total_valid_rows,
            total_invalid_rows,
            pages_processed,
            pages_failed,
            raw_parquet_path,
            last_successful_period,
        )

        return ExtractResult(
            mode="full",
            total_rows_reported=total_rows_reported,
            total_rows_valid=total_valid_rows,
            total_rows_invalid=total_invalid_rows,
            pages_processed=pages_processed,
            pages_failed=pages_failed,
            raw_parquet_path=raw_parquet_path,
            state_path=state_path,
            last_successful_period=last_successful_period,
            full_extract_completed=True,
            next_offset=None,
        )

    # Public method for a forced full extract from scratch.
    def run_full_extract(self) -> ExtractResult:
        return self._run_full_extract(start_offset=0)

    # Public method for an incremental refresh based on the last saved successful period.
    def run_incremental_extract(self) -> ExtractResult:
        logger.info("Starting incremental extraction from EIA.")

        state = self._load_state()
        cutoff_period = state.get("last_successful_period") or self._get_latest_period_from_raw()

        if not cutoff_period:
            logger.info(
                "No previous successful period is available. Falling back to full extraction."
            )
            return self.run_full_extract()

        if not self.settings.raw_parquet_path.exists():
            logger.info(
                "Raw parquet does not exist. Falling back to full extraction."
            )
            return self.run_full_extract()

        total_valid_rows = 0
        total_invalid_rows = 0
        pages_processed = 0
        pages_failed = 0
        extracted_rows: list[dict[str, Any]] = []

        logger.info(
            "Incremental extraction will use overlap from period=%s",
            cutoff_period,
        )

        with EIAClient(settings=self.settings) as client:
            total_rows_reported = client.get_total_rows()
            page_size = self.settings.page_size

            for offset in range(0, total_rows_reported, page_size):
                try:
                    rows = client.get_rows(offset=offset, length=page_size)
                    pages_processed += 1

                    valid_rows, invalid_count = self._filter_valid_rows(rows, offset=offset)
                    total_invalid_rows += invalid_count

                    if not valid_rows:
                        logger.info(
                            "Page offset=%s returned no valid rows. Continuing to the next page.",
                            offset,
                        )
                        continue

                    # Since the API is sorted by period descending, once a page is fully older
                    # than the cutoff period there is no reason to keep scanning more pages.
                    page_periods = [row["period"] for row in valid_rows]
                    page_newest_period = max(page_periods)

                    if page_newest_period < cutoff_period:
                        logger.info(
                            "Reached a page older than the incremental cutoff (%s). Stopping scan.",
                            cutoff_period,
                        )
                        break

                    overlap_rows = [
                        row
                        for row in valid_rows
                        if row["period"] >= cutoff_period
                    ]

                    extracted_rows.extend(overlap_rows)
                    total_valid_rows += len(overlap_rows)

                    logger.info(
                        "Processed incremental page. offset=%s, valid_in_page=%s, selected_for_merge=%s, invalid=%s",
                        offset,
                        len(valid_rows),
                        len(overlap_rows),
                        invalid_count,
                    )

                except EIAAuthError:
                    logger.error(
                        "Incremental extraction aborted because of authentication failure."
                    )
                    raise

                except EIAClientError as exc:
                    pages_failed += 1

                    logger.error(
                        "Incremental extraction failed at offset=%s after exhausting retries. Error: %s",
                        offset,
                        exc,
                    )

                    raw_parquet_path, state_path, last_successful_period = self._persist_incremental_progress(
                        extracted_rows=extracted_rows,
                        fallback_period=cutoff_period,
                    )

                    logger.warning(
                        "Partial incremental progress saved. raw=%s, last_successful_period=%s",
                        raw_parquet_path,
                        last_successful_period,
                    )

                    raise EIAClientError(
                        "Incremental extraction aborted after a page failed and retries were exhausted. "
                        "Partial progress was saved and the next run can resume from the saved period."
                    ) from exc

        if extracted_rows:
            raw_parquet_path = self._merge_and_write_raw(extracted_rows)
            last_successful_period = self._get_latest_period_from_raw() or cutoff_period
        else:
            raw_parquet_path = self.settings.raw_parquet_path
            last_successful_period = cutoff_period

        state_path = self._save_state(
            full_extract_completed=True,
            next_offset=None,
            last_successful_period=last_successful_period,
        )

        logger.info(
            "Incremental extraction completed. reported=%s, selected=%s, invalid=%s, pages_ok=%s, pages_failed=%s, raw=%s, last_period=%s",
            total_rows_reported,
            total_valid_rows,
            total_invalid_rows,
            pages_processed,
            pages_failed,
            raw_parquet_path,
            last_successful_period,
        )

        return ExtractResult(
            mode="incremental",
            total_rows_reported=total_rows_reported,
            total_rows_valid=total_valid_rows,
            total_rows_invalid=total_invalid_rows,
            pages_processed=pages_processed,
            pages_failed=pages_failed,
            raw_parquet_path=raw_parquet_path,
            state_path=state_path,
            last_successful_period=last_successful_period,
            full_extract_completed=True,
            next_offset=None,
        )

    # Single entry point:
    # - no state/raw -> full from offset 0
    # - incomplete full -> resume full from saved offset
    # - completed full -> incremental refresh by period
    def run_extract(self) -> ExtractResult:
        state = self._load_state()
        raw_exists = self.settings.raw_parquet_path.exists()

        full_extract_completed = bool(state.get("full_extract_completed"))
        next_offset = state.get("next_offset")
        last_successful_period = state.get("last_successful_period")

        if not raw_exists and next_offset not in (None, 0):
            logger.warning(
                "State indicates a resumable full extraction at offset=%s, but raw parquet does not exist. "
                "A fresh full extraction will start from offset 0.",
                next_offset,
            )
            return self._run_full_extract(start_offset=0)

        if not raw_exists and not full_extract_completed:
            logger.info(
                "No raw parquet or completed state found. Starting full extraction from offset 0."
            )
            return self._run_full_extract(start_offset=0)

        if not full_extract_completed:
            resume_offset = next_offset or 0
            logger.info(
                "Resuming incomplete full extraction from offset=%s",
                resume_offset,
            )
            return self._run_full_extract(start_offset=resume_offset)

        if not last_successful_period:
            logger.info(
                "Full extraction is marked as complete but no last_successful_period is available. "
                "Falling back to incremental resolution logic."
            )

        return self.run_incremental_extract()