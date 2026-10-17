from fastapi import HTTPException
from mysql.connector.errors import IntegrityError

from app.db.connection import get_connection

from app.Models.instrument_models import (
    AddInstrumentRequest,
    UpdateInstrumentRequest,
    InstrumentResponse
)

from app.db.queries.instrument_queries import (
    ADD_INSTRUMENT,
    UPDATE_INSTRUMENT,
    DELETE_INSTRUMENT
)

from app.utils.instruments import (
    _validate_category,
    _validate_price,
    _check_symbol_unique,
    _get_instruments,
    _get_instrument_by_id
)

from app.services.pagination_service import PaginationRequest


def _build_instrument_response(instrument: dict) -> InstrumentResponse:
    return InstrumentResponse(
        id=instrument["id"],
        symbol=instrument["symbol"],
        name=instrument["name"],
        category_id=instrument["category_id"],
        category=instrument["category"],
        current_price=instrument["current_price"],
        is_active=bool(instrument["is_active"]),
        created_at=instrument["created_at"],
        updated_at=instrument["updated_at"]
    )


def get_instruments(
    limit: int = 10,
    offset: int = 0,
    is_active: bool | None = None
):
    """
    Admin function to list paginated instruments, including inactive
    ones unless filtered by is_active.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        pagination = PaginationRequest(_get_instruments)

        instruments = pagination.runCallback(
            cursor=cursor,
            limit=limit,
            offset=offset,
            is_active=is_active
        )

        return [_build_instrument_response(i) for i in instruments]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def add_instrument(data: AddInstrumentRequest):
    """
    Admin function to add a new instrument.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        _validate_category(cursor, data.category_id)
        _validate_price(data.current_price)
        _check_symbol_unique(cursor, data.symbol)

        try:
            cursor.execute(ADD_INSTRUMENT, (
                data.symbol,
                data.name,
                data.category_id,
                data.current_price
            ))
        except IntegrityError as e:
            raise HTTPException(
                status_code=409,
                detail="Instrument symbol already in use."
            ) from e

        instrument_id = cursor.lastrowid

        response = _build_instrument_response(
            _get_instrument_by_id(cursor, instrument_id))

        conn.commit()

        return response

    except HTTPException:
        if conn is not None:
            conn.rollback()
        raise
    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def update_instrument(instrument_id: int, data: UpdateInstrumentRequest):
    """
    Admin function to update an instrument. Provided fields are merged
    with the current row, so is_active toggles through this endpoint.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        current = _get_instrument_by_id(cursor, instrument_id)

        new_symbol = data.symbol if data.symbol is not None else current["symbol"]
        new_name = data.name if data.name is not None else current["name"]
        new_category = data.category_id if data.category_id is not None else current["category_id"]
        new_price = data.current_price if data.current_price is not None else current["current_price"]
        new_active = data.is_active if data.is_active is not None else bool(current["is_active"])

        if data.category_id is not None:
            _validate_category(cursor, new_category)
        if data.current_price is not None:
            _validate_price(new_price)
        if data.symbol is not None:
            _check_symbol_unique(cursor, new_symbol, exclude_id=instrument_id)

        try:
            cursor.execute(UPDATE_INSTRUMENT, (
                new_symbol,
                new_name,
                new_category,
                new_price,
                new_active,
                instrument_id
            ))
        except IntegrityError as e:
            raise HTTPException(
                status_code=409,
                detail="Instrument symbol already in use."
            ) from e

        response = _build_instrument_response(
            _get_instrument_by_id(cursor, instrument_id))

        conn.commit()

        return response

    except HTTPException:
        if conn is not None:
            conn.rollback()
        raise
    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def delete_instrument(instrument_id: int):
    """
    Admin function to soft delete an instrument by setting
    is_active to FALSE. Trade history is preserved.
    Idempotent: deleting an inactive instrument returns it as-is.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        _get_instrument_by_id(cursor, instrument_id)

        cursor.execute(DELETE_INSTRUMENT, (instrument_id,))
        conn.commit()

        return _build_instrument_response(
            _get_instrument_by_id(cursor, instrument_id))

    except HTTPException:
        if conn is not None:
            conn.rollback()
        raise
    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
