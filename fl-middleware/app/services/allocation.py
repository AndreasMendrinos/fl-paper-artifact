from app.allocators.base import ProviderAllocator
from app.models.allocation import (
    ResourceRequirements,
    ReservationResult,
)
from app.models.provider import ProviderId
from app.services.matching import ResourceMatchingService


class AllocationService:
    """Coordinate resource selection and provider reservation."""

    def __init__(
        self,
        matching_service: ResourceMatchingService,
        allocators: dict[
            ProviderId,
            ProviderAllocator,
        ],
    ) -> None:
        self._matching_service = matching_service
        self._allocators = allocators

    async def allocate(
        self,
        requirements: ResourceRequirements,
        *,
        duration_minutes: int,
    ) -> ReservationResult:
        allocation = self._matching_service.allocate(
            requirements
        )

        if not allocation.resources:
            return ReservationResult(
                provider="unknown",
                resource_id="unallocated",
                status="unsatisfied",
                message=(
                    "No resource matched the "
                    "requested requirements."
                ),
            )

        resource = allocation.resources[0]

        allocator = self._allocators.get(
            resource.provider
        )

        if allocator is None:
            return ReservationResult(
                provider=resource.provider.value,
                resource_id=resource.id,
                status="unsupported",
                message=(
                    "No reservation allocator is "
                    "registered for this provider."
                ),
            )

        native_result = await allocator.reserve(
            resource,
            duration_minutes=duration_minutes,
        )

        return ReservationResult(
            provider=resource.provider.value,
            resource_id=resource.id,
            status=str(
                native_result.get(
                    "status",
                    "planned",
                )
            ),
            reservation_id=(
                str(native_result["reservation_id"])
                if native_result.get(
                    "reservation_id"
                )
                is not None
                else None
            ),
            message=(
                str(native_result["message"])
                if native_result.get("message")
                is not None
                else None
            ),
            native_data=native_result,
        )

    async def get_reservation(
        self,
        *,
        provider: ProviderId,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        allocator = self._allocators.get(provider)

        if allocator is None:
            raise ValueError(
                f"No allocator registered for {provider.value}."
            )

        return await allocator.get_reservation(
            site=site,
            reservation_id=reservation_id,
        )


    async def release(
        self,
        *,
        provider: ProviderId,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        allocator = self._allocators.get(provider)

        if allocator is None:
            raise ValueError(
                f"No allocator registered for {provider.value}."
            )

        return await allocator.release(
            site=site,
            reservation_id=reservation_id,
        )
        