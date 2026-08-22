from typing import Any

from app.mappers.grid5000 import Grid5000Mapper
from app.clients.grid5000 import Grid5000Client
from app.models.provider import (
    ProviderId,
    ProviderInfo,
    ProviderMode,
    ProviderStatus,
)
from app.models.resource import NormalizedResource
from app.providers.base import ProviderAdapter
from app.providers.fixtures.grid5000 import (
    GRID5000_MOCK_RESPONSE,
)


class Grid5000Adapter(ProviderAdapter):
    """Retrieve Grid'5000 inventory and delegate normalization."""

    def __init__(
        self,
        mode: ProviderMode = ProviderMode.MOCK,
        client: Grid5000Client | None = None,
        mapper: Grid5000Mapper | None = None,
        sites: list[str] | None = None,
        auto_discover_sites: bool = True,
        include_native_data: bool = False,
    ) -> None:
        self._mode = mode
        self._client = client
        self._mapper = mapper or Grid5000Mapper()
        self._sites = sites or []
        self._auto_discover_sites = auto_discover_sites
        self._include_native_data = include_native_data

    @property
    def provider_info(self) -> ProviderInfo:
        enabled = self._mode != ProviderMode.DISABLED

        return ProviderInfo(
            id=ProviderId.GRID5000,
            name="Grid'5000",
            description=(
                "Large-scale distributed and HPC experimentation "
                "testbed"
            ),
            enabled=enabled,
            mode=self._mode,
            status=(
                ProviderStatus.CONNECTED
                if enabled
                else ProviderStatus.DISABLED
            ),
            discovery_supported=True,
            availability_supported=False,
            provisioning_supported=False,
            authentication_type="HTTP Basic Authentication",
            capabilities=[
                "bare-metal",
                "hpc",
                "job-reservations",
                "oar",
                "system-deployment",
            ],
        )
    
    async def discover_resources(
        self,
    ) -> list[NormalizedResource]:
        if self._mode == ProviderMode.DISABLED:
            return []

        native_response = await self._fetch_native_response()

        native_resources = self._dictionary_list(
            native_response.get("items")
        )

        resources: list[NormalizedResource] = []
        skipped_nodes = 0

        for index, native_node in enumerate(native_resources):
            site_uid = str(
                native_node.get("_site_uid")
                or "unknown"
            )

            cluster_uid = str(
                native_node.get("_cluster_uid")
                or native_node.get("nodeset")
                or "unknown"
            )

            try:
                resource = self._mapper.map_resource(
                    native_node,
                    context={
                        "site_uid": site_uid,
                        "cluster_uid": cluster_uid,
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

                print(
                    "Skipping invalid Grid'5000 node:",
                    f"index={index}",
                    f"uid={native_node.get('uid')!r}",
                    f"site={site_uid!r}",
                    f"cluster={cluster_uid!r}",
                    f"error={exc}",
                    flush=True,
                )

        print(
            "Mapped Grid'5000 resources:",
            len(resources),
            flush=True,
        )

        print(
            "Skipped invalid Grid'5000 nodes:",
            skipped_nodes,
            flush=True,
        )

        return resources
    
    async def _fetch_native_response(
        self,
    ) -> dict[str, Any]:
        if self._mode == ProviderMode.MOCK:
            return GRID5000_MOCK_RESPONSE

        if self._mode != ProviderMode.LIVE:
            return {
                "items": [],
            }

        if self._client is None:
            raise RuntimeError(
                "Grid5000Client is required in live mode."
            )

        if self._auto_discover_sites:
            site_ids = await self._client.discover_site_ids()
        else:
            site_ids = self._sites

        if not site_ids:
            raise RuntimeError(
                "No Grid'5000 sites were configured or discovered."
            )

        print(
            "Grid'5000 sites:",
            site_ids,
            flush=True,
        )

        native_response = (
            await self._client.get_nodes_for_sites(site_ids)
        )

        print(
            "Raw Grid'5000 nodes:",
            len(
                self._dictionary_list(
                    native_response.get("items")
                )
            ),
            flush=True,
        )

        return native_response


    @staticmethod
    def _dictionary_list(
        value: object,
    ) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        return [
            item
            for item in value
            if isinstance(item, dict)
        ]