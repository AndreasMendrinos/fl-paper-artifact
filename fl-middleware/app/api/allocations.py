from fastapi import APIRouter

from app.models.allocation import (
    ResourceAllocation,
    ResourceRequirements,
)
from app.services import matching_service

from app.models.allocation import (
    AllocationReservationRequest,
    ReservationResult,
)
from app.services import allocation_service

from app.models.provider import ProviderId

router = APIRouter(
    prefix="/api/v1",
    tags=["allocations"],
)


@router.post(
    "/allocations",
    response_model=ResourceAllocation,
)
def match_resources(
    requirements: ResourceRequirements,
) -> ResourceAllocation:
    return matching_service.allocate(requirements)


@router.post(
    "/allocations/reserve",
    response_model=ReservationResult,
)
async def reserve_resource(
    request: AllocationReservationRequest,
) -> ReservationResult:
    return await allocation_service.allocate(
        request.requirements,
        duration_minutes=(
            request.duration_minutes
        ),
    )


@router.get(
    "/reservations/{provider}/{site}/{reservation_id}"
)
async def get_reservation(
    provider: ProviderId,
    site: str,
    reservation_id: str,
) -> dict[str, object]:
    return await allocation_service.get_reservation(
        provider=provider,
        site=site,
        reservation_id=reservation_id,
    )

@router.delete(
    "/reservations/{provider}/{site}/{reservation_id}"
)
async def release_reservation(
    provider: ProviderId,
    site: str,
    reservation_id: str,
) -> dict[str, object]:
    return await allocation_service.release(
        provider=provider,
        site=site,
        reservation_id=reservation_id,
    )