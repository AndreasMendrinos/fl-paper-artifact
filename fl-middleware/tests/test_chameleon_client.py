import httpx
import pytest

from app.clients.chameleon import ChameleonClient
from app.clients.base import ProviderResponseError


@pytest.mark.asyncio
async def test_get_sites() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == "/sites"

        return httpx.Response(
            status_code=200,
            json={
                "total": 1,
                "items": [
                    {
                        "uid": "tacc",
                        "name": "CHI@TACC",
                        "location": "Austin, Texas, USA",
                        "site_class": "baremetal",
                        "version": "version-1",
                    }
                ],
                "version": "version-1",
            },
        )

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    response = await client.get_sites()

    assert response["total"] == 1
    assert response["items"][0]["uid"] == "tacc"


@pytest.mark.asyncio
async def test_discover_site() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        if request.url.path == "/sites/tacc":
            return httpx.Response(
                status_code=200,
                json={
                    "uid": "tacc",
                    "name": "CHI@TACC",
                    "location": "Austin, Texas, USA",
                    "site_class": "baremetal",
                    "version": "version-2",
                },
            )

        if (
            request.url.path
            == "/sites/tacc/clusters/chameleon/nodes"
        ):
            return httpx.Response(
                status_code=200,
                json={
                    "total": 1,
                    "version": "version-2",
                    "items": [
                        {
                            "uid": "node-1",
                            "architecture": {
                                "platform_type": "x86_64"
                            },
                            "processors": [
                                {
                                    "model": "Test CPU",
                                    "nb_cores": 16,
                                }
                            ],
                            "main_memory": {
                                "ram_size": 68719476736
                            },
                            "storage_devices": [],
                            "network_adapters": [],
                            "gpu_devices": [],
                        }
                    ],
                },
            )

        return httpx.Response(status_code=404)

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    response = await client.discover_site(
        site_id="tacc",
        cluster_id="chameleon",
    )

    assert response["site"]["uid"] == "tacc"
    assert response["version"] == "version-2"
    assert len(response["items"]) == 1
    assert response["items"][0]["uid"] == "node-1"


@pytest.mark.asyncio
async def test_invalid_json_shape() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json=["not", "an", "object"],
        )

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderResponseError):
        await client.get_sites()


@pytest.mark.asyncio
async def test_http_error() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=503,
            json={"detail": "temporarily unavailable"},
        )

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderResponseError):
        await client.get_sites()


@pytest.mark.asyncio
async def test_discover_baremetal_sites() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == "/sites"

        return httpx.Response(
            status_code=200,
            json={
                "total": 4,
                "version": "test-version",
                "items": [
                    {
                        "uid": "tacc",
                        "name": "CHI@TACC",
                        "site_class": "baremetal",
                    },
                    {
                        "uid": "uc",
                        "name": "CHI@UC",
                        "site_class": "baremetal",
                    },
                    {
                        "uid": "kvm",
                        "name": "KVM@TACC",
                        "site_class": "kvm",
                    },
                    {
                        "uid": "edge",
                        "name": "CHI@Edge",
                        "site_class": "edge",
                    },
                ],
            },
        )

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    site_ids = await client.discover_site_ids(
        allowed_site_classes={"baremetal"}
    )

    assert site_ids == ["tacc", "uc"]


@pytest.mark.asyncio
async def test_discover_all_site_ids() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "items": [
                    {
                        "uid": "tacc",
                        "site_class": "baremetal",
                    },
                    {
                        "uid": "edge",
                        "site_class": "edge",
                    },
                ],
            },
        )

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    site_ids = await client.discover_site_ids()

    assert site_ids == ["tacc", "edge"]

@pytest.mark.asyncio
async def test_discover_cluster_ids() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.url.path
            == "/sites/tacc/clusters"
        )

        return httpx.Response(
            status_code=200,
            json={
                "items": [
                    {"uid": "cluster-a"},
                    {"uid": "cluster-b"},
                    {"uid": "cluster-a"},
                ],
            },
        )

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    cluster_ids = await client.discover_cluster_ids(
        site_id="tacc"
    )

    assert cluster_ids == [
        "cluster-a",
        "cluster-b",
    ]

@pytest.mark.asyncio
async def test_discover_cluster_ids_supports_fallback_fields(
) -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "items": [
                    {"id": "cluster-by-id"},
                    {"name": "cluster-by-name"},
                    {},
                ],
            },
        )

    client = ChameleonClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    cluster_ids = await client.discover_cluster_ids(
        site_id="tacc"
    )

    assert cluster_ids == [
        "cluster-by-id",
        "cluster-by-name",
    ]

