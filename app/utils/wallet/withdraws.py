from decimal import Decimal
from fastapi import HTTPException
from app.db.queries.withdraw_queries import (
    GET_WITHDRAWAL_DESTINATION,
    INSERT_WITHDRAW_DESTINATION,
    INSERT_BANK_DESTINATION,
    INSERT_CRYPTO_DESTINATION,
    GET_WITHDRAW_DESTINATION_BY_LABEL,
    INSERT_WITHDRAWAL_RECORD,
    GET_ASSET_BY_SYMBOL,
    GET_WITHDRAWAL_RECORD,
    GET_WITHDRAWAL_RECORDS,
    GET_ALL_WITHDRAWALS,
    CONFIRM_WITHDRAWAL,
    REJECT_WITHDRAWAL,
    GET_WITHDRAWAL_DESTINATIONS,
    UPDATE_WITHDRAWAL_DESTINATION,
    UPDATE_BANK_DESTINATION,
    UPDATE_CRYPTO_DESTINATION,
    DELETE_WITHDRAWAL_DESTINATION,
    GET_WITHDRAWAL_COUNTS_FOR_DESTINATION
)

from app.Models.wallet_models import (
    Withdraw,
    DestinationType,
    BankDestination,
    CryptoDestination
)


def _validate_available_balance(amount: Decimal, available=0):
    """
    User must have sufficient available balance.
    """

    if amount > available:
        raise HTTPException(
            status_code=400,
            detail="Investment Amount is greater than available balance."
        )


def _get_withdraw_destination(cursor, destination_id, user_id=None):
    """
    Get withdraw_destination or 404 error.

    When user_id is supplied the destination must belong to that user,
    so callers cannot operate on another user's destination.
    """

    cursor.execute(GET_WITHDRAWAL_DESTINATION, (destination_id,))
    destination = cursor.fetchone()

    if not destination or (
        user_id is not None and destination["user_id"] != user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="withdraw destination not found"
        )

    return destination


def _get_withdraw_destinations(cursor, user_id):
    """
    Get withdraw_destinations or 404 error
    """

    cursor.execute(GET_WITHDRAWAL_DESTINATIONS, (user_id,))
    destinations = cursor.fetchall()

    if not destinations:
        return []

    return destinations


def _add_bank_destination(
        cursor, destination_id: int,
        bank: BankDestination
):

    cursor.execute(INSERT_BANK_DESTINATION,
                   (
                       destination_id,
                       bank.bank_name,
                       bank.account_name,
                       bank.account_number
                   )
                   )


def _validate_destination_label(cursor, label: str, user_id: int):
    """
    Check's label uniqueness or 400 error
    """
    cursor.execute(GET_WITHDRAW_DESTINATION_BY_LABEL, (label, user_id,))

    label = cursor.fetchone()

    if label:
        raise HTTPException(
            status_code=404,
            detail="Label already used"
        )


def _validate_destination_update_label(
    cursor, label: str, user_id: int, destination_id: int
):
    """
    Checks a new label does not belong to a different destination.
    """

    cursor.execute(GET_WITHDRAW_DESTINATION_BY_LABEL, (label, user_id))
    existing = cursor.fetchone()

    if existing and existing["id"] != destination_id:
        raise HTTPException(
            status_code=409,
            detail="Label already used"
        )


def _update_withdraw_destination_label(
    cursor, destination_id: int, user_id: int, label: str
):
    """
    Updates a destination label.
    """

    cursor.execute(
        UPDATE_WITHDRAWAL_DESTINATION,
        (label, destination_id, user_id)
    )


def _update_bank_destination(
    cursor, destination_id: int, user_id: int, bank: BankDestination
):
    """
    Updates a bank destination's details.
    """

    cursor.execute(
        UPDATE_BANK_DESTINATION,
        (
            bank.bank_name,
            bank.account_name,
            bank.account_number,
            destination_id,
            user_id
        )
    )


def _update_crypto_destination(
    cursor, destination_id: int, user_id: int, crypto: CryptoDestination
):
    """
    Updates a crypto destination's details.
    """

    cursor.execute(
        UPDATE_CRYPTO_DESTINATION,
        (
            crypto.address,
            crypto.asset_id,
            destination_id,
            user_id
        )
    )


def _get_destination_withdrawal_counts(cursor, destination_id: int):
    """
    Returns the total and pending withdrawal counts for a destination.
    """

    cursor.execute(
        GET_WITHDRAWAL_COUNTS_FOR_DESTINATION,
        (destination_id,)
    )

    return cursor.fetchone()


def _delete_withdraw_destination(
    cursor, destination_id: int, user_id: int
):
    """
    Deletes a destination owned by the user.
    """

    cursor.execute(
        DELETE_WITHDRAWAL_DESTINATION,
        (destination_id, user_id)
    )


def _add_crypto_destination(
        cursor, destination_id: int,
        crypto: CryptoDestination
):

    cursor.execute(INSERT_CRYPTO_DESTINATION,
                   (destination_id, crypto.asset_id,
                    crypto.address,))


def _add_withdraw_destination(
        cursor, user_id: int,
        label: str, destination_type: DestinationType,
):
    """
    Add withdraw_destination.
    """

    cursor.execute(INSERT_WITHDRAW_DESTINATION,
                   (user_id, label, destination_type,))


def _create_withdraw_record(cursor, withdraw: Withdraw):
    """
    To add withdraw record to db.
    """

    cursor.execute(INSERT_WITHDRAWAL_RECORD,
                   (withdraw.user_id, withdraw.asset_id,
                    withdraw.destination_id, withdraw.amount,))


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


def _get_user_withdrawal_records(cursor, user_id: int):
    """
    Fetch withdraw records for a user or raise 404.
    """

    cursor.execute(GET_WITHDRAWAL_RECORDS, (user_id,))
    assets = cursor.fetchall()

    if not assets:
        return []

    return assets


def _get_all_withdrawals(cursor, limit: int, offset: int, status: str | None = None):
    """
    Fetch paginated withdraw records for admin, optionally filtered by status.
    """

    cursor.execute(GET_ALL_WITHDRAWALS, (status, status, limit, offset))

    return cursor.fetchall()


def _confirm_withdrawal_record(cursor, confirmed_at, withdrawal_id: int):
    """
    Confirm's withdrawal in db or raise a 400 error.
    """

    cursor.execute(CONFIRM_WITHDRAWAL, (confirmed_at, withdrawal_id,))

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail="Withdrawal is not pending or does not exist."
        )


def _reject_withdrawal_record(cursor, withdrawal_id: int):
    """
    Reject's withdrawal in db or raise a 400 error.
    """

    cursor.execute(REJECT_WITHDRAWAL, (withdrawal_id,))

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail="Withdrawal is not pending or does not exist."
        )
