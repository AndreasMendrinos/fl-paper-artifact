from pydantic import BaseModel, Field

from app.models.provider import ProviderId
from app.models.resource import ResourceType


class ResourceRequirements(BaseModel):
    """Provider-independent resource allocation requirements."""

    count: int = Field(default=1, ge=1)

    provider: ProviderId | None = None
    site: str | None = None
    resource_type: ResourceType | None = None

    #available: bool = True
    available: bool | None = None
    architecture: str | None = None

    min_cpu_cores: int | None = Field(
        default=None,
        ge=1,
    )
    min_memory_mb: int | None = Field(
        default=None,
        ge=1,
    )
    min_gpu_count: int | None = Field(
        default=None,
        ge=0,
    )
    native_resource_type: str | None = None

    requires_ipv4: bool | None = None
    requires_ipv6: bool | None = None
    requires_outbound_http: bool | None = None

    python_version: str | None = None

    capabilities: list[str] = Field(
        default_factory=list
    )


class ResourceAllocation(BaseModel):
    """Result of a logical resource allocation request."""

    status: str
    requested_count: int
    matched_count: int

    resources: list["NormalizedResource"]

    message: str | None = None


from app.models.resource import NormalizedResource

ResourceAllocation.model_rebuild()

class ReservationRequest(BaseModel):
    duration_minutes: int = Field(
        default=60,
        ge=1,
    )


class ReservationResult(BaseModel):
    provider: str
    resource_id: str
    status: str
    reservation_id: str | None = None
    message: str | None = None
    native_data: dict[str, object] | None = None

class AllocationReservationRequest(BaseModel):
    requirements: ResourceRequirements

    duration_minutes: int = Field(
        default=60,
        ge=1,
    )

class ReservationStatus(BaseModel):
    provider: str
    reservation_id: str
    site: str
    state: str

    assigned_resources: list[str] = Field(
        default_factory=list
    )

    connection: dict[str, object] | None = None

    native_data: dict[str, object] | None = None