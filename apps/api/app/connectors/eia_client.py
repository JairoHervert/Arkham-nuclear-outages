from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class EIAClientError(Exception):
    """Base error for the EIA client."""


class EIAAuthError(EIAClientError):
    """Authentication or authorization error while calling EIA."""


class EIAResponseError(EIAClientError):
    """Invalid or unexpected response returned by EIA."""


class EIAClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = httpx.Client(
            timeout=self.settings.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )

    def _build_params(self, offset: int = 0, length: int | None = None) -> dict[str, Any]:
        page_size = length or self.settings.page_size

        return {
            "api_key": self.settings.eia_api_key.get_secret_value(),
            "frequency": "daily",
            "data[0]": "capacity",
            "data[1]": "outage",
            "data[2]": "percentOutage",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": offset,
            "length": page_size,
        }

    def _extract_error_message(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                if "error" in payload:
                    return f"EIA API error ({response.status_code}): {payload['error']}"
                if "message" in payload:
                    return f"EIA API error ({response.status_code}): {payload['message']}"
        except ValueError:
            pass

        text = response.text.strip()
        if text:
            return f"EIA API error ({response.status_code}): {text}"

        return f"EIA API error ({response.status_code}) without additional details."

    def get_page(self, offset: int = 0, length: int | None = None) -> dict[str, Any]:
        params = self._build_params(offset=offset, length=length)
        page_size = length or self.settings.page_size

        logger.info("Requesting EIA page: offset=%s, length=%s", offset, page_size)

        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.get(self.settings.eia_url, params=params)

                if response.status_code in (401, 403):
                    logger.error("Authentication failed while calling EIA.")
                    raise EIAAuthError(
                        "Could not authenticate with EIA. "
                        "Check your API key and endpoint access."
                    )

                if 500 <= response.status_code < 600:
                    if attempt < self.settings.max_retries:
                        logger.warning(
                            "EIA returned %s. Retrying attempt %s/%s",
                            response.status_code,
                            attempt + 1,
                            self.settings.max_retries,
                        )
                        time.sleep(self.settings.retry_backoff_seconds * (attempt + 1))
                        continue

                    logger.error("EIA returned a server error: %s", response.status_code)
                    raise EIAResponseError(self._extract_error_message(response))

                if response.is_error:
                    logger.error("HTTP error while calling EIA: %s", response.status_code)
                    raise EIAResponseError(self._extract_error_message(response))

                payload = response.json()

                if not isinstance(payload, dict):
                    logger.error("EIA response was not a JSON object.")
                    raise EIAResponseError("EIA response is not a valid JSON object.")

                if "response" not in payload:
                    logger.error("EIA JSON response does not contain the 'response' key.")
                    raise EIAResponseError("EIA JSON response does not contain the 'response' key.")

                logger.info("EIA page retrieved successfully.")
                return payload

            except httpx.RequestError as exc:
                if attempt < self.settings.max_retries:
                    logger.warning(
                        "Network error while calling EIA. Retrying attempt %s/%s",
                        attempt + 1,
                        self.settings.max_retries,
                    )
                    time.sleep(self.settings.retry_backoff_seconds * (attempt + 1))
                    continue

                logger.exception("Could not reach EIA after multiple attempts.")
                raise EIAClientError(
                    "Could not communicate with the EIA API after multiple attempts."
                ) from exc

            except ValueError as exc:
                logger.exception("EIA response does not contain valid JSON.")
                raise EIAResponseError("EIA response does not contain valid JSON.") from exc

        logger.error("All attempts to call EIA were exhausted.")
        raise EIAClientError("An unexpected error occurred while calling EIA.")

    def get_rows(self, offset: int = 0, length: int | None = None) -> list[dict[str, Any]]:
        payload = self.get_page(offset=offset, length=length)
        response_block = payload.get("response", {})
        data = response_block.get("data", [])

        if not isinstance(data, list):
            logger.error("The response.data field does not have the expected format.")
            raise EIAResponseError("The response.data field does not have the expected format.")

        logger.info("Retrieved %s rows.", len(data))
        return data

    def get_total_rows(self) -> int:
        payload = self.get_page(offset=0, length=1)
        response_block = payload.get("response", {})
        total = response_block.get("total", 0)

        try:
            total_rows = int(total)
            logger.info("EIA reported %s total rows.", total_rows)
            return total_rows
        except (TypeError, ValueError) as exc:
            logger.error("The response.total field is not a valid integer.")
            raise EIAResponseError("The response.total field is not a valid integer.") from exc

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "EIAClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()