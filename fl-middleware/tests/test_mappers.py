from app.mappers.chameleon import ChameleonMapper
from app.mappers.grid5000 import Grid5000Mapper
from app.mappers.iotlab import IoTLabMapper
from app.models.provider import ProviderId
from app.models.resource import (
    AvailabilityState,
    ResourceType,
    ResourceAvailability,
)
from app.providers.fixtures.chameleon import (
    CHAMELEON_MOCK_RESPONSE,
)
from app.providers.fixtures.grid5000 import (
    GRID5000_MOCK_RESPONSE,
)
from app.providers.fixtures.iotlab import IOTLAB_MOCK_NODES


def test_iotlab_mapper() -> None:
    mapper = IoTLabMapper()

    resource = mapper.map_resource(
        IOTLAB_MOCK_NODES[0]
    )

    assert resource.provider == ProviderId.IOTLAB
    #assert resource.id == "iotlab:grenoble:a8-103"
    assert resource.id == "iotlab:grenoble:103"
    assert resource.name == "a8-103.grenoble.iot-lab.info"
    assert resource.resource_type == ResourceType.IOT_DEVICE
    assert resource.hardware.architecture == "armv7l"
    assert resource.runtime.numpy is True
    assert resource.runtime.flower_native is False
    assert resource.runtime.proxy_required is True
    assert (
        resource.availability.state
        == AvailabilityState.AVAILABLE
    )
    #assert "energy-monitoring" in resource.capabilities
    assert (
        "power-consumption-monitoring"
        in resource.capabilities
    )
    assert "radio-sniffing" in resource.capabilities

def test_iotlab_mapper_maps_busy_state() -> None:
    mapper = IoTLabMapper()

    native_node = {
        **IOTLAB_MOCK_NODES[0],
        "state": "Busy",
    }

    resource = mapper.map_resource(native_node)

    assert (
        resource.availability.state
        == AvailabilityState.UNAVAILABLE
    )
    '''
    assert (
        resource.availability.state
        == ResourceAvailability.UNAVAILABLE
    )

    assert (
        resource.availability.state
        == ResourceAvailability.AVAILABLE
    )
    '''

def test_chameleon_mapper() -> None:
    mapper = ChameleonMapper()

    site = CHAMELEON_MOCK_RESPONSE["site"]
    assert isinstance(site, dict)

    items = CHAMELEON_MOCK_RESPONSE["items"]
    assert isinstance(items, list)

    resource = mapper.map_resource(
        items[0],
        context={
            "site_uid": site["uid"],
            "site_location": site["location"],
            "site_class": site["site_class"],
            "inventory_version": (
                CHAMELEON_MOCK_RESPONSE["version"]
            ),
        },
    )
    print(items[0].keys())
    assert resource.provider == ProviderId.CHAMELEON
    assert resource.id == (
        "chameleon:tacc:mock-node-tacc-001"
    )
    assert resource.resource_type == ResourceType.BARE_METAL
    assert resource.hardware.cpu_cores == 16
    assert resource.hardware.memory_mb == 131072
    assert resource.hardware.gpu_count == 0
    assert resource.network.bandwidth_mbps == 10000
    assert (
        resource.availability.state
        == AvailabilityState.UNKNOWN
    )
    '''
    assert (
        resource.availability.state
        == ResourceAvailability.UNKNOWN
    )
    '''
    assert resource.resource_type == "bare-metal"
    assert resource.native_resource_type is not None


def test_grid5000_mapper() -> None:
    mapper = Grid5000Mapper()

    items = GRID5000_MOCK_RESPONSE["items"]
    assert isinstance(items, list)

    resource = mapper.map_resource(
        items[0],
        context={
            "site_uid": GRID5000_MOCK_RESPONSE[
                "site_uid"
            ],
            "cluster_uid": GRID5000_MOCK_RESPONSE[
                "cluster_uid"
            ],
        },
    )

    assert resource.provider == ProviderId.GRID5000
    assert resource.id == "grid5000:grenoble:dahu-1"
    assert resource.resource_type == ResourceType.BARE_METAL
    assert resource.hardware.cpu_cores == 16
    assert resource.hardware.memory_mb == 131072
    assert resource.network.public_ipv6 is True
    assert resource.labels["cluster"] == "dahu"
    assert "bare-metal-deployment" in resource.capabilities