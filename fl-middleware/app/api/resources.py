from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.provider import ProviderId
from app.models.resource import (
    NormalizedResource,
    ResourceCollection,
    ResourceType,
)
from app.services import (
    InventoryService,
    get_inventory_service,
)


router = APIRouter(
    prefix="/api/v1/resources",
    tags=["Resources"],
)


@router.post(
    "/refresh",
    summary="Refresh provider resource inventory",
)
async def refresh_resources(
    providers: Annotated[
        list[ProviderId] | None,
        Query(
            description=(
                "Providers to refresh. Leave empty to refresh all."
            )
        ),
    ] = None,
    inventory: InventoryService = Depends(
        get_inventory_service
    ),
) -> dict[str, object]:
    provider_set = set(providers) if providers else None
    return await inventory.refresh(provider_set)


@router.get(
    "",
    response_model=ResourceCollection,
    summary="List normalized resources",
)
async def list_resources(
    provider: ProviderId | None = Query(default=None),
    site: str | None = Query(default=None),
    available: bool | None = Query(default=None),
    resource_type: ResourceType | None = Query(default=None),
    capability: str | None = Query(default=None),
    inventory: InventoryService = Depends(
        get_inventory_service
    ),
) -> ResourceCollection:
    resources = inventory.list_resources(
        provider=provider,
        site=site,
        available=available,
        resource_type=(
            resource_type.value
            if resource_type is not None
            else None
        ),
        capability=capability,
    )

    return ResourceCollection(
        total=len(resources),
        items=resources,
    )


@router.get(
    "/{resource_id:path}",
    response_model=NormalizedResource,
    summary="Get one normalized resource",
)
async def get_resource(
    resource_id: str,
    inventory: InventoryService = Depends(
        get_inventory_service
    ),
) -> NormalizedResource:
    resource = inventory.get_resource(resource_id)

    if resource is None:
        raise HTTPException(
            status_code=404,
            detail=f"Resource '{resource_id}' was not found.",
        )

    return resource