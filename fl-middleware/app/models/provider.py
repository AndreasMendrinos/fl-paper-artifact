from enum import StrEnum

from pydantic import BaseModel, Field


class ProviderId(StrEnum):
    IOTLAB = "iotlab"
    CHAMELEON = "chameleon"
    GRID5000 = "grid5000"


class ProviderMode(StrEnum):
    MOCK = "mock"
    LIVE = "live"
    DISABLED = "disabled"


class ProviderStatus(StrEnum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    DISABLED = "disabled"


class ProviderInfo(BaseModel):
    """Metadata describing a testbed provider adapter."""

    id: ProviderId
    name: str
    description: str

    enabled: bool
    mode: ProviderMode
    status: ProviderStatus

    discovery_supported: bool = True
    availability_supported: bool = False
    provisioning_supported: bool = False

    authentication_type: str | None = None
    capabilities: list[str] = Field(default_factory=list)

    last_error: str | None = None