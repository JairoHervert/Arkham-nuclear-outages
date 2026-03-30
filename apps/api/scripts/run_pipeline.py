import argparse
import logging
from pathlib import Path
import sys

# Allow running the script from apps/api/scripts without installing the backend as a package.
API_ROOT = Path(__file__).resolve().parents[1]

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.logging import setup_logging
from app.services.extract_service import EIAAuthError, EIAClientError, ExtractService
from app.services.transform_service import TransformService, TransformServiceError

logger = logging.getLogger(__name__)

"""
Pipeline runner script for the Arkham Nuclear Outages project.

This script:
1. extracts data from the EIA API
2. persists the raw parquet dataset
3. transforms the raw parquet into the modeled parquet tables:
   - facilities.parquet
   - generators.parquet
   - outages.parquet

It is intended as the manual executable script requested by the challenge.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Nuclear Outages data pipeline (extract + transform)."
    )

    parser.add_argument(
        "--mode",
        choices=["auto", "full"],
        default="auto",
        help=(
            "Extraction mode. "
            "'auto' lets ExtractService decide between full/resume/incremental. "
            "'full' forces a full extraction from scratch."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging()

    logger.info("Starting pipeline run. mode=%s", args.mode)

    try:
        # Step 1: Extract data from EIA and persist raw parquet
        extract_service = ExtractService()

        if args.mode == "full":
            extract_result = extract_service.run_full_extract()
        else:
            extract_result = extract_service.run_extract()

        logger.info(
            (
                "Extraction finished successfully. "
                "mode=%s, reported_rows=%s, valid_rows=%s, invalid_rows=%s, "
                "pages_processed=%s, pages_failed=%s, raw_parquet=%s"
            ),
            extract_result.mode,
            extract_result.total_rows_reported,
            extract_result.total_rows_valid,
            extract_result.total_rows_invalid,
            extract_result.pages_processed,
            extract_result.pages_failed,
            extract_result.raw_parquet_path,
        )

        # Step 2: Transform raw parquet into the modeled parquet tables
        transform_service = TransformService()
        transform_result = transform_service.run_transform()

        logger.info(
            (
                "Transformation finished successfully. "
                "raw_rows=%s, facilities_rows=%s, generators_rows=%s, outages_rows=%s"
            ),
            transform_result.raw_rows,
            transform_result.facilities_rows,
            transform_result.generators_rows,
            transform_result.outages_rows,
        )

        print("\nPipeline completed successfully.\n")
        print("Extract summary:")
        print(f"  Requested mode: {args.mode}")
        print(f"  Actual extract mode: {extract_result.mode}")
        print(f"  Total rows reported by API: {extract_result.total_rows_reported}")
        print(f"  Total valid rows extracted: {extract_result.total_rows_valid}")
        print(f"  Total invalid rows discarded: {extract_result.total_rows_invalid}")
        print(f"  Pages processed: {extract_result.pages_processed}")
        print(f"  Pages failed: {extract_result.pages_failed}")
        print(f"  Raw parquet: {extract_result.raw_parquet_path}")
        print(f"  State file: {extract_result.state_path}")
        print(f"  Last successful period: {extract_result.last_successful_period}")
        print()

        print("Transform summary:")
        print(f"  Raw rows loaded: {transform_result.raw_rows}")
        print(f"  Facilities rows: {transform_result.facilities_rows}")
        print(f"  Generators rows: {transform_result.generators_rows}")
        print(f"  Outages rows: {transform_result.outages_rows}")
        print(f"  Facilities parquet: {transform_result.facilities_parquet_path}")
        print(f"  Generators parquet: {transform_result.generators_parquet_path}")
        print(f"  Outages parquet: {transform_result.outages_parquet_path}")
        print()

        return 0

    except (EIAAuthError, EIAClientError) as exc:
        logger.exception("Pipeline failed during extraction: %s", exc)
        print(f"\nPipeline failed during extraction: {exc}\n")
        return 1

    except TransformServiceError as exc:
        logger.exception("Pipeline failed during transformation: %s", exc)
        print(f"\nPipeline failed during transformation: {exc}\n")
        return 1

    except Exception as exc:
        logger.exception("Unexpected pipeline failure: %s", exc)
        print(f"\nUnexpected pipeline failure: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())