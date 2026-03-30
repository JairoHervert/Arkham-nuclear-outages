from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_data import router as data_router
from app.api.routes_refresh import router as refresh_router
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="Arkham Nuclear Outages API",
    lifespan=lifespan,
)

app.include_router(data_router)
app.include_router(refresh_router)