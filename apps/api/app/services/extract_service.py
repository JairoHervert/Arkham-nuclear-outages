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

# Min fields required for a row to be considered valid for raw storage
REQUIRED_RAW_FIELDS = (
    "period",
    "facility",
    "facilityName",
    "generator",
    "capacity",
    "outage",
    "percentOutage",
)

# Fields used to determine duplicates when merging incremental extracts into raw parquet
RAW_DEDUP_KEYS = (
    "period",
    "facility",
    "generator",
)


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

    # use _validate_row to filter out invalid rows and log warnings for them
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
                    "Registro inválido omitido en offset=%s, index=%s. Campos faltantes: %s",
                    offset,
                    index,
                    ", ".join(missing_fields),
                )
                continue

            valid_rows.append(row)

        return valid_rows, invalid_count

    def _rows_to_df(self, rows: list[dict[str, Any]]) -> pl.DataFrame:
        return pl.DataFrame(rows)

    # Merge new rows with existing raw parquet, deduplicating by RAW_DEDUP_KEYS and keeping the latest record based on 'period'
    def _merge_and_write_raw(self, rows: list[dict[str, Any]]) -> Path:
        new_df = self._rows_to_df(rows)

        if self.settings.raw_parquet_path.exists():
            existing_df = pl.read_parquet(self.settings.raw_parquet_path)

            merged_df = (
                pl.concat([existing_df, new_df], how="vertical_relaxed")
                .unique(subset=list(RAW_DEDUP_KEYS), keep="last")
                .sort(by=["period", "facility", "generator"], descending=[True, False, False])
            )
        else:
            merged_df = (
                new_df
                .unique(subset=list(RAW_DEDUP_KEYS), keep="last")
                .sort(by=["period", "facility", "generator"], descending=[True, False, False])
            )

        merged_df.write_parquet(self.settings.raw_parquet_path)
        return self.settings.raw_parquet_path

    def _write_full_raw(self, rows: list[dict[str, Any]]) -> Path:
        df = (
            self._rows_to_df(rows)
            .unique(subset=list(RAW_DEDUP_KEYS), keep="last")
            .sort(by=["period", "facility", "generator"], descending=[True, False, False])
        )
        df.write_parquet(self.settings.raw_parquet_path)
        return self.settings.raw_parquet_path

    # Load the last successful period extracted
    def _load_state(self) -> dict[str, Any]:
        state_path = self.settings.extract_state_path

        if not state_path.exists():
            return {}

        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(
                "El archivo de estado existe pero no contiene JSON válido. Se ignorará: %s",
                state_path,
            )
            return {}

    def _save_state(self, last_successful_period: str | None) -> Path:
        state_payload = {
            "last_successful_period": last_successful_period,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }

        self.settings.extract_state_path.write_text(
            json.dumps(state_payload, indent=2),
            encoding="utf-8",
        )
        return self.settings.extract_state_path

    # Get the latest period from a extracted page of rows
    def _get_latest_period_from_rows(self, rows: list[dict[str, Any]]) -> str | None:
        if not rows:
            return None

        periods = [row["period"] for row in rows if row.get("period")]
        return max(periods) if periods else None

    # Get the latest period from the existing raw parquet
    def _get_latest_period_from_raw(self) -> str | None:
        if not self.settings.raw_parquet_path.exists():
            return None

        df = pl.read_parquet(self.settings.raw_parquet_path)

        if "period" not in df.columns or df.height == 0:
            return None

        return df.select(pl.col("period").max()).item()

    # Run a full extract, ignoring any existing raw parquet or state
    def run_full_extract(self) -> ExtractResult:
        logger.info("Iniciando extracción completa desde EIA.")

        total_valid_rows = 0
        total_invalid_rows = 0
        pages_processed = 0
        pages_failed = 0
        extracted_rows: list[dict[str, Any]] = []

        with EIAClient(settings=self.settings) as client:
            total_rows_reported = client.get_total_rows()
            page_size = self.settings.page_size

            logger.info(
                "Total de filas reportadas por EIA: %s. Tamaño de página: %s",
                total_rows_reported,
                page_size,
            )

            for offset in range(0, total_rows_reported, page_size):
                try:
                    rows = client.get_rows(offset=offset, length=page_size)
                    pages_processed += 1

                    valid_rows, invalid_count = self._filter_valid_rows(rows, offset=offset)

                    extracted_rows.extend(valid_rows)
                    total_valid_rows += len(valid_rows)
                    total_invalid_rows += invalid_count

                    logger.info(
                        "Página procesada correctamente. offset=%s, recibidas=%s, válidas=%s, inválidas=%s",
                        offset,
                        len(rows),
                        len(valid_rows),
                        invalid_count,
                    )

                except EIAAuthError:
                    logger.error(
                        "Extracción abortada por error de autenticación. "
                        "No tiene sentido continuar con más páginas."
                    )
                    raise

                except EIAClientError as exc:
                    pages_failed += 1
                    logger.error(
                        "Falló la extracción de la página con offset=%s. Error: %s",
                        offset,
                        exc,
                    )
                    continue

        if not extracted_rows:
            logger.error("La extracción completa terminó sin filas válidas.")
            raise EIAClientError("La extracción completa terminó sin filas válidas para guardar.")

        raw_parquet_path = self._write_full_raw(extracted_rows)
        last_successful_period = self._get_latest_period_from_rows(extracted_rows)
        state_path = self._save_state(last_successful_period)

        logger.info(
            "Extracción completa finalizada. total_reportadas=%s, válidas=%s, inválidas=%s, páginas_ok=%s, páginas_fallidas=%s, archivo=%s, last_period=%s",
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
        )

    # Run an incremental extract, using the last successful period from state or raw parquet as cutoff, and merging new rows with existing raw parquet
    def run_incremental_extract(self) -> ExtractResult:
        logger.info("Iniciando extracción incremental desde EIA.")

        state = self._load_state()
        cutoff_period = state.get("last_successful_period") or self._get_latest_period_from_raw()

        if not cutoff_period:
            logger.info(
                "No existe estado previo ni raw parquet. Se ejecutará extracción completa."
            )
            return self.run_full_extract()

        if not self.settings.raw_parquet_path.exists():
            logger.info(
                "No existe raw parquet previo. Se ejecutará extracción completa."
            )
            return self.run_full_extract()

        logger.info(
            "Extracción incremental con solapamiento desde period=%s",
            cutoff_period,
        )

        total_valid_rows = 0
        total_invalid_rows = 0
        pages_processed = 0
        pages_failed = 0
        extracted_rows: list[dict[str, Any]] = []

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
                            "Página offset=%s sin filas válidas; se continúa con la siguiente.",
                            offset,
                        )
                        continue

                    # I'm using desc sort on period, so the first page with a newest period older than cutoff means we can stop
                    page_periods = [row["period"] for row in valid_rows]
                    page_newest_period = max(page_periods)

                    if page_newest_period < cutoff_period:
                        logger.info(
                            "Se alcanzó una página completamente anterior al corte incremental (%s). Se detiene la extracción.",
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
                        "Página incremental procesada. offset=%s, válidas_en_página=%s, seleccionadas_para_merge=%s, inválidas=%s",
                        offset,
                        len(valid_rows),
                        len(overlap_rows),
                        invalid_count,
                    )

                except EIAAuthError:
                    logger.error(
                        "Extracción incremental abortada por error de autenticación."
                    )
                    raise

                except EIAClientError as exc:
                    pages_failed += 1
                    logger.error(
                        "Falló la extracción incremental de la página con offset=%s. Error: %s",
                        offset,
                        exc,
                    )
                    continue

        if not extracted_rows:
            logger.info(
                "No se encontraron filas nuevas o solapadas para integrar. Se mantiene el raw actual."
            )
            state_path = self._save_state(cutoff_period)

            return ExtractResult(
                mode="incremental",
                total_rows_reported=0,
                total_rows_valid=0,
                total_rows_invalid=total_invalid_rows,
                pages_processed=pages_processed,
                pages_failed=pages_failed,
                raw_parquet_path=self.settings.raw_parquet_path,
                state_path=state_path,
                last_successful_period=cutoff_period,
            )

        raw_parquet_path = self._merge_and_write_raw(extracted_rows)
        last_successful_period = max(
            cutoff_period,
            self._get_latest_period_from_rows(extracted_rows) or cutoff_period,
        )
        state_path = self._save_state(last_successful_period)

        logger.info(
            "Extracción incremental finalizada. seleccionadas=%s, inválidas=%s, páginas_ok=%s, páginas_fallidas=%s, archivo=%s, last_period=%s",
            total_valid_rows,
            total_invalid_rows,
            pages_processed,
            pages_failed,
            raw_parquet_path,
            last_successful_period,
        )

        return ExtractResult(
            mode="incremental",
            total_rows_reported=0,
            total_rows_valid=total_valid_rows,
            total_rows_invalid=total_invalid_rows,
            pages_processed=pages_processed,
            pages_failed=pages_failed,
            raw_parquet_path=raw_parquet_path,
            state_path=state_path,
            last_successful_period=last_successful_period,
        )