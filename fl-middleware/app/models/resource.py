from datetime import datetime, timezone
from enum import StrEnum
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.provider import ProviderId


class ResourceType(StrEnum):
    IOT_DEVICE = "iot-device"
    BARE_METAL = "bare-metal"
    VIRTUAL_MACHINE = "virtual-machine"
    GPU_NODE = "gpu-node"
    EDGE_DEVICE = "edge-device"
    UNKNOWN = "unknown"


class AvailabilityState(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"

class AvailabilityConfidence(StrEnum):
    OBSERVED = "observed"
    ESTIMATED = "estimated"
    DECLARED = "declared"
    UNKNOWN = "unknown"


class HardwareInfo(BaseModel):
    architecture: str | None = None
    cpu_model: str | None = None
    cpu_cores: int | None = Field(default=None, ge=1)
    memory_mb: int | None = Field(default=None, ge=0)
    gpu_count: int | None = Field(default=None, ge=0)
    gpu_model: str | None = None
    storage_gb: float | None = Field(default=None, ge=0)


class NetworkInfo(BaseModel):
    public_ipv4: bool | None = None
    public_ipv6: bool | None = None
    outbound_http: bool | None = None
    bandwidth_mbps: float | None = Field(default=None, ge=0)


class RuntimeInfo(BaseModel):
    python_version: str | None = None
    numpy: bool | None = None
    pytorch: bool | None = None
    flower_native: bool | None = None
    proxy_required: bool | None = None


class AvailabilityInfo(BaseModel):
    state: AvailabilityState = AvailabilityState.UNKNOWN
    confidence: AvailabilityConfidence = AvailabilityConfidence.UNKNOWN
    source: str | None = None
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ResourceSource(BaseModel):
    adapter: str
    native_id: str
    inventory_version: str | None = None
    native_data: dict[str, Any] | None = None

class ResourceAvailability(BaseModel):
    state: AvailabilityState = AvailabilityState.UNKNOWN

class NormalizedResource(BaseModel):
    """Provider-independent representation of a resource."""

    id: str = Field(
        min_length=3,
        examples=["iotlab:grenoble:a8-103"],
    )

    provider: ProviderId

    name: str
    site: str
    location: str | None = None

    resource_type: ResourceType

    native_resource_type: str | None = None

    hardware: HardwareInfo = Field(default_factory=HardwareInfo)
    network: NetworkInfo = Field(default_factory=NetworkInfo)
    runtime: RuntimeInfo = Field(default_factory=RuntimeInfo)
    
    availability: ResourceAvailability = Field(
        default_factory=ResourceAvailability
    )

    capabilities: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)

    source: ResourceSource

    @model_validator(mode="after")
    def validate_resource_id(self) -> "NormalizedResource":
        expected_prefix = f"{self.provider.value}:"

        if not self.id.startswith(expected_prefix):
            raise ValueError(
                f"Resource id must start with '{expected_prefix}'"
            )

        return self


class ResourceCollection(BaseModel):
    total: int
    items: list[NormalizedResource]