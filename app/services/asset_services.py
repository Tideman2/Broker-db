from fastapi import HTTPException
from app.db.connection import get_connection

from app.utils.wallet import (
    _get_assets,
    _get_asset_by_id
)
from app.Models.asset_models import (
    AddAssetRequest,
    UpdateAssetRequest,
)

from app.db.queries.asset_queries import (
    ADD_ASSET,
    DELETE_ASSET,
    UPDATE_ASSET
)

from app.utils.wallet import (
    _build_assets_response,
    _build_asset_response,
    _build_delete_asset_response
)


def get_assets():
    """
    Get all assets.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        assets = _get_assets(cursor)

        return _build_assets_response(assets)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def add_asset(asset: AddAssetRequest):
    """
    Add a new asset.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            ADD_ASSET,
            (
                asset.symbol,
                asset.name,
                asset.address,
                asset.is_active,
            )
        )

        asset_id = cursor.lastrowid
        conn.commit()

        created_asset = _get_asset_by_id(
            cursor,
            asset_id
        )

        return _build_asset_response(created_asset)

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def update_asset(
    asset_id: int,
    asset: UpdateAssetRequest
):
    """
    Update an existing asset.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            UPDATE_ASSET,
            (
                asset.symbol,
                asset.name,
                asset.address,
                asset.is_active,
                asset_id,
            )
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Asset '{asset_id}' not found."
            )

        conn.commit()

        updated_asset = _get_asset_by_id(
            cursor,
            asset_id
        )

        return _build_asset_response(updated_asset)

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def delete_asset(asset_id: int):
    """
    Delete an asset.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            DELETE_ASSET,
            (asset_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Asset '{asset_id}' not found."
            )

        conn.commit()

        return _build_delete_asset_response(asset_id)

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()
