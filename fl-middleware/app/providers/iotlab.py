from __future__ import annotations
from typing import Any

from app.clients.iotlab import IoTLabClient

from app.mappers.iotlab import IoTLabMapper
from app.models.provider import (
    ProviderId,
    ProviderInfo,
    ProviderMode,
    ProviderStatus,
)
from app.models.resource import NormalizedResource
from app.providers.base import ProviderAdapter
from app.providers.fixtures.iotlab import IOTLAB_MOCK_NODES


class IoTLabAdapter(ProviderAdapter):
    """Retrieve IoT-LAB resources and delegate normalization."""

    def __init__(
        self,
        *,
        mode: ProviderMode,
        mapper: IoTLabMapper | None = None,
        client: IoTLabClient | None = None,
        sites: list[str] | None = None,
        auto_discover_sites: bool = True,
        include_native_data: bool = False,
    ) -> None:
        self._mode = mode
        self._mapper = mapper or IoTLabMapper()
        self._client = client
        self._sites = sites or []
        self._auto_discover_sites = auto_discover_sites
        self._include_native_data = include_native_data

    @property
    def provider_info(self) -> ProviderInfo:
        enabled = self._mode != ProviderMode.DISABLED

        return ProviderInfo(
            id=ProviderId.IOTLAB,
            name="FIT IoT-LAB",
            description="Large-scale IoT experimentation testbed",
            enabled=enabled,
            mode=self._mode,
            status=(
                ProviderStatus.CONNECTED
                if enabled
                else ProviderStatus.DISABLED
            ),
            discovery_supported=True,
            availability_supported=True,
            provisioning_supported=False,
            authentication_type="HTTP Basic Authentication",
            capabilities=[
                "iot-devices",
                "experiment-reservations",
                "firmware-deployment",
                "energy-monitoring",
                "radio-monitoring",
            ],
        )
    async def _fetch_native_response(
        self,
    ) -> dict[str, Any]:
        if self._mode == ProviderMode.MOCK:
            return {
                "version": "mock-iotlab-v1",
                "items": IOTLAB_MOCK_NODES,
            }

        if self._client is None:
            raise RuntimeError(
                "An IoTLabClient is required "
                "in live mode."
            )

        site_ids = await self._resolve_sites()

        native_response = (
            await self._client.get_nodes_for_sites(
                site_ids
            )
        )

        return native_response
    
    async def _resolve_sites(self) -> list[str]:
        if self._mode == ProviderMode.MOCK:
            return self._sites

        if not self._auto_discover_sites:
            if not self._sites:
                raise RuntimeError(
                    "No IoT-LAB sites were configured."
                )

            return self._sites

        if self._client is None:
            raise RuntimeError(
                "An IoTLabClient is required for "
                "automatic IoT-LAB site discovery."
            )

        site_ids = await self._client.discover_site_ids()

        if not site_ids:
            raise RuntimeError(
                "IoT-LAB site discovery returned "
                "no sites."
            )

        return site_ids

    async def discover_resources(
        self,
    ) -> list[NormalizedResource]:
        native_response = (
            await self._fetch_native_response()
        )
        #print(">>> IoTLabAdapter.discover_resources() called")
        raw_items = native_response.get("items")
        
        native_nodes = self._dictionary_list(
            raw_items
        )
        
        resources: list[NormalizedResource] = []
        skipped_nodes = 0
        for index, native_node in enumerate(native_nodes):
            try:
                resource = self._mapper.map_resource(
                    native_node,
                    context={
                        "inventory_version": (
                            native_response.get("version")
                        ),
                        "include_native_data": (
                            self._include_native_data
                        ),
                    },
                )

                resources.append(resource)
            except ValueError as exc:
                skipped_nodes += 1
                '''
                print(
                    "Skipping invalid IoT-LAB node:",
                    f"index={index}",
                    f"uid={native_node.get('uid')!r}",
                    f"site={native_node.get('site')!r}",
                    f"error={exc}",
                    flush=True,
                )'''
            except Exception as exc:
                print(
                    "IoT-LAB mapping failed:",
                    f"index={index}",
                    f"node={native_node}",
                    f"error={type(exc).__name__}: {exc}",
                    flush=True,
                )

                raise

        return resources
        
    def _discover_mock_resources(
        self,
    ) -> list[NormalizedResource]:
        return [
            self._mapper.map_resource(
                native_node,
                context={
                    "include_native_data": (
                        self._include_native_data
                    ),
                },
            )
            for native_node in IOTLAB_MOCK_NODES
        ]

    

    @staticmethod
    def _dictionary_list(
        value: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        return [
            item
            for item in value
            if isinstance(item, dict)
        ]