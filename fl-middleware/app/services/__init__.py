from app.clients.chameleon import ChameleonClient
from app.clients.iotlab import IoTLabClient
from app.clients.grid5000 import Grid5000Client

from app.config import get_settings
from app.providers import (
    ChameleonAdapter,
    Grid5000Adapter,
    IoTLabAdapter,
)
from app.services.inventory import InventoryService
from app.services.matching import ResourceMatchingService
from app.models.provider import (
    ProviderId,
    ProviderMode,
)
from app.clients.chameleon_allocation import (
    ChameleonAllocationClient,
)

def _parse_comma_separated(
    value: str,
) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]

def _parse_lowercase_set(
    value: str,
) -> set[str]:
    return {
        item.strip().lower()
        for item in value.split(",")
        if item.strip()
    }

def _resolve_chameleon_site_configuration(
    value: str,
) -> tuple[bool, list[str]]:
    parsed_sites = _parse_comma_separated(value)

    auto_discover = any(
        site.lower() == "auto"
        for site in parsed_sites
    )

    if auto_discover:
        return True, []

    return False, parsed_sites

def _parse_chameleon_cluster_config(
    value: str,
) -> tuple[bool, str | None]:
    normalized = value.strip()

    if not normalized:
        return True, None

    if normalized.casefold() == "auto":
        return True, None

    return False, normalized

def _parse_site_config(
    value: str,
) -> tuple[bool, list[str]]:
    normalized = value.strip()

    if not normalized:
        return True, []

    if normalized.casefold() == "auto":
        return True, []

    sites = [
        item.strip().lower()
        for item in normalized.split(",")
        if item.strip()
    ]

    return False, list(dict.fromkeys(sites))

#def build_inventory_service() -> InventoryService:
def build_inventory_service() -> tuple[
    InventoryService,
    Grid5000Client | None,
    ChameleonAllocationClient | None,
    IoTLabClient | None,
]:
    settings = get_settings()

    chameleon_mode = ProviderMode(
        settings.chameleon_mode
    )
    iotlab_mode = ProviderMode(
        settings.iotlab_mode
    )
    grid5000_mode = ProviderMode(
        settings.grid5000_mode
    )

    (
        chameleon_auto_discover_sites,
        chameleon_sites,
    ) = _resolve_chameleon_site_configuration(
        settings.chameleon_sites
    )

    (
        auto_discover_clusters,
        configured_cluster_id,
    ) = _parse_chameleon_cluster_config(
        settings.chameleon_clusters
    )
    chameleon_client: ChameleonClient | None = None

    if chameleon_mode == ProviderMode.LIVE:
        chameleon_client = ChameleonClient(
            base_url=settings.chameleon_discovery_url,
            timeout_seconds=(
                settings.chameleon_request_timeout_seconds
            ),
            max_connections=(
                settings.chameleon_max_connections
            ),
            verify_ssl=settings.chameleon_verify_ssl,
        )

    chameleon_allocation_client: (
        ChameleonAllocationClient | None
    ) = None

    if (
        chameleon_mode == ProviderMode.LIVE
        and settings.chameleon_auth_enabled
    ):
        if not settings.chameleon_auth_url:
            raise ValueError(
                "CHAMELEON_AUTH_URL is required "
                "for Chameleon allocation."
            )

        if not settings.chameleon_application_credential_id:
            raise ValueError(
                "CHAMELEON_APPLICATION_CREDENTIAL_ID "
                "is required for Chameleon allocation."
            )

        if not settings.chameleon_application_credential_secret:
            raise ValueError(
                "CHAMELEON_APPLICATION_CREDENTIAL_SECRET "
                "is required for Chameleon allocation."
            )

        if not settings.chameleon_region_name:
            raise ValueError(
                "CHAMELEON_REGION_NAME is required "
                "for Chameleon allocation."
            )

        chameleon_allocation_client = (
            ChameleonAllocationClient(
                auth_url=settings.chameleon_auth_url,
                application_credential_id=(
                    settings.chameleon_application_credential_id
                ),
                application_credential_secret=(
                    settings.chameleon_application_credential_secret
                ),
                region_name=settings.chameleon_region_name,
                interface=settings.chameleon_interface,
            )
        )


    (
        iotlab_auto_discover_sites,
        iotlab_sites,
    ) = _parse_site_config(
        settings.iotlab_sites
    )

    iotlab_client: IoTLabClient | None = None

    if iotlab_mode == ProviderMode.LIVE:
        if not settings.iotlab_username:
            raise RuntimeError(
                "IOTLAB_USERNAME is required "
                "in live mode."
            )

        if not settings.iotlab_password:
            raise RuntimeError(
                "IOTLAB_PASSWORD is required "
                "in live mode."
            )

        iotlab_client = IoTLabClient(
            base_url=settings.iotlab_api_url,
            username=settings.iotlab_username,
            password=settings.iotlab_password,
        )
    
    grid5000_mode = (
        ProviderMode(settings.grid5000_mode)
        if settings.grid5000_enabled
        else ProviderMode.DISABLED
    )

    (
        grid5000_auto_discover_sites,
        grid5000_sites,
    ) = _parse_site_config(
        settings.grid5000_sites
    )

    grid5000_client: Grid5000Client | None = None

    if grid5000_mode == ProviderMode.LIVE:
        if not settings.grid5000_username:
            raise ValueError(
                "GRID5000_USERNAME is required "
                "when GRID5000_MODE=live."
            )

        if not settings.grid5000_password:
            raise ValueError(
                "GRID5000_PASSWORD is required "
                "when GRID5000_MODE=live."
            )

        grid5000_client = Grid5000Client(
            base_url=settings.grid5000_api_url,
            username=settings.grid5000_username,
            password=settings.grid5000_password,
            timeout_seconds=(
                settings.grid5000_request_timeout_seconds
            ),
            max_connections=(
                settings.grid5000_max_connections
            ),
            verify_ssl=settings.grid5000_verify_ssl,
        )


    adapters = [
        IoTLabAdapter(
            mode=iotlab_mode,
            client=iotlab_client,
            sites=iotlab_sites,
            auto_discover_sites=(
                iotlab_auto_discover_sites
            ),
            include_native_data=(
                settings.iotlab_include_native_data
            ),
        ),
        ChameleonAdapter(
            mode=chameleon_mode,
            client=chameleon_client,
            sites=chameleon_sites,
            auto_discover_sites=chameleon_auto_discover_sites,
            allowed_site_classes=_parse_lowercase_set(
                settings.chameleon_site_classes
            ),
            cluster_id=configured_cluster_id,
            auto_discover_clusters=auto_discover_clusters,
            include_native_data=(
                settings.chameleon_include_native_data
            ),
        ),
        Grid5000Adapter(
            mode=grid5000_mode,
            client=grid5000_client,
            sites=grid5000_sites,
            auto_discover_sites=(
            grid5000_auto_discover_sites
            ),
            include_native_data=(
                settings.grid5000_include_native_data
            ),
        ),
    ]
    print(
        "Grid5000 mode:",
        grid5000_mode,
        flush=True,
    )
    #return InventoryService(adapters=adapters)
    return (
        InventoryService(adapters=adapters),
        grid5000_client,
        chameleon_allocation_client,
        iotlab_client,
    )


#inventory_service = build_inventory_service()
(
    inventory_service,
    grid5000_client,
    chameleon_allocation_client,
    iotlab_client,
) = build_inventory_service()

print(
    "Grid5000 client:",
    type(grid5000_client).__name__
    if grid5000_client is not None
    else None,
    flush=True,
)

matching_service = ResourceMatchingService(
    inventory_service=inventory_service
)

from app.allocators.grid5000 import (
    Grid5000Allocator,
)
from app.services.allocation import (
    AllocationService,
)
from app.allocators.chameleon import ChameleonAllocator
from app.allocators.iotlab import IoTLabAllocator

settings = get_settings()

allocation_service = AllocationService(
    matching_service=matching_service,
    allocators={
        #ProviderId.GRID5000: Grid5000Allocator(),
        ProviderId.GRID5000: Grid5000Allocator(
            client=grid5000_client,
        ),
        ProviderId.CHAMELEON: ChameleonAllocator(
            client=chameleon_allocation_client,
            key_name=settings.chameleon_key_name,
            image_name=settings.chameleon_image_name,
            network_name=settings.chameleon_network_name,
            ssh_username=settings.chameleon_ssh_username,
        ),
        #ProviderId.CHAMELEON: ChameleonAllocator(
        #   client=chameleon_allocation_client,
        #),
        #ProviderId.IOTLAB: IoTLabAllocator(),
        ProviderId.IOTLAB: IoTLabAllocator(
            client=iotlab_client,
        ),
    },
)


def get_inventory_service() -> InventoryService:
    return inventory_service