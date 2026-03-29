import logging
from dataclasses import asdict
from pprint import pprint

from app.connectors.eia_client import EIAAuthError, EIAClientError
from app.core.logging import setup_logging
from app.services.extract_service import ExtractService

"""
Manual smoke test for the extraction service.

Purpose:
- exercise the extraction flow from a single entry point
- verify full, resumed, or incremental behavior
- print a compact summary of the extraction result for quick inspection
"""

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("Starting manual extraction service test.")

    try:
        service = ExtractService()

        # Default behavior: decide automatically between full, resume, or incremental
        result = service.run_extract()

        # Force full extract
        # result = service.run_full_extract()

        # Force incremental extract
        # result = service.run_incremental_extract()

        logger.info("Extraction test completed successfully.")
        logger.info(
            "Mode=%s | valid=%s | invalid=%s | pages_ok=%s | pages_failed=%s | raw=%s",
            result.mode,
            result.total_rows_valid,
            result.total_rows_invalid,
            result.pages_processed,
            result.pages_failed,
            result.raw_parquet_path,
        )

        pprint(asdict(result))
        return 0

    except EIAAuthError as exc:
        logger.error("Authentication error while running extraction test: %s", exc)
        return 2

    except EIAClientError as exc:
        logger.error("EIA connector error while running extraction test: %s", exc)
        return 1

    except Exception:
        logger.exception("Unexpected error while running extraction service test.")
        return 99


if __name__ == "__main__":
    raise SystemExit(main())