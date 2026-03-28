from app.core.logging import setup_logging
from app.connectors.eia_client import EIAClient

setup_logging()

with EIAClient() as client:
    rows = client.get_rows(offset=0, length=200)
    print(rows[:5])