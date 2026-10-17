from decimal import Decimal
from fastapi import HTTPException
from app.db.queries.instrument_queries import (
    CHECK_CATEGORY,
    CHECK_INSTRUMENT_BY_SYMBOL,
    GET_INSTRUMENTS,
    GET_INSTRUMENT_BY_ID,
)


def _validate_category(cursor, category_id: int):
    """
    checks if category exists or raises 404.
    """

    cursor.execute(CHECK_CATEGORY, (category_id,))
    category = cursor.fetchone()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found."
        )


def _validate_price(price: Decimal):
    """
    validates instrument price is positive or raises 400.
    """

    if price is None or price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Current price must be greater than zero."
        )


def _check_symbol_unique(cursor, symbol: str, exclude_id: int | None = None):
    """
    raises 409 if another instrument already uses the symbol.
    """

    cursor.execute(CHECK_INSTRUMENT_BY_SYMBOL, (symbol,))
    row = cursor.fetchone()

    if row and (exclude_id is None or row["id"] != exclude_id):
        raise HTTPException(
            status_code=409,
            detail="Instrument symbol already in use."
        )


def _get_instruments(
    cursor,
    limit: int,
    offset: int,
    is_active: bool | None = None
) -> list[dict]:
    """
    Get's paginated instruments for admin, optionally filtered by status.
    """
    cursor.execute(GET_INSTRUMENTS, (is_active, is_active, limit, offset))

    return cursor.fetchall()


def _get_instrument_by_id(cursor, instrument_id: int) -> dict:
    """
    Get's instrument by id or raise a 404 error.
    """

    cursor.execute(GET_INSTRUMENT_BY_ID, (instrument_id,))

    instrument = cursor.fetchone()

    if not instrument:
        raise HTTPException(
            status_code=404,
            detail="Instrument not found."
        )

    return instrument
