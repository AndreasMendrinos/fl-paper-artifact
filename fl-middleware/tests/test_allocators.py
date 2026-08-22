from app.allocators.grid5000 import Grid5000Allocator
from app.models.allocation import ResourceRequirements
from app.models.provider import ProviderId, ProviderMode
from app.providers.grid5000 import Grid5000Adapter
from app.services.allocation import AllocationService
from app.services.inventory import InventoryService
from app.services.matching import ResourceMatchingService
import pytest
from app.providers.chameleon import ChameleonAdapter
from app.providers.iotlab import IoTLabAdapter
from app.allocators.chameleon import ChameleonAllocator
from app.allocators.iotlab import IoTLabAllocator

@pytest.mark.asyncio
async def test_grid5000_allocator_builds_plan() -> None:
    inventory_service = InventoryService(
        adapters=[
            Grid5000Adapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    resources = inventory_service.list_resources(
        provider=ProviderId.GRID5000,
    )

    assert resources

    resource = resources[0]

    allocator = Grid5000Allocator()

    result = await allocator.reserve(
        resource,
        duration_minutes=60,
    )

    assert result["status"] == "planned"
    assert result["provider"] == "grid5000"
    assert result["resource_id"] == resource.id
    assert result["site"] == resource.site
    assert result["node"] == resource.name
    assert result["duration_minutes"] == 60


@pytest.mark.asyncio
async def test_allocation_service_selects_and_plans_grid5000() -> None:
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

    allocation_service = AllocationService(
        matching_service=matching_service,
        allocators={
            ProviderId.GRID5000: Grid5000Allocator(),
        },
    )

    requirements = ResourceRequirements(
        count=1,
        provider=ProviderId.GRID5000,
        min_memory_mb=16000,
    )

    result = await allocation_service.allocate(
        requirements,
        duration_minutes=60,
    )

    assert result.status == "planned"
    assert result.provider == "grid5000"
    assert result.resource_id.startswith("grid5000:")

    assert result.native_data is not None
    assert result.native_data["duration_minutes"] == 60

@pytest.mark.asyncio
async def test_chameleon_allocator_builds_plan() -> None:
    inventory_service = InventoryService(
        adapters=[
            ChameleonAdapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    resources = inventory_service.list_resources(
        provider=ProviderId.CHAMELEON,
    )

    assert resources

    allocator = ChameleonAllocator()

    result = await allocator.reserve(
        resources[0],
        duration_minutes=60,
    )

    assert result["status"] == "planned"
    assert result["provider"] == "chameleon"
    assert result["reservation_type"] == "lease"

@pytest.mark.asyncio
async def test_iotlab_allocator_builds_plan() -> None:
    inventory_service = InventoryService(
        adapters=[
            IoTLabAdapter(
                mode=ProviderMode.MOCK,
            )
        ]
    )

    await inventory_service.refresh()

    resources = inventory_service.list_resources(
        provider=ProviderId.IOTLAB,
    )

    assert resources

    allocator = IoTLabAllocator()

    result = await allocator.reserve(
        resources[0],
        duration_minutes=60,
    )

    assert result["status"] == "planned"
    assert result["provider"] == "iotlab"
    assert result["reservation_type"] == "experiment"