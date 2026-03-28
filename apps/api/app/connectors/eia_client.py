from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class EIAClientError(Exception):
    """Error base del cliente EIA."""


class EIAAuthError(EIAClientError):
    """Error de autenticación o autorización contra EIA."""


class EIAResponseError(EIAClientError):
    """Error de respuesta inválida o inesperada de EIA."""


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

        return f"EIA API error ({response.status_code}) sin detalle adicional."

    def get_page(self, offset: int = 0, length: int | None = None) -> dict[str, Any]:
        params = self._build_params(offset=offset, length=length)
        page_size = length or self.settings.page_size

        logger.info("Consultando EIA: offset=%s, length=%s", offset, page_size)

        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.get(self.settings.eia_url, params=params)

                if response.status_code in (401, 403):
                    logger.error("Autenticación fallida contra EIA.")
                    raise EIAAuthError(
                        "No fue posible autenticarse con EIA. "
                        "Revisa tu API key y el acceso al endpoint."
                    )

                if 500 <= response.status_code < 600:
                    if attempt < self.settings.max_retries:
                        logger.warning(
                            "EIA devolvió %s. Reintentando intento %s/%s",
                            response.status_code,
                            attempt + 1,
                            self.settings.max_retries,
                        )
                        time.sleep(self.settings.retry_backoff_seconds * (attempt + 1))
                        continue

                    logger.error("EIA devolvió error del servidor: %s", response.status_code)
                    raise EIAResponseError(self._extract_error_message(response))

                if response.is_error:
                    logger.error("Error HTTP al consultar EIA: %s", response.status_code)
                    raise EIAResponseError(self._extract_error_message(response))

                payload = response.json()

                if not isinstance(payload, dict):
                    logger.error("La respuesta de EIA no fue un objeto JSON.")
                    raise EIAResponseError("La respuesta de EIA no es un JSON objeto válido.")

                if "response" not in payload:
                    logger.error("La respuesta JSON no contiene la clave 'response'.")
                    raise EIAResponseError("La respuesta JSON no contiene la clave 'response'.")

                logger.info("Página obtenida correctamente desde EIA.")
                return payload

            except httpx.RequestError as exc:
                if attempt < self.settings.max_retries:
                    logger.warning(
                        "Fallo de red al consultar EIA. Reintentando intento %s/%s",
                        attempt + 1,
                        self.settings.max_retries,
                    )
                    time.sleep(self.settings.retry_backoff_seconds * (attempt + 1))
                    continue

                logger.exception("No fue posible comunicarse con EIA tras varios intentos.")
                raise EIAClientError(
                    "No fue posible comunicarse con la API de EIA después de varios intentos."
                ) from exc

            except ValueError as exc:
                logger.exception("La respuesta de EIA no contiene JSON válido.")
                raise EIAResponseError("La respuesta de EIA no contiene JSON válido.") from exc

        logger.error("Se agotaron los intentos al consultar EIA.")
        raise EIAClientError("Ocurrió un error inesperado al consultar EIA.")

    def get_rows(self, offset: int = 0, length: int | None = None) -> list[dict[str, Any]]:
        payload = self.get_page(offset=offset, length=length)
        response_block = payload.get("response", {})
        data = response_block.get("data", [])

        if not isinstance(data, list):
            logger.error("El campo response.data no tiene el formato esperado.")
            raise EIAResponseError("El campo 'response.data' no tiene el formato esperado.")

        logger.info("Se obtuvieron %s filas.", len(data))
        return data

    def get_total_rows(self) -> int:
        payload = self.get_page(offset=0, length=1)
        response_block = payload.get("response", {})
        total = response_block.get("total", 0)

        try:
            total_rows = int(total)
            logger.info("Total de filas reportadas por EIA: %s", total_rows)
            return total_rows
        except (TypeError, ValueError) as exc:
            logger.error("El campo response.total no es un entero válido.")
            raise EIAResponseError("El campo 'response.total' no es un entero válido.") from exc

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "EIAClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()