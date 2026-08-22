from typing import Any

import pytest

from app.models.provider import ProviderMode
from app.models.resource import ResourceType
from app.providers.chameleon import ChameleonAdapter
from app.providers.fixtures.chameleon import CHAMELEON_MOCK_RESPONSE
from copy import deepcopy

class FakeChameleonClient:
    def __init__(self) -> None:
        self.discover_site_calls: list[
            tuple[str, str]
        ] = []

    async def discover_site_ids(
        self,
        *,
        allowed_site_classes: set[str] | None = None,
    ) -> list[str]:
        return ["tacc", "uc"]

    async def discover_cluster_ids(
        self,
        *,
        site_id: str,
    ) -> list[str]:
        return [f"{site_id}-cluster"]

    async def discover_site(
        self,
        *,
        site_id: str,
        cluster_id: str,
    ) -> dict:
        self.discover_site_calls.append(
            (site_id, cluster_id)
        )

        response = deepcopy(
            CHAMELEON_MOCK_RESPONSE
        )

        response["version"] = "fake-version"

        response["site"]["uid"] = site_id

        response["items"][0]["uid"] = (
            f"{site_id}-node-1"
        )

        return response


@pytest.mark.asyncio
async def test_live_chameleon_adapter() -> None:
    adapter = ChameleonAdapter(
        mode=ProviderMode.LIVE,
        client=FakeChameleonClient(),  # type: ignore[arg-type]
        sites=["tacc", "uc"],
        cluster_id="chameleon",
    )

    resources = await adapter.discover_resources()

    assert len(resources) == 2

    assert resources[0].id.startswith("chameleon:")
    assert resources[0].resource_type == ResourceType.BARE_METAL
    assert resources[0].source.inventory_version == (
        "fake-version"
    )


@pytest.mark.asyncio
async def test_live_adapter_discovers_sites_automatically(
) -> None:
    adapter = ChameleonAdapter(
        mode=ProviderMode.LIVE,
        client=FakeChameleonClient(),  # type: ignore[arg-type]
        auto_discover_sites=True,
        allowed_site_classes={"baremetal"},
        cluster_id="chameleon",
    )

    resources = await adapter.discover_resources()

    assert len(resources) == 2

    native_ids = {
        resource.source.native_id
        for resource in resources
    }

    assert native_ids == {
        "tacc-node-1",
        "uc-node-1",
    }
    assert {
        resource.source.native_id
        for resource in resources
    } == {
        "tacc-node-1",
        "uc-node-1",
    }

@pytest.mark.asyncio
async def test_live_adapter_uses_configured_sites(
) -> None:
    adapter = ChameleonAdapter(
        mode=ProviderMode.LIVE,
        client=FakeChameleonClient(),  # type: ignore[arg-type]
        sites=["tacc"],
        auto_discover_sites=False,
        cluster_id="chameleon",
    )

    resources = await adapter.discover_resources()

    assert len(resources) == 1
    assert resources[0].source.native_id == (
        "tacc-node-1"
    )


@pytest.mark.asyncio
async def test_live_adapter_discovers_clusters_automatically(
) -> None:
    client = FakeChameleonClient()

    adapter = ChameleonAdapter(
        mode=ProviderMode.LIVE,
        client=client,  # type: ignore[arg-type]
        auto_discover_sites=True,
        allowed_site_classes={"baremetal"},
        cluster_id=None,
        auto_discover_clusters=True,
    )

    resources = await adapter.discover_resources()

    assert resources

    assert set(client.discover_site_calls) == {
        ("tacc", "tacc-cluster"),
        ("uc", "uc-cluster"),
    }

    assert {
        resource.labels["cluster"]
        for resource in resources
    } == {
        "tacc-cluster",
        "uc-cluster",
    }

@pytest.mark.asyncio
async def test_live_adapter_uses_configured_cluster(
) -> None:
    client = FakeChameleonClient()

    adapter = ChameleonAdapter(
        mode=ProviderMode.LIVE,
        client=client,  # type: ignore[arg-type]
        sites=["tacc"],
        auto_discover_sites=False,
        cluster_id="manual-cluster",
        auto_discover_clusters=False,
    )

    resources = await adapter.discover_resources()

    assert resources

    assert client.discover_site_calls == [
        ("tacc", "manual-cluster")
    ]

    assert (
        resources[0].labels["cluster"]
        == "manual-cluster"
    )