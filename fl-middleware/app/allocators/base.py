from abc import ABC, abstractmethod

from app.models.resource import NormalizedResource


class ProviderAllocator(ABC):
    """Reserve resources using provider-native mechanisms."""

    @abstractmethod
    async def reserve(
        self,
        resource: NormalizedResource,
        *,
        duration_minutes: int,
    ) -> dict[str, object]:
        """Reserve the selected resource."""
        raise NotImplementedError

    @abstractmethod
    async def get_reservation(
        self,
        *,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    async def release(
        self,
        *,
        site: str,
        reservation_id: str,
    ) -> dict[str, object]:
        raise NotImplementedError