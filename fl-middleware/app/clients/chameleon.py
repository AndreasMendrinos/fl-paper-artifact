import asyncio
from typing import Any

import httpx

from app.clients.base import (
    ProviderConnectionError,
    ProviderResponseError,
)


class ChameleonClient:
    """Asynchronous client for the Chameleon Resource Discovery API."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 30.0,
        max_connections: int = 10,
        verify_ssl: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections,
        )
        self._verify_ssl = verify_ssl
        self._transport = transport

    async def get_sites(self) -> dict[str, Any]:
        """Retrieve all sites visible through Resource Discovery."""

        return await self._get_json("/sites")

    async def discover_sites(
        self,
        *,
        allowed_site_classes: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Discover sites exposed by the Chameleon API.

        When allowed_site_classes is provided, only sites whose
        site_class matches one of the configured values are returned.
        """

        response = await self.get_sites()
        sites = self._extract_items(response)

        if allowed_site_classes is None:
            return sites

        normalized_classes = {
            site_class.strip().lower()
            for site_class in allowed_site_classes
            if site_class.strip()
        }

        if not normalized_classes:
            return sites

        return [
            site
            for site in sites
            if self._normalize_optional_string(
                site.get("site_class")
            )
            in normalized_classes
        ]

    async def discover_site_ids(
        self,
        *,
        allowed_site_classes: set[str] | None = None,
    ) -> list[str]:
        """Return valid site identifiers discovered from the API."""

        sites = await self.discover_sites(
            allowed_site_classes=allowed_site_classes
        )

        site_ids: list[str] = []

        for site in sites:
            site_id = site.get("uid")

            if site_id is None:
                continue

            normalized_id = str(site_id).strip()

            if not normalized_id:
                continue

            try:
                normalized_id = self._safe_path_value(
                    normalized_id
                )
            except ValueError:
                continue

            site_ids.append(normalized_id)

        # Preserve provider order while preventing duplicates.
        return list(dict.fromkeys(site_ids))

    async def get_site(self, site_id: str) -> dict[str, Any]:
        """Retrieve metadata for one site."""

        return await self._get_json(
            f"/sites/{self._safe_path_value(site_id)}"
        )

    async def get_clusters(
        self,
        site_id: str,
    ) -> dict[str, Any]:
        """Retrieve the clusters exposed by one site."""

        site_id = self._safe_path_value(site_id)

        return await self._get_json(
            f"/sites/{site_id}/clusters"
        )

    async def get_nodes(
        self,
        site_id: str,
        cluster_id: str = "chameleon",
    ) -> dict[str, Any]:
        """Retrieve physical inventory nodes for one cluster."""

        site_id = self._safe_path_value(site_id)
        cluster_id = self._safe_path_value(cluster_id)

        return await self._get_json(
            f"/sites/{site_id}/clusters/"
            f"{cluster_id}/nodes"
        )

    async def get_versions(
        self,
        site_id: str,
    ) -> dict[str, Any]:
        """Retrieve inventory versions for a site."""

        site_id = self._safe_path_value(site_id)

        return await self._get_json(
            f"/sites/{site_id}/versions"
        )

    async def discover_site(
        self,
        site_id: str,
        cluster_id: str = "chameleon",
    ) -> dict[str, Any]:
        """
        Retrieve site metadata and physical nodes.

        The returned dictionary matches the intermediate structure
        expected by the Chameleon adapter.
        """

        site_response, nodes_response = await asyncio.gather(
            self.get_site(site_id),
            self.get_nodes(site_id, cluster_id),
        )

        site = self._extract_single_item(
            site_response,
            expected_id=site_id,
        )

        nodes = self._extract_items(nodes_response)

        inventory_version = (
            nodes_response.get("version")
            or site.get("version")
            or site_response.get("version")
        )

        return {
            "version": inventory_version,
            "site": site,
            "cluster": {
                "uid": cluster_id,
            },
            "items": nodes,
        }

    async def health_check(self) -> bool:
        """Check whether the public Resource Discovery API responds."""

        try:
            response = await self.get_sites()
            return isinstance(response.get("items"), list)
        except (
            ProviderConnectionError,
            ProviderResponseError,
        ):
            return False

    async def _get_json(
        self,
        path: str,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                limits=self._limits,
                verify=self._verify_ssl,
                transport=self._transport,
                headers={
                    "Accept": "application/json",
                    "User-Agent": (
                        "fl-middleware/0.1 "
                        "chameleon-resource-client"
                    ),
                },
                follow_redirects=True,
            ) as client:
                response = await client.get(url)

            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise ProviderConnectionError(
                f"Chameleon request timed out: {url}"
            ) from exc

        except httpx.ConnectError as exc:
            raise ProviderConnectionError(
                f"Could not connect to Chameleon: {url}"
            ) from exc

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            raise ProviderResponseError(
                "Chameleon returned HTTP "
                f"{status_code} for {url}."
            ) from exc

        except httpx.HTTPError as exc:
            raise ProviderConnectionError(
                f"Chameleon HTTP request failed for {url}: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                f"Chameleon returned invalid JSON for {url}."
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderResponseError(
                "Chameleon response must be a JSON object: "
                f"{url}"
            )

        return payload
    
    async def discover_cluster_ids(
        self,
        *,
        site_id: str,
    ) -> list[str]:
        """
        Discover cluster identifiers for a Chameleon site.
        """

        response = await self.get_clusters(site_id)
        clusters = self.extract_items(response)

        cluster_ids: list[str] = []

        for cluster in clusters:
            cluster_id = (
                cluster.get("uid")
                or cluster.get("id")
                or cluster.get("name")
            )

            if cluster_id is None:
                continue

            normalized_id = str(cluster_id).strip()

            if not normalized_id:
                continue

            try:
                normalized_id = self._safe_path_value(
                    normalized_id
                )
            except ValueError:
                continue

            cluster_ids.append(normalized_id)

        return list(dict.fromkeys(cluster_ids))

    @staticmethod
    def _extract_items(
        response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items = response.get("items")

        if items is None:
            return []

        if not isinstance(items, list):
            raise ProviderResponseError(
                "Chameleon response field 'items' must be a list."
            )

        return [
            item
            for item in items
            if isinstance(item, dict)
        ]

    @classmethod
    def _extract_single_item(
        cls,
        response: dict[str, Any],
        *,
        expected_id: str,
    ) -> dict[str, Any]:
        """
        Support both possible API shapes:

        1. A direct site object.
        2. A collection containing an items array.
        """

        items = response.get("items")

        if isinstance(items, list):
            dictionaries = cls._extract_items(response)

            for item in dictionaries:
                if str(item.get("uid")) == expected_id:
                    return item

            if dictionaries:
                return dictionaries[0]

        if response.get("uid") is not None:
            return response

        raise ProviderResponseError(
            f"Chameleon site '{expected_id}' was not found."
        )

    @staticmethod
    def _safe_path_value(value: str) -> str:
        stripped = value.strip()

        if not stripped:
            raise ValueError(
                "Chameleon path value cannot be empty."
            )

        allowed = set(
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789-_"
        )

        if any(character not in allowed for character in stripped):
            raise ValueError(
                f"Unsafe Chameleon path value: {value!r}"
            )

        return stripped
    
    @staticmethod
    def _normalize_optional_string(
        value: object,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()

        return normalized or None

    @staticmethod
    def extract_items(
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract a list of records from a Chameleon API response.

        This is the public equivalent of _extract_items and is useful
        for diagnostic scripts and higher-level client operations.
        """
        return ChameleonClient._extract_items(payload)