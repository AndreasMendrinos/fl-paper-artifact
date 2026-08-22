from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.providers import router as providers_router
from app.api.resources import router as resources_router
from app.config import get_settings
from app.services import inventory_service

from app.api.allocations import (
    router as allocations_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Initial discovery when the middleware starts.
    await inventory_service.refresh()

    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Middleware prototype for discovering, normalizing, "
        "filtering, and planning deployments across IoT-LAB, "
        "Chameleon, and Grid'5000."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Health",
            "description": "Middleware health and runtime status.",
        },
        {
            "name": "Providers",
            "description": (
                "Provider adapters and their supported capabilities."
            ),
        },
        {
            "name": "Resources",
            "description": (
                "Normalized resource discovery and filtering."
            ),
        },
    ],
)

app.include_router(health_router)
app.include_router(providers_router)
app.include_router(resources_router)
app.include_router(allocations_router)


@app.get(
    "/",
    tags=["Health"],
    include_in_schema=False,
)
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "documentation": "/docs",
        "openapi": "/openapi.json",
        "redoc": "/redoc",
    }