import asyncio
from typing import Any

from app.clients.chameleon import ChameleonClient
from app.mappers.chameleon import ChameleonMapper
from app.models.provider import (
    ProviderId,
    ProviderInfo,
    ProviderMode,
    ProviderStatus,
)
from app.models.resource import NormalizedResource
from app.providers.base import ProviderAdapter
from app.providers.fixtures.chameleon import (
    CHAMELEON_MOCK_RESPONSE,
)


class ChameleonAdapter(ProviderAdapter):
    """Retrieve Chameleon inventory and delegate normalization."""

    def __init__(
        self,
        mode: ProviderMode = ProviderMode.MOCK,
        *,
        client: ChameleonClient | None = None,
        mapper: ChameleonMapper | None = None,
        sites: list[str] | None = None,
        auto_discover_sites: bool = False,
        allowed_site_classes: set[str] | None = None,
        cluster_id: str | None = None,
        auto_discover_clusters: bool = True,
        #cluster_id: str = "chameleon",
        include_native_data: bool = False,
    ) -> None:
        self._mode = mode
        self._client = client
        self._mapper = mapper or ChameleonMapper()

        self._sites = sites or []
        self._auto_discover_sites = auto_discover_sites
        self._allowed_site_classes = (
            allowed_site_classes or {"baremetal"}
        )
        self._cluster_id = cluster_id
        self._auto_discover_clusters = (
            auto_discover_clusters
        )

        self._include_native_data = include_native_data


    @property
    def provider_info(self) -> ProviderInfo:
        enabled = self._mode != ProviderMode.DISABLED

        if not enabled:
            status = ProviderStatus.DISABLED
        elif self._mode == ProviderMode.MOCK:
            status = ProviderStatus.CONNECTED
        else:
            # The inventory service may override this with DEGRADED
            # when a refresh fails.
            status = ProviderStatus.CONNECTED

        return ProviderInfo(
            id=ProviderId.CHAMELEON,
            name="Chameleon Cloud",
            description=(
                "Configurable cloud and bare-metal research testbed"
            ),
            enabled=enabled,
            mode=self._mode,
            status=status,
            discovery_supported=True,
            availability_supported=False,
            provisioning_supported=False,
            authentication_type=None,
            capabilities=[
                "bare-metal",
                "virtual-machines",
                "public-networking",
                "hardware-versioning",
                "openstack",
            ],
        )

    async def _resolve_sites(self) -> list[str]:
        """
        Resolve the sites that should participate in discovery.

        In automatic mode the list comes from the Chameleon API.
        Otherwise the configured site list is used.
        """

        if self._mode == ProviderMode.MOCK:
            return self._sites or ["tacc"]

        if not self._auto_discover_sites:
            if not self._sites:
                raise RuntimeError(
                    "No Chameleon sites were configured."
                )

            return list(dict.fromkeys(self._sites))

        if self._client is None:
            raise RuntimeError(
                "A ChameleonClient is required for "
                "automatic site discovery."
            )

        discovered_sites = await self._client.discover_site_ids(
            allowed_site_classes=self._allowed_site_classes,
        )

        if not discovered_sites:
            classes = ", ".join(
                sorted(self._allowed_site_classes)
            )

            raise RuntimeError(
                "Chameleon site discovery returned no usable "
                f"sites for classes: {classes}."
            )

        return discovered_sites

    async def discover_resources(
        self,
    ) -> list[NormalizedResource]:
        if self._mode == ProviderMode.DISABLED:
            return []

        native_responses = await self._fetch_native_responses()

        resources: list[NormalizedResource] = []

        for native_response in native_responses:
            site = self._dictionary(
                native_response.get("site")
            )
            cluster = self._dictionary(
                native_response.get("cluster")
            )
            native_nodes = self._dictionary_list(
                native_response.get("items")
            )

            context = {
                "site_uid": site.get("uid"),
                "site_name": site.get("name"),
                "site_location": site.get("location"),
                "site_class": site.get("site_class"),
                "cluster_uid": cluster.get("uid"),
                "inventory_version": (
                    native_response.get("version")
                    or site.get("version")
                ),
                "include_native_data": (
                    self._include_native_data
                ),
            }

            mapped_resources = self._mapper.map_resources(
                native_nodes,
                context=context,
            )

            resources.extend(mapped_resources)

        return resources

    async def health_check(self) -> bool:
        if self._mode == ProviderMode.DISABLED:
            return False

        if self._mode == ProviderMode.MOCK:
            return True

        if self._client is None:
            return False

        return await self._client.health_check()

    async def _fetch_native_responses(
        self,
    ) -> list[dict[str, Any]]:
        if self._mode == ProviderMode.MOCK:
            return [CHAMELEON_MOCK_RESPONSE]

        if self._mode != ProviderMode.LIVE:
            return []

        if self._client is None:
            raise RuntimeError(
                "A ChameleonClient is required in live mode."
            )
        
        site_ids = await self._resolve_sites()

        site_cluster_pairs = (
            await self._resolve_site_cluster_pairs(
                site_ids
            )
        )

        results = await asyncio.gather(
            *[
                self._client.discover_site(
                    site_id=site_id,
                    cluster_id=cluster_id,
                )
                for site_id, cluster_id
                in site_cluster_pairs
            ],
            return_exceptions=True,
        )

        successful_responses: list[dict[str, Any]] = []
        errors: list[str] = []

        for (
            site_id,
            cluster_id,
        ), result in zip(
            site_cluster_pairs,
            results,
            strict=True,
        ):
            if isinstance(result, BaseException):
                errors.append(
                    f"{site_id}/{cluster_id}: {result}"
                )
                continue

            result["cluster"] = {
                "uid": cluster_id,
            }

            successful_responses.append(result)


        if not successful_responses:
            error_details = " | ".join(errors)

            raise RuntimeError(
                "Chameleon discovery failed for every "
                f"resolved site. {error_details}"
            )

        return successful_responses

    async def _resolve_clusters(
        self,
        site_id: str,
    ) -> list[str]:
        if self._mode == ProviderMode.MOCK:
            return [self._cluster_id or "chameleon"]

        if not self._auto_discover_clusters:
            if self._cluster_id is None:
                raise ProviderAdapterError(
                    "No Chameleon cluster was configured "
                    f"for site '{site_id}'."
                )

            return [self._cluster_id]

        if self._client is None:
            raise ProviderAdapterError(
                "A ChameleonClient is required for "
                "automatic cluster discovery."
            )

        cluster_ids = await self._client.discover_cluster_ids(
            site_id=site_id
        )

        if not cluster_ids:
            raise ProviderAdapterError(
                "Chameleon cluster discovery returned "
                f"no clusters for site '{site_id}'."
            )

        return cluster_ids

    async def _resolve_site_cluster_pairs(
        self,
        site_ids: list[str],
    ) -> list[tuple[str, str]]:
        results = await asyncio.gather(
            *[
                self._resolve_clusters(site_id)
                for site_id in site_ids
            ],
            return_exceptions=True,
        )

        pairs: list[tuple[str, str]] = []
        errors: list[str] = []

        for site_id, result in zip(
            site_ids,
            results,
            strict=True,
        ):
            if isinstance(result, BaseException):
                errors.append(f"{site_id}: {result}")
                continue

            pairs.extend(
                (site_id, cluster_id)
                for cluster_id in result
            )

        if not pairs:
            detail = " | ".join(errors)

            raise ProviderAdapterError(
                "No usable Chameleon site-cluster pairs "
                f"were discovered. {detail}"
            )

        return pairs

    @staticmethod
    def _dictionary(
        value: object,
    ) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

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