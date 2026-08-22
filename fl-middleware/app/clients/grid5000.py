from __future__ import annotations

import asyncio
from typing import Any

import httpx


class Grid5000Client:
    """Asynchronous client for the Grid'5000 Reference API."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout_seconds: float = 30.0,
        max_connections: int = 10,
        verify_ssl: bool = True,
    ) -> None:
        if not username.strip():
            raise ValueError(
                "Grid'5000 username must not be empty."
            )

        if not password:
            raise ValueError(
                "Grid'5000 password must not be empty."
            )

        self._base_url = base_url.rstrip("/")
        self._semaphore = asyncio.Semaphore(max_connections)

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=(username, password),
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_connections,
            ),
            verify=verify_ssl,
            headers={
                "Accept": "application/json",
                "User-Agent": "fl-resource-middleware/0.1",
            },
        )

    async def _get_json(
        self,
        path: str,
    ) -> dict[str, Any]:
        async with self._semaphore:
            response = await self._client.get(path)

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError(
                "Grid'5000 API returned a non-object "
                f"JSON response for {path!r}."
            )

        return payload
    
    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        async with self._semaphore:
            response = await self._client.post(
                path,
                data=payload,
            )

        if response.is_error:
            raise RuntimeError(
                "Grid'5000 API request failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError(
                "Grid'5000 API returned a non-object "
                f"JSON response for {path!r}."
            )

        return data
    
    async def _delete(
        self,
        path: str,
    ) -> None:
        async with self._semaphore:
            response = await self._client.delete(path)

        response.raise_for_status()

    async def create_job(
        self,
        *,
        site_id: str,
        node_name: str,
        duration_minutes: int,
        queue: str | None = None,
    ) -> dict[str, Any]:
        payload = self.build_job_payload(
            site_id=site_id,
            node_name=node_name,
            duration_minutes=duration_minutes,
            queue=queue,
        )

        return await self._post_json(
            f"/sites/{site_id}/jobs",
            payload,
        )

    async def get_job(
        self,
        *,
        site_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        return await self._get_json(
            f"/sites/{site_id}/jobs/{job_id}"
        )

    async def delete_job(
        self,
        *,
        site_id: str,
        job_id: str,
    ) -> None:
        await self._delete(
            f"/sites/{site_id}/jobs/{job_id}"
        )

    @staticmethod
    def build_job_payload(
        *,
        site_id: str,
        node_name: str,
        duration_minutes: int,
        queue: str | None = None,
    ) -> dict[str, Any]:
        if duration_minutes < 1:
            raise ValueError(
                "duration_minutes must be >= 1."
            )

        hours, minutes = divmod(
            duration_minutes,
            60,
        )

        walltime = f"{hours:02d}:{minutes:02d}:00"

        payload: dict[str, Any] = {
            "resources": (
                f"host=1,walltime={walltime}"
            ),
            "properties": (
                f"host='{node_name}'"
            ),
            "command": (
                f"sleep {duration_minutes * 60}"
            ),
            "name": "fl-middleware-allocation",
        }

        if queue is not None:
            payload["queue"] = queue

        return payload
    

    @staticmethod
    def _dictionary_items(
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items = payload.get("items")

        if not isinstance(items, list):
            return []

        return [
            item
            for item in items
            if isinstance(item, dict)
        ]

    async def get_grid_info(
        self,
    ) -> dict[str, Any]:
        return await self._get_json("/")

    async def discover_site_ids(
        self,
    ) -> list[str]:
        payload = await self._get_json("/sites")

        site_ids: list[str] = []

        for site in self._dictionary_items(payload):
            uid = str(site.get("uid", "")).strip()

            if uid:
                site_ids.append(uid)

        return sorted(set(site_ids))

    async def discover_cluster_ids(
        self,
        site_id: str,
    ) -> list[str]:
        payload = await self._get_json(
            f"/sites/{site_id}/clusters"
        )

        cluster_ids: list[str] = []

        for cluster in self._dictionary_items(payload):
            uid = str(cluster.get("uid", "")).strip()

            if uid:
                cluster_ids.append(uid)

        return sorted(set(cluster_ids))

    async def get_nodes_for_cluster(
        self,
        *,
        site_id: str,
        cluster_id: str,
    ) -> list[dict[str, Any]]:
        payload = await self._get_json(
            f"/sites/{site_id}/clusters/"
            f"{cluster_id}/nodes"
        )

        nodes: list[dict[str, Any]] = []

        for node in self._dictionary_items(payload):
            nodes.append(
                {
                    **node,
                    "_site_uid": site_id,
                    "_cluster_uid": cluster_id,
                }
            )

        return nodes

    async def get_nodes_for_site(
        self,
        site_id: str,
    ) -> list[dict[str, Any]]:
        cluster_ids = await self.discover_cluster_ids(
            site_id
        )

        cluster_results = await asyncio.gather(
            *[
                self.get_nodes_for_cluster(
                    site_id=site_id,
                    cluster_id=cluster_id,
                )
                for cluster_id in cluster_ids
            ]
        )

        return [
            node
            for cluster_nodes in cluster_results
            for node in cluster_nodes
        ]

    async def get_nodes_for_sites(
        self,
        site_ids: list[str],
    ) -> dict[str, Any]:
        grid_info = await self.get_grid_info()

        site_results = await asyncio.gather(
            *[
                self.get_nodes_for_site(site_id)
                for site_id in site_ids
            ]
        )

        nodes = [
            node
            for site_nodes in site_results
            for node in site_nodes
        ]

        return {
            "items": nodes,
            "version": grid_info.get("version"),
            "sites": site_ids,
        }

    async def close(
        self,
    ) -> None:
        await self._client.aclose()