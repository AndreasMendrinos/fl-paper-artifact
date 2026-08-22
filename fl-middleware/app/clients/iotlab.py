from __future__ import annotations

from typing import Any

import httpx
import json

class IoTLabClientError(RuntimeError):
    """Raised when communication with the IoT-LAB API fails."""


class IoTLabAuthenticationError(IoTLabClientError):
    """Raised when IoT-LAB rejects the supplied credentials."""


class IoTLabClient:
    def __init__(
        self,
        *,
        base_url: str = "https://www.iot-lab.info/api",
        username: str,
        password: str,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        normalized_path = (
            path if path.startswith("/") else f"/{path}"
        )

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                auth=(
                    self._username,
                    self._password,
                ),
                timeout=self._timeout_seconds,
                transport=self._transport,
                headers={
                    "Accept": "application/json",
                },
            ) as client:
                response = await client.get(
                    normalized_path,
                    params=params,
                )

        except httpx.TimeoutException as exc:
            raise IoTLabClientError(
                "The IoT-LAB API request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise IoTLabClientError(
                "Could not communicate with the "
                "IoT-LAB API."
            ) from exc

        if response.status_code in {401, 403}:
            raise IoTLabAuthenticationError(
                "IoT-LAB authentication failed."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise IoTLabClientError(
                "IoT-LAB API returned "
                f"HTTP {response.status_code}: "
                f"{response.text[:300]}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise IoTLabClientError(
                "IoT-LAB returned a non-JSON response."
            ) from exc

        if not isinstance(payload, dict):
            raise IoTLabClientError(
                "IoT-LAB returned an unexpected "
                "top-level response type."
            )

        return payload

    async def get_nodes(
        self,
    ) -> dict[str, Any]:
        return await self._get_json("/nodes")

    async def discover_site_ids(self) -> list[str]:
        """
        Discover the IoT-LAB sites represented in the node inventory.
        """

        payload = await self.get_nodes()
        nodes = self.extract_items(payload)

        site_ids = {
            str(node["site"]).strip().lower()
            for node in nodes
            if node.get("site")
        }

        return sorted(
            site_id
            for site_id in site_ids
            if site_id
        )

    async def get_nodes_for_sites(
        self,
        site_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = await self.get_nodes()

        if not site_ids:
            return payload

        allowed_sites = {
            str(site_id).strip().lower()
            for site_id in site_ids
            if str(site_id).strip()
        }

        nodes = self.extract_items(payload)

        filtered_nodes = [
            node
            for node in nodes
            if str(node.get("site", "")).strip().lower()
            in allowed_sites
        ]

        return {
            **payload,
            "items": filtered_nodes,
        }

    async def _post_experiment(
        self,
        experiment: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                auth=(
                    self._username,
                    self._password,
                ),
                timeout=self._timeout_seconds,
                transport=self._transport,
                headers={
                    "Accept": "application/json",
                },
            ) as client:
                response = await client.post(
                    "/experiments",
                    files={
                        "experiment": (
                            None,
                            json.dumps(experiment),
                            "application/json",
                        )
                    },
                )

        except httpx.TimeoutException as exc:
            raise IoTLabClientError(
                "The IoT-LAB experiment request timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise IoTLabClientError(
                "Could not communicate with IoT-LAB."
            ) from exc

        if response.status_code in {401, 403}:
            raise IoTLabAuthenticationError(
                "IoT-LAB authentication failed."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise IoTLabClientError(
                "IoT-LAB API returned "
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            ) from exc

        payload = response.json()

        if not isinstance(payload, dict):
            raise IoTLabClientError(
                "IoT-LAB returned an unexpected response."
            )

        return payload

    async def create_experiment(
        self,
        *,
        site: str,
        architecture: str,
        count: int,
        duration_minutes: int,
    ) -> dict[str, Any]:
        if count < 1:
            raise ValueError("count must be >= 1.")

        if duration_minutes < 1:
            raise ValueError(
                "duration_minutes must be >= 1."
            )

        experiment = {
            "name": "fl-middleware-allocation",
            "duration": duration_minutes,
            "type": "alias",
            "nodes": [
                {
                    "alias": "1",
                    "nbnodes": count,
                    "properties": {
                        "archi": architecture,
                        "site": site,
                        "mobile": 0,
                    },
                }
            ],
        }

        return await self._post_experiment(
            experiment
        )

    async def get_experiment(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        return await self._get_json(
            f"/experiments/{experiment_id}"
        )

    async def get_experiment_nodes(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        return await self._get_json(
            f"/experiments/{experiment_id}/nodes"
        )

    async def delete_experiment(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        path = f"/experiments/{experiment_id}"

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                auth=(
                    self._username,
                    self._password,
                ),
                timeout=self._timeout_seconds,
                transport=self._transport,
                headers={
                    "Accept": "application/json",
                },
            ) as client:
                response = await client.delete(path)

        except httpx.RequestError as exc:
            raise IoTLabClientError(
                "Could not communicate with IoT-LAB."
            ) from exc

        if response.status_code in {401, 403}:
            raise IoTLabAuthenticationError(
                "IoT-LAB authentication failed."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise IoTLabClientError(
                "IoT-LAB API returned "
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            ) from exc

        payload = response.json()

        return (
            payload
            if isinstance(payload, dict)
            else {}
        )

    @staticmethod
    def extract_items(
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raw_items = payload.get("items")

        if not isinstance(raw_items, list):
            return []

        return [
            item
            for item in raw_items
            if isinstance(item, dict)
        ]

    