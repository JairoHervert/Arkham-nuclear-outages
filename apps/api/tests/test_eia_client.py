from __future__ import annotations

import logging
from pprint import pprint

from app.connectors.eia_client import EIAAuthError, EIAClient, EIAClientError
from app.core.logging import setup_logging


"""
Manual smoke test for the EIA client.

Purpose:
- verify that the connector can request a page successfully
- verify that authentication and connector errors are surfaced clearly
- print one sample row for quick inspection during development
"""

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("Starting manual EIA client test.")

    try:
        # Request a small sample page to validate the connector behavior
        # without running a full extraction.
        with EIAClient() as client:
            rows = client.get_rows(offset=0, length=200)

            logger.info("Test completed successfully. Retrieved rows: %s", len(rows))

            if not rows:
                logger.warning("The API responded successfully, but returned no rows.")
                return 0

            logger.info("Printing the first retrieved row.")
            pprint(rows[0])
            return 0

    except EIAAuthError as exc:
        logger.error("Authentication error while testing the EIA client: %s", exc)
        return 2

    except EIAClientError as exc:
        logger.error("EIA client error while running the test: %s", exc)
        return 1

    except Exception:
        logger.exception("Unexpected error while running the EIA client test.")
        return 99


if __name__ == "__main__":
    raise SystemExit(main())