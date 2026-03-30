import logging
from pprint import pprint

from app.core.logging import setup_logging
from app.schemas.refresh import RefreshRequest
from app.services.refresh_service import RefreshService, RefreshServiceError

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("Starting manual refresh service test.")

    try:
        service = RefreshService()

        # ---------------------------------------------------------------------
        # Test 1: Automatic refresh mode
        # This lets ExtractService decide whether to run full, resume, or incremental
        # ---------------------------------------------------------------------
        result = service.run_refresh(
            RefreshRequest(mode="auto")
        )

        # ---------------------------------------------------------------------
        # Test 2: Forced full refresh mode
        # Uncomment this block only when you explicitly want a full extract
        # ---------------------------------------------------------------------
        # result = service.run_refresh(
        #     RefreshRequest(mode="full")
        # )

        pprint(result.model_dump())
        return 0

    except RefreshServiceError as exc:
        logger.exception("Refresh service failed: %s", exc)
        return 1

    except Exception as exc:
        logger.exception("Unexpected error during refresh test: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())