from fastapi import HTTPException
from app.db.queries.asset_queries import (
    GET_ASSET,
    GET_ASSETS
)


def _validate_asset(cursor, asset_id: int):
    """
    checks if asset exists or raises 404.
    """

    cursor.execute(GET_ASSET, (asset_id,))
    asset = cursor.fetchone()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found."
        )


def _get_assets(cursor):
    """
    Fetch all assets.
    """

    cursor.execute(GET_ASSETS)
    assets = cursor.fetchall()

    if not assets:
        raise HTTPException(
            status_code=404,
            detail="No assets found."
        )

    return assets


def _get_asset_by_id(cursor, asset_id: int):
    cursor.execute(
        """
        SELECT *
        FROM assets
        WHERE id = %s
        """,
        (asset_id,)
    )

    asset = cursor.fetchone()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{asset_id}' not found."
        )

    return asset
