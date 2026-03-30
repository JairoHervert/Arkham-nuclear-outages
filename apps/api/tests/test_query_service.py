from __future__ import annotations

import logging
from datetime import date as DateType
from pprint import pprint

from app.core.logging import setup_logging
from app.schemas.outage import DataQueryParams
from app.services.query_service import QueryService, QueryServiceError

logger = logging.getLogger(__name__)

"""
Manual test script for QueryService.

This script is useful to validate:
- generator view
- facility view
- date filtering
- text search
- sorting
- pagination

Uncomment one test case at a time while developing.
"""


def main() -> int:
    setup_logging()
    logger.info("Starting manual query service test.")

    try:
        service = QueryService()

        # ---------------------------------------------------------------------
        # Test 1: Generator view with pagination and sorting
        # ---------------------------------------------------------------------
        # result = service.query_data(
        #     DataQueryParams(
        #         view="generator",
        #         page=1,
        #         page_size=5,
        #         sort_by="period_date",
        #         sort_order="asc",
        #     )
        # )

        # ---------------------------------------------------------------------
        # Test 2: Facility view with pagination and sorting
        # ---------------------------------------------------------------------
        # result = service.query_data(
        #     DataQueryParams(
        #         view="facility",
        #         page=1,
        #         page_size=5,
        #         sort_by="period_date",
        #         sort_order="desc",
        #     )
        # )

        # ---------------------------------------------------------------------
        # Test 3: Generator view filtered by exact date
        # ---------------------------------------------------------------------
        # result = service.query_data(
        #     DataQueryParams(
        #         view="generator",
        #         date=DateType(2021, 6, 30),
        #         page=1,
        #         page_size=5,
        #         sort_by="outage_mw",
        #         sort_order="desc",
        #     )
        # )

        # ---------------------------------------------------------------------
        # Test 4: Facility view filtered by exact date
        # ---------------------------------------------------------------------
        # result = service.query_data(
        #     DataQueryParams(
        #         view="facility",
        #         date=DateType(2026, 1, 27),
        #         page=1,
        #         page_size=5,
        #         sort_by="percent_outage",
        #         sort_order="desc",
        #     )
        # )

        # ---------------------------------------------------------------------
        # Test 5: Generator view with text search
        # Useful for plant names, facility ids, generator ids, or generator codes
        # ---------------------------------------------------------------------
        result = service.query_data(
            DataQueryParams(
                view="generator",
                search="Arkansas",
                page=1,
                page_size=5,
                sort_by="facility_name",
                sort_order="asc",
            )
        )

        # ---------------------------------------------------------------------
        # Test 6: Facility view with text search
        # ---------------------------------------------------------------------
        # result = service.query_data(
        #     DataQueryParams(
        #         view="facility",
        #         search="Arkansas",
        #         page=1,
        #         page_size=5,
        #         sort_by="facility_name",
        #         sort_order="desc",
        #     )
        # )

        # ---------------------------------------------------------------------
        # Test 7: Generator view sorted by outage descending
        # ---------------------------------------------------------------------
        # result = service.query_data(
        #     DataQueryParams(
        #         view="generator",
        #         page=1,
        #         page_size=10,
        #         sort_by="outage_mw",
        #         sort_order="desc",
        #     )
        # )

        # ---------------------------------------------------------------------
        # Test 8: Facility view sorted by percent outage descending
        # ---------------------------------------------------------------------
        # result = service.query_data(
        #     DataQueryParams(
        #         view="facility",
        #         page=1,
        #         page_size=10,
        #         sort_by="percent_outage",
        #         sort_order="desc",
        #     )
        # )

        pprint(result.model_dump())
        return 0

    except QueryServiceError as exc:
        logger.exception("Query service failed: %s", exc)
        return 1

    except Exception as exc:
        logger.exception("Unexpected error during query test: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())