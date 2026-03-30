import logging
from pprint import pprint

from app.core.logging import setup_logging
from app.services.transform_service import (
    TransformService,
    TransformServiceError,
)

"""
Manual test for the TransformService.

- This script can be run directly to execute the transform process on the raw parquet data and log the results.
"""

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("Starting manual transform service test.")

    try:
        service = TransformService()
        result = service.run_transform()

        pprint(
            {
                "raw_rows": result.raw_rows,
                "plants_rows": result.facilities_rows,
                "generators_rows": result.generators_rows,
                "outages_rows": result.outages_rows,
                "plants_parquet_path": str(result.facilities_parquet_path),
                "generators_parquet_path": str(result.generators_parquet_path),
                "outages_parquet_path": str(result.outages_parquet_path),
            }
        )
        return 0

    except TransformServiceError as exc:
        logger.exception("Transform service failed: %s", exc)
        return 1

    except Exception as exc:
        logger.exception("Unexpected error during transform: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())