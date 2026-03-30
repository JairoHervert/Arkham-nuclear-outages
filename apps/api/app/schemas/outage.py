from __future__ import annotations

from datetime import date as DateType
from typing import Literal

# Field and field_validator are used for validation such as default values and min/max constraints.
from pydantic import BaseModel, Field, field_validator

"""
Schemas for outage data query parameters and paginated responses.
"""

# Schema definitions for outage data query parameters and response items
class DataQueryParams(BaseModel):
    view: Literal["generator", "facility"] = "generator"
    date: DateType | None = None
    search: str | None = None

    # page default is 1 and must be >= 1
    page: int = Field(default=1, ge=1)

    # page_size default is 20 and must be between 1 and 100
    page_size: int = Field(default=20, ge=1, le=100)

    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

# One item in the generator view response
class GeneratorOutageItem(BaseModel):
    period_date: DateType
    generator_id: str
    generator_code: str
    facility_id: str
    facility_name: str
    capacity_mw: float
    outage_mw: float
    percent_outage: float

# One item in the facility view response
class FacilityOutageItem(BaseModel):
    period_date: DateType
    facility_id: str
    facility_name: str
    total_capacity_mw: float
    total_outage_mw: float
    percent_outage: float

# Complete JSON response schema for paginated data queries
class PaginatedDataResponse(BaseModel):
    view: Literal["generator", "facility"]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: list[GeneratorOutageItem | FacilityOutageItem]