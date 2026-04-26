from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import get_settings

"""
Authentication and authorization dependencies for the API.

Policy:
- read access: allows either the read key or the admin key
- admin access: allows only the admin key
"""


def require_read_access(
    x_api_key: str | None = Header(default=None, alias="X-Internal-API-Key")
) -> None:
    settings = get_settings()

    read_key = settings.nuclear_outages_read_api_key.get_secret_value()
    admin_key = settings.nuclear_outages_admin_api_key.get_secret_value()

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )

    if x_api_key not in {read_key, admin_key}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )


def require_admin_access(
    x_api_key: str | None = Header(default=None, alias="X-Internal-API-Key")
) -> None:
    settings = get_settings()

    read_key = settings.nuclear_outages_read_api_key.get_secret_value()
    admin_key = settings.nuclear_outages_admin_api_key.get_secret_value()

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )

    if x_api_key == read_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API key required.",
        )

    if x_api_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )