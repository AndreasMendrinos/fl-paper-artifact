from typing import Any

import pytest
from app.models.provider import ProviderId
from app.models.provider import ProviderMode
from app.models.resource import ResourceType
from app.models.resource import AvailabilityState
from app.providers.iotlab import IoTLabAdapter
from app.providers.fixtures.iotlab import IOTLAB_MOCK_NODES
from copy import deepcopy



class FakeIoTLabClient:
    def __init__(self) -> None:
        self.get_nodes_for_sites_calls: list[
            list[str] | None
        ] = []

    async def discover_site_ids(
        self,
    ) -> list[str]:
        return [
            "grenoble",
            "lille",
        ]

    async def get_nodes_for_sites(
        self,
        site_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        self.get_nodes_for_sites_calls.append(
            site_ids
        )

        all_nodes = [
            {
                "uid": "9982",
                "archi": "m3:at86rf231",
                "site": "grenoble",
                "state": "Alive",
                "network_address": (
                    "m3-2.grenoble."
                    "iot-lab.info"
                ),
                "mobile": 0,
                "camera": 0,
                "power_consumption": 1,
                "power_control": 1,
                "radio_sniffing": 1,
                "mobility_type": " ",
                "x": "20.70",
                "y": "26.76",
                "z": "-0.04",
            },
            {
                "uid": "2001",
                "archi": "a8:at86rf231",
                "site": "lille",
                "state": "Busy",
                "network_address": (
                    "a8-1.lille.iot-lab.info"
                ),
                "mobile": 0,
                "camera": 0,
                "power_consumption": 1,
                "power_control": 1,
                "radio_sniffing": 0,
                "mobility_type": "",
                "x": "1",
                "y": "2",
                "z": "3",
            },
        ]

        if not site_ids:
            selected_nodes = all_nodes
        else:
            allowed = set(site_ids)

            selected_nodes = [
                node
                for node in all_nodes
                if node["site"] in allowed
            ]

        return {
            "version": "fake-iotlab-v1",
            "items": selected_nodes,
        }

@pytest.mark.asyncio
async def test_live_adapter_discovers_sites_automatically(
) -> None:
    client = FakeIoTLabClient()

    adapter = IoTLabAdapter(
        mode=ProviderMode.LIVE,
        client=client,  # type: ignore[arg-type]
        sites=[],
        auto_discover_sites=True,
    )

    resources = await adapter.discover_resources()

    assert len(resources) == 2

    assert {
        resource.site
        for resource in resources
    } == {
        "grenoble",
        "lille",
    }

    assert client.get_nodes_for_sites_calls == [
        ["grenoble", "lille"]
    ]

@pytest.mark.asyncio
async def test_live_adapter_uses_configured_sites(
) -> None:
    client = FakeIoTLabClient()

    adapter = IoTLabAdapter(
        mode=ProviderMode.LIVE,
        client=client,  # type: ignore[arg-type]
        sites=["grenoble"],
        auto_discover_sites=False,
    )

    resources = await adapter.discover_resources()

    assert len(resources) == 1
    assert resources[0].site == "grenoble"

    assert client.get_nodes_for_sites_calls == [
        ["grenoble"]
    ]

@pytest.mark.asyncio
async def test_live_adapter_maps_availability(
) -> None:
    client = FakeIoTLabClient()

    adapter = IoTLabAdapter(
        mode=ProviderMode.LIVE,
        client=client,  # type: ignore[arg-type]
        auto_discover_sites=True,
    )

    resources = await adapter.discover_resources()

    states_by_site = {
        resource.site: (
            resource.availability.state
        )
        for resource in resources
    }

    assert states_by_site["grenoble"] == (
        AvailabilityState.AVAILABLE
    )

    assert states_by_site["lille"] == (
        AvailabilityState.UNAVAILABLE
    )

@pytest.mark.asyncio
async def test_mock_adapter_returns_fixture_nodes(
) -> None:
    adapter = IoTLabAdapter(
        mode=ProviderMode.MOCK,
    )

    resources = await adapter.discover_resources()

    assert len(resources) == 3

    assert all(
        resource.provider == ProviderId.IOTLAB
        for resource in resources
    )

@pytest.mark.asyncio
async def test_mock_adapter_contains_available_grenoble_nodes(
) -> None:
    adapter = IoTLabAdapter(
        mode=ProviderMode.MOCK,
    )

    resources = await adapter.discover_resources()

    matching_resources = [
        resource
        for resource in resources
        if resource.site == "grenoble"
        and resource.availability.state
        == AvailabilityState.AVAILABLE
    ]

    assert len(matching_resources) == 3

class FakeIoTLabClient_2:
    def __init__(
        self,
        nodes: list[dict[str, object]] | None = None,
    ) -> None:
        self._nodes = (
            nodes
            if nodes is not None
            else [
                {
                    "uid": "101",
                    "archi": "m3:at86rf231",
                    "site": "grenoble",
                    "state": "Alive",
                    "network_address": (
                        "m3-101.grenoble.iot-lab.info"
                    ),
                    "power_consumption": 1,
                    "power_control": 1,
                    "radio_sniffing": 1,
                },
                {
                    "uid": "102",
                    "archi": "m3:at86rf231",
                    "site": "grenoble",
                    "state": "Busy",
                    "network_address": (
                        "m3-102.grenoble.iot-lab.info"
                    ),
                    "power_consumption": 1,
                    "power_control": 1,
                    "radio_sniffing": 1,
                },
            ]
        )
    async def get_nodes_for_sites(
        self,
        site_ids: list[str],
    ) -> dict[str, object]:
        allowed_sites = {
            site.strip().lower()
            for site in site_ids
        }

        nodes = [
            node
            for node in self._nodes
            if str(node.get("site", "")).lower()
            in allowed_sites
        ]

        return {
            "items": nodes,
        }

    async def discover_site_ids(
        self,
    ) -> list[str]:
        return sorted(
            {
                str(node["site"])
                for node in self._nodes
                if node.get("site")
            }
        )


@pytest.mark.asyncio
async def test_invalid_nodes_do_not_cancel_discovery(
) -> None:
    client = FakeIoTLabClient_2(
        nodes=[
            {
                "uid": "101",
                "archi": "m3:at86rf231",
                "site": "grenoble",
                "state": "Alive",
                "network_address": (
                    "m3-101.grenoble.iot-lab.info"
                ),
                "power_consumption": 1,
                "power_control": 1,
                "radio_sniffing": 1,
            },
            {
                "uid": " ",
                "archi": "rpi3:at86rf233",
                "site": "grenoble",
                "state": "Alive",
                "network_address": (
                    "rpi3-5.grenoble.iot-lab.info"
                ),
                "power_consumption": 1,
                "power_control": 1,
                "radio_sniffing": 1,
            },
        ]
    )

    adapter = IoTLabAdapter(
        mode=ProviderMode.LIVE,
        client=client,
        sites=["grenoble"],
        auto_discover_sites=False,
    )

    resources = await adapter.discover_resources()

    assert len(resources) == 1
    assert resources[0].id == "iotlab:grenoble:101"