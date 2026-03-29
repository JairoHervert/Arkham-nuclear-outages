from app.core.logging import setup_logging
from app.services.extract_service import ExtractService


def main() -> int:
    setup_logging()

    service = ExtractService()

    # Primera vez:
    # result = service.run_full_extract()

    # Siguientes veces:
    result = service.run_incremental_extract()

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())