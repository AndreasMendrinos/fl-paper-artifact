from abc import ABC, abstractmethod

from app.models.provider import ProviderInfo
from app.models.resource import NormalizedResource


class ProviderAdapterError(RuntimeError):
    """Raised when a provider cannot complete an operation."""


class ProviderAdapter(ABC):
    """Common contract implemented by every provider adapter."""

    @property
    @abstractmethod
    def provider_info(self) -> ProviderInfo:
        """Return provider metadata and supported capabilities."""

    @abstractmethod
    async def discover_resources(self) -> list[NormalizedResource]:
        """Retrieve and normalize resources from the provider."""

    async def health_check(self) -> bool:
        """
        Check whether the provider adapter is operational.

        Adapters may override this method with a real remote request.
        """

        return self.provider_info.enabled