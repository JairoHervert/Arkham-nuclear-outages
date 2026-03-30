from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

"""
Schemas for refresh requests and responses.
"""

# endopoint /refresh can be called with either "auto" or "full" mode
# if "auto", the service will use ExtractService.run_extract() which decides internally whether to do a full or incremental extract based on the last successful extract state
# if "full", the service will use ExtractService.run_full_extract() which forces a full extract
class RefreshRequest(BaseModel):
    mode: Literal["auto", "full"] = "auto"

# The response includes detailed summaries of the extract and transform steps
class ExtractSummary(BaseModel):
    mode: str
    total_rows_reported: int
    total_rows_valid: int
    total_rows_invalid: int
    pages_processed: int
    pages_failed: int
    raw_parquet_path: str
    state_path: str
    last_successful_period: str | None
    full_extract_completed: bool
    next_offset: int | None

# The transform summary includes counts of rows processed and paths to the resulting parquet files
class TransformSummary(BaseModel):
    raw_rows: int
    facilities_rows: int
    generators_rows: int
    outages_rows: int
    facilities_parquet_path: str
    generators_parquet_path: str
    outages_parquet_path: str


# complete response model for the /refresh endpoint
class RefreshResponse(BaseModel):
    # no error details are included because any errors would result in an HTTPException
    status: Literal["success"]
    requested_mode: Literal["auto", "full"]
    extract: ExtractSummary
    transform: TransformSummary