from __future__ import annotations

import httpx
import pytest

from app.clients.iotlab import (
    IoTLabAuthenticationError,
    IoTLabClient,
    IoTLabClientError,
)


@pytest.mark.asyncio
async def test_get_nodes() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/nodes"

        authorization = request.headers.get(
            "Authorization"
        )

        assert authorization is not None
        assert authorization.startswith("Basic ")

        return httpx.Response(
            status_code=200,
            json={
                "items": [
                    {
                        "uid": "2354",
                        "archi": "m3:at86rf231",
                        "site": "grenoble",
                        "state": "Alive",
                        "network_address": (
                            "m3-1.grenoble."
                            "iot-lab.info"
                        ),
                        "mobile": 0,
                        "camera": 0,
                        "x": "20.10",
                        "y": "26.76",
                        "z": "-0.04",
                    }
                ]
            },
        )

    client = IoTLabClient(
        base_url=(
            "https://www.iot-lab.info/api"
        ),
        username="test-user",
        password="test-password",
        transport=httpx.MockTransport(handler),
    )

    payload = await client.get_nodes()
    items = client.extract_items(payload)

    assert len(items) == 1
    assert items[0]["uid"] == "2354"
    assert items[0]["site"] == "grenoble"
    assert items[0]["state"] == "Alive"


@pytest.mark.asyncio
async def test_get_nodes_rejects_invalid_credentials(
) -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=401,
            json={"message": "Unauthorized"},
        )

    client = IoTLabClient(
        username="invalid",
        password="invalid",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        IoTLabAuthenticationError
    ):
        await client.get_nodes()


@pytest.mark.asyncio
async def test_get_nodes_rejects_server_error(
) -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=500,
            text="Internal Server Error",
        )

    client = IoTLabClient(
        username="test-user",
        password="test-password",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(IoTLabClientError):
        await client.get_nodes()


def test_extract_items_ignores_invalid_values(
) -> None:
    payload = {
        "items": [
            {"uid": "1"},
            "invalid",
            None,
            {"uid": "2"},
        ]
    }

    items = IoTLabClient.extract_items(payload)

    assert items == [
        {"uid": "1"},
        {"uid": "2"},
    ]


def test_extract_items_returns_empty_list(
) -> None:
    assert IoTLabClient.extract_items({}) == []
    assert (
        IoTLabClient.extract_items(
            {"items": "invalid"}
        )
        == []
    )

@pytest.mark.asyncio
async def test_discover_site_ids() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "items": [
                    {
                        "uid": "1",
                        "site": "grenoble",
                    },
                    {
                        "uid": "2",
                        "site": "lille",
                    },
                    {
                        "uid": "3",
                        "site": "grenoble",
                    },
                    {
                        "uid": "4",
                        "site": None,
                    },
                ]
            },
        )

    client = IoTLabClient(
        username="test-user",
        password="test-password",
        transport=httpx.MockTransport(handler),
    )

    site_ids = await client.discover_site_ids()

    assert site_ids == [
        "grenoble",
        "lille",
    ]

@pytest.mark.asyncio
async def test_get_nodes_for_sites() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "items": [
                    {
                        "uid": "1",
                        "site": "grenoble",
                    },
                    {
                        "uid": "2",
                        "site": "lille",
                    },
                    {
                        "uid": "3",
                        "site": "paris",
                    },
                ]
            },
        )

    client = IoTLabClient(
        username="test-user",
        password="test-password",
        transport=httpx.MockTransport(handler),
    )

    payload = await client.get_nodes_for_sites(
        ["grenoble", "paris"]
    )

    items = client.extract_items(payload)

    assert {
        item["uid"]
        for item in items
    } == {
        "1",
        "3",
    }