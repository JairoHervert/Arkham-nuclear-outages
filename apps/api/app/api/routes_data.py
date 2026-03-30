from __future__ import annotations

import logging
from datetime import date as DateType
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.api.dependencies.auth import require_read_access
from app.schemas.outage import DataQueryParams, PaginatedDataResponse
from app.services.query_service import (
    QueryService,
    QueryServiceError,
    QueryValidationError,
)

"""
HTTP route for querying outage data.

Responsibilities:
- receive validated query parameters from the HTTP layer
- build a DataQueryParams object
- call QueryService
- return a paginated JSON response
"""

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])


@router.get(
    "",
    response_model=PaginatedDataResponse,
    dependencies=[Depends(require_read_access)],
)
def get_outage_data(
    view: Literal["generator", "facility"] = Query(
        default="generator",
        description="Selects the output view: generator detail or facility summary.",
    ),
    date: DateType | None = Query(
        default=None,
        description="Filters records by exact outage date (YYYY-MM-DD).",
    ),
    search: str | None = Query(
        default=None,
        description="Free-text search over facility name, facility id, generator id, or generator code.",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number, starting at 1.",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of rows per page. Maximum allowed is 100.",
    ),
    sort_by: str | None = Query(
        default=None,
        description="Column name used for sorting. Allowed values depend on the selected view.",
    ),
    sort_order: Literal["asc", "desc"] = Query(
        default="asc",
        description="Sort direction.",
    ),
) -> PaginatedDataResponse:
    logger.info(
        "Received /data request. view=%s, date=%s, search=%s, page=%s, page_size=%s, sort_by=%s, sort_order=%s",
        view,
        date,
        search,
        page,
        page_size,
        sort_by,
        sort_order,
    )

    try:
        params = DataQueryParams(
            view=view,
            date=date,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        service = QueryService()
        response = service.query_data(params)

        logger.info(
            "/data request completed successfully. returned_items=%s, total_items=%s, total_pages=%s",
            len(response.items),
            response.total_items,
            response.total_pages,
        )

        return response

    except ValidationError as exc:
        logger.warning("Invalid /data request parameters: %s", exc)
        raise HTTPException(
            status_code=422,
            detail="Invalid query parameters.",
        ) from exc

    except QueryValidationError as exc:
        logger.warning("Query validation failed for /data request: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except QueryServiceError as exc:
        logger.exception("Query service failed while handling /data: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to query outage data.",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error while handling /data: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Unexpected server error while querying outage data.",
        ) from exc