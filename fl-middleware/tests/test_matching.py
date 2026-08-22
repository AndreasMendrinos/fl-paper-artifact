import pytest
from app.providers.grid5000 import Grid5000Adapter
from app.models.allocation import ResourceRequirements
from app.models.provider import ProviderId, ProviderMode
from app.models.resource import ResourceType
from app.providers.iotlab import IoTLabAdapter
from app.services.inventory import InventoryService
from app.services.matching import ResourceMatchingService


@pytest.mark.asyncio
async def test_allocate_iotlab_resources() -> None:
    inventory_service = InventoryService(
        adapters=[
            IoTLabAdapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    resources = inventory_service.list_resources()

    print("Inventory resources:", len(resources))

    for resource in resources:
        print(
            resource.id,
            resource.provider,
            resource.site,
            resource.resource_type,
            resource.availability.state,
        )

    matching_service = ResourceMatchingService(
        inventory_service=inventory_service
    )

    requirements = ResourceRequirements(
        count=1,
        provider=ProviderId.IOTLAB,
        site="grenoble",
        resource_type=ResourceType.IOT_DEVICE,
        available=True,
    )

    result = matching_service.allocate(requirements)

    print("Allocation status:", result.status)
    print("Matched:", result.matched_count)

    assert result.status == "satisfied"
    assert result.requested_count == 1
    assert result.matched_count == 1
    assert len(result.resources) == 1
    assert result.resources[0].provider == ProviderId.IOTLAB

@pytest.mark.asyncio
async def test_allocation_returns_partial_result() -> None:
    inventory_service = InventoryService(
        adapters=[
            IoTLabAdapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    matching_service = ResourceMatchingService(
        inventory_service=inventory_service
    )

    requirements = ResourceRequirements(
        count=100,
        provider=ProviderId.IOTLAB,
        site="grenoble",
        resource_type=ResourceType.IOT_DEVICE,
        available=True,
    )

    result = matching_service.allocate(requirements)

    assert result.status == "partial"
    assert result.requested_count == 100
    assert 0 < result.matched_count < 100
    assert len(result.resources) == result.matched_count

@pytest.mark.asyncio
async def test_allocation_returns_unsatisfied_result() -> None:
    inventory_service = InventoryService(
        adapters=[
            IoTLabAdapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    matching_service = ResourceMatchingService(
        inventory_service=inventory_service
    )

    requirements = ResourceRequirements(
        count=1,
        provider=ProviderId.IOTLAB,
        site="nonexistent-site",
        available=True,
    )

    result = matching_service.allocate(requirements)

    assert result.status == "unsatisfied"
    assert result.requested_count == 1
    assert result.matched_count == 0
    assert result.resources == []

@pytest.mark.asyncio
async def test_allocation_filters_by_memory() -> None:
    inventory_service = InventoryService(
        adapters=[
            IoTLabAdapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    matching_service = ResourceMatchingService(
        inventory_service=inventory_service
    )

    requirements = ResourceRequirements(
        count=1,
        provider=ProviderId.IOTLAB,
        min_memory_mb=200,
        available=True,
    )

    result = matching_service.allocate(requirements)

    assert result.status == "satisfied"
    assert result.resources[0].hardware.memory_mb >= 200


@pytest.mark.asyncio
async def test_best_fit_prefers_smaller_resource() -> None:
    inventory_service = InventoryService(
        adapters=[
            Grid5000Adapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    matching_service = ResourceMatchingService(
        inventory_service=inventory_service
    )

    requirements = ResourceRequirements(
        count=1,
        provider=ProviderId.GRID5000,
        min_memory_mb=16000,
    )

    eligible_resources = [
        resource
        for resource
        in inventory_service.list_resources(
            provider=ProviderId.GRID5000,
        )
        if (
            resource.hardware.memory_mb is not None
            and resource.hardware.memory_mb >= 16000
        )
    ]

    result = matching_service.allocate(
        requirements
    )

    assert result.status == "satisfied"
    assert len(result.resources) == 1

    selected = result.resources[0]

    expected_memory = min(
        resource.hardware.memory_mb
        for resource in eligible_resources
        if resource.hardware.memory_mb is not None
    )

    assert (
        selected.hardware.memory_mb
        == expected_memory
    )

@pytest.mark.asyncio
async def test_allocation_filters_by_native_resource_type() -> None:
    inventory_service = InventoryService(
        adapters=[
            IoTLabAdapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    matching_service = ResourceMatchingService(
        inventory_service=inventory_service
    )

    requirements = ResourceRequirements(
        count=1,
        provider=ProviderId.IOTLAB,
        site="grenoble",
        resource_type=ResourceType.IOT_DEVICE,
        native_resource_type="a8:at86rf231",
    )

    result = matching_service.allocate(
        requirements
    )

    assert result.matched_count >= 1

    assert all(
        resource.native_resource_type
        == "a8:at86rf231"
        for resource in result.resources
    )