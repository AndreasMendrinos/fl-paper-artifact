from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings


router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Check middleware health",
)
async def health_check() -> dict[str, object]:
    settings = get_settings()

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc),
    }