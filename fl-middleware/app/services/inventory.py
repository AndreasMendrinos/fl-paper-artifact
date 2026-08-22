import asyncio
from datetime import datetime, timezone

from app.models.provider import ProviderId, ProviderInfo
from app.models.resource import NormalizedResource
from app.providers.base import ProviderAdapter
from app.models.provider import (
    ProviderId,
    ProviderInfo,
    ProviderStatus,
)
from app.models.resource import ResourceAvailability
from app.models.resource import AvailabilityState

class InventoryService:
    """Maintains the normalized in-memory resource inventory."""

    def __init__(self, adapters: list[ProviderAdapter]) -> None:
        self._adapters = {
            adapter.provider_info.id: adapter
            for adapter in adapters
        }
        
        self._resources: dict[str, NormalizedResource] = {}
        self._last_refresh: datetime | None = None
        self._provider_errors: dict[ProviderId, str] = {}

    @property
    def last_refresh(self) -> datetime | None:
        return self._last_refresh

    def list_providers(self) -> list[ProviderInfo]:
        providers: list[ProviderInfo] = []

        for adapter in self._adapters.values():
            provider_info = adapter.provider_info
            error = self._provider_errors.get(provider_info.id)

            updates: dict[str, object] = {
                "last_error": error,
            }

            if error is not None and provider_info.enabled:
                updates["status"] = ProviderStatus.DEGRADED

            provider = provider_info.model_copy(update=updates)
            providers.append(provider)

        return sorted(
            providers,
            key=lambda item: item.id.value,
        )

    async def refresh(
        self,
        provider_ids: set[ProviderId] | None = None,
    ) -> dict[str, object]:
        selected_adapters = [
            adapter
            for provider_id, adapter in self._adapters.items()
            if provider_ids is None or provider_id in provider_ids
        ]

        results = await asyncio.gather(
            *[
                self._discover_safely(adapter)
                for adapter in selected_adapters
            ]
        )

        refreshed_provider_ids: list[str] = []
        discovered_count = 0

        for provider_id, resources, error in results:
            if error is not None:
                self._provider_errors[provider_id] = error
                continue

            self._provider_errors.pop(provider_id, None)

            # Replace only the inventory records belonging to this provider.
            self._resources = {
                resource_id: resource
                for resource_id, resource in self._resources.items()
                if resource.provider != provider_id
            }

            for resource in resources:
                self._resources[resource.id] = resource

            refreshed_provider_ids.append(provider_id.value)
            discovered_count += len(resources)

        self._last_refresh = datetime.now(timezone.utc)

        return {
            "refreshed_at": self._last_refresh,
            "providers": refreshed_provider_ids,
            "discovered_resources": discovered_count,
            "total_inventory_resources": len(self._resources),
            "errors": {
                provider.value: error
                for provider, error in self._provider_errors.items()
            },
        }

    async def _discover_safely(
        self,
        adapter: ProviderAdapter,
    ) -> tuple[ProviderId, list[NormalizedResource], str | None]:
        provider_id = adapter.provider_info.id

        try:
            resources = await adapter.discover_resources()
            return provider_id, resources, None
        except Exception as exc:
            return provider_id, [], str(exc)

    def list_resources(
        self,
        provider: ProviderId | None = None,
        site: str | None = None,
        available: bool | None = None,
        resource_type: str | None = None,
        capability: str | None = None,
    ) -> list[NormalizedResource]:
        resources = list(self._resources.values())

        if provider is not None:
            resources = [
                item for item in resources
                if item.provider == provider
            ]

        if site is not None:
            normalized_site = site.casefold()
            resources = [
                item for item in resources
                if item.site.casefold() == normalized_site
            ]

        if available is not None:
            expected_state = (
                #ResourceAvailability.AVAILABLE
                AvailabilityState.AVAILABLE
                if available
                #else ResourceAvailability.UNAVAILABLE
                else AvailabilityState.UNAVAILABLE
            )

            resources = [
                item
                for item in resources
                if item.availability.state == expected_state
            ]

        if resource_type is not None:
            resources = [
                item
                for item in resources
                if item.resource_type.value == resource_type
            ]

        if capability is not None:
            normalized_capability = capability.casefold()
            resources = [
                item
                for item in resources
                if normalized_capability
                in {
                    value.casefold()
                    for value in item.capabilities
                }
            ]

        return sorted(
            resources,
            key=lambda item: (
                item.provider.value,
                item.site,
                item.name,
            ),
        )

    def get_resource(
        self,
        resource_id: str,
    ) -> NormalizedResource | None:
        return self._resources.get(resource_id)