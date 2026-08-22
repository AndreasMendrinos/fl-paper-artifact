from fastapi import APIRouter, Depends

from app.models.provider import ProviderInfo
from app.services import (
    InventoryService,
    get_inventory_service,
)


router = APIRouter(
    prefix="/api/v1/providers",
    tags=["Providers"],
)


@router.get(
    "",
    response_model=list[ProviderInfo],
    summary="List middleware providers",
)
async def list_providers(
    inventory: InventoryService = Depends(
        get_inventory_service
    ),
) -> list[ProviderInfo]:
    return inventory.list_providers()