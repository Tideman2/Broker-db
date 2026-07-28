from decimal import Decimal
from fastapi import HTTPException
from app.db.queries.withdraw_queries import (
    GET_WITHDRAWAL_DESTINATION,
    INSERT_WITHDRAWAL_RECORD,
    GET_ASSET_BY_SYMBOL,
    GET_WITHDRAWAL_RECORD
)

from app.Models.wallet_models import Deposit, Withdraw


def _validate_available_balance(amount: Decimal, available=0):
    """
    User must have sufficient available balance.
    """

    if amount > available:
        raise HTTPException(
            status_code=400,
            detail="Withdraw Amount is greater than available balance."
        )


def _get_withdraw_destination(cursor, destination_id):
    """
    Get withdraw_destination or 404 error
    """

    cursor.execute(GET_WITHDRAWAL_DESTINATION, (destination_id,))
    destination = cursor.fetchone()

    if not destination:
        raise HTTPException(
            status_code=404,
            detail="withdraw destination not found"
        )

    return destination


def _create_withdraw_record(cursor, withdraw: Withdraw):
    """
    To add withdraw record to db.
    """

    cursor.execute(INSERT_WITHDRAWAL_RECORD,
                   (withdraw.user_id, withdraw.asset_id,
                    withdraw.destination_id, withdraw.amount,))
    destination = cursor.fetchone()

    if not destination:
        raise HTTPException(
            status_code=404,
            detail="Could not add withdraw record"
        )

    return destination


def _get_asset_by_symbol(cursor, symbol: str):
    """
    Fetch an asset by symbol or raise 404.
    """

    cursor.execute(GET_ASSET_BY_SYMBOL, (symbol,))
    asset = cursor.fetchone()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{symbol}' not found."
        )

    return asset


def _get_withdrawal_record(cursor, withdrawal_id: int):
    """
    Fetch withdraw record or raise 404.
    """

    cursor.execute(GET_WITHDRAWAL_RECORD, (withdrawal_id,))
    asset = cursor.fetchone()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Withdraw record '{withdrawal_id}' not found."
        )

    return asset
