from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_providers() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/providers")

    assert response.status_code == 200

    providers = response.json()
    provider_ids = {provider["id"] for provider in providers}

    assert provider_ids == {
        "iotlab",
        "chameleon",
        "grid5000",
    }


def test_initial_resource_inventory() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/resources")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 5
    assert len(body["items"]) == 5


def test_filter_iotlab_resources() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/resources",
            params={
                "provider": "iotlab",
                "site": "grenoble",
                "available": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3

    for resource in body["items"]:
        assert resource["provider"] == "iotlab"
        assert resource["site"] == "grenoble"
        assert resource["availability"]["state"] == "available"


def test_unknown_resource_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/resources/iotlab:grenoble:does-not-exist"
        )

    assert response.status_code == 404

def test_filter_unavailable_resources() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/resources",
            params={
                "available": False,
            },
        )

    assert response.status_code == 200

    body = response.json()

    for resource in body["items"]:
        assert (
            resource["availability"]["state"]
            == "unavailable"
        )

def test_available_false_excludes_unknown() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/resources",
            params={
                "available": False,
            },
        )

    assert response.status_code == 200

    body = response.json()

    states = {
        resource["availability"]["state"]
        for resource in body["items"]
    }

    assert "unknown" not in states

def test_allocate_iotlab_resource() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/allocations",
            json={
                "count": 1,
                "provider": "iotlab",
                "site": "grenoble",
                "resource_type": "iot-device",
                "available": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "satisfied"
    assert body["requested_count"] == 1
    assert body["matched_count"] == 1
    assert len(body["resources"]) == 1
    assert (
        body["resources"][0]["provider"]
        == "iotlab"
    )