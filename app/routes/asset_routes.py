from fastapi import APIRouter, Depends

from app.Models.asset_models import (
    AddAssetRequest,
    AssetResponse,
    DeleteAssetResponse,
    UpdateAssetRequest,
)

from app.services.asset_services import (
    add_asset,
    delete_asset,
    get_assets,
    update_asset,
)

from app.utils.jwt import require_admin, get_current_user


asset_router = APIRouter(
    prefix="/assets",
    tags=["Assets"]
)


@asset_router.get(
    "",
    response_model=list[AssetResponse]
)
def get_assets_endpoint(
    user=Depends(get_current_user)
):
    """
    Get all assets.
    """

    return get_assets()


@asset_router.post(
    "",
    response_model=AssetResponse
)
def add_asset_endpoint(
    request: AddAssetRequest,
    user=Depends(require_admin)
):
    """
    Add a new asset.
    """

    return add_asset(
        asset=request
    )


@asset_router.put(
    "/{asset_id}",
    response_model=AssetResponse
)
def update_asset_endpoint(
    asset_id: int,
    request: UpdateAssetRequest,
    user=Depends(require_admin)
):
    """
    Update an asset.
    """

    return update_asset(
        asset_id=asset_id,
        asset=request
    )


@asset_router.delete(
    "/{asset_id}",
    response_model=DeleteAssetResponse
)
def delete_asset_endpoint(
    asset_id: int,
    user=Depends(require_admin)
):
    """
    Delete an asset.
    """

    return delete_asset(
        asset_id=asset_id
    )
