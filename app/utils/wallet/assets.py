from fastapi import HTTPException
from app.db.queries.asset_queries import GET_ASSET


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
