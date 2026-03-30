from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.schemas.refresh import RefreshRequest, RefreshResponse
from app.services.refresh_service import RefreshService, RefreshServiceError

"""
HTTP route for triggering the refresh pipeline.
"""

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/refresh", tags=["refresh"])


@router.post("", response_model=RefreshResponse)
def refresh_data(request: RefreshRequest) -> RefreshResponse:
    logger.info("Received /refresh request. requested_mode=%s", request.mode)

    try:
        service = RefreshService()
        response = service.run_refresh(request)

        logger.info(
            "/refresh request completed successfully. requested_mode=%s, extract_mode=%s",
            request.mode,
            response.extract.mode,
        )
        return response

    except ValidationError as exc:
        logger.warning("Invalid /refresh request payload: %s", exc)
        raise HTTPException(
            status_code=422,
            detail="Invalid refresh request payload.",
        ) from exc

    except RefreshServiceError as exc:
        logger.error("Refresh service failed while handling /refresh: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.error("Unexpected error while handling /refresh: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Unexpected server error while refreshing data.",
        ) from exc