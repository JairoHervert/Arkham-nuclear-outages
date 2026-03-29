from __future__ import annotations

import logging
from pprint import pprint

from app.connectors.eia_client import EIAAuthError, EIAClient, EIAClientError
from app.core.logging import setup_logging


logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("Iniciando prueba manual del cliente EIA.")

    try:
        with EIAClient() as client:
            rows = client.get_rows(offset=0, length=200)

            logger.info("Prueba completada con éxito. Filas recuperadas: %s", len(rows))

            if not rows:
                logger.warning("La API respondió correctamente, pero no devolvió filas.")
                return 0

            logger.info("Mostrando la primera fila recuperada.")
            pprint(rows[0])
            return 0

    except EIAAuthError as exc:
        logger.error("Error de autenticación con EIA: %s", exc)
        return 2

    except EIAClientError as exc:
        logger.error("Error del cliente EIA: %s", exc)
        return 1

    except Exception:
        logger.exception("Ocurrió un error inesperado durante la prueba del cliente EIA.")
        return 99


if __name__ == "__main__":
    raise SystemExit(main())