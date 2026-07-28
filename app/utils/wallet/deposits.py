from decimal import Decimal
from fastapi import HTTPException
from app.db.queries.deposits_queries import (
    ADD_DEPOSIT,
    GET_DEPOSIT,
    CONFIRM_DEPOSIT,
    REJECT_DEPOSIT
)

from app.Models.wallet_models import Deposit


def _create_deposit_record(cursor, user_id: int, deposit: Deposit):
    """
    Creates a deposit record with status pending.
    """

    cursor.execute(ADD_DEPOSIT, (
        user_id, deposit.amount, deposit.asset_id,
        deposit.payment_method
    ))


def _validate_amount(amount: Decimal):
    """
    Validates amount.
    """

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero."
        )


def _get_deposit_record(cursor, deposit_id: int):
    """
    Get's deposit from db or raise a 404 error.
    """

    cursor.execute(GET_DEPOSIT, (deposit_id, ))

    deposit = cursor.fetchone()

    if not deposit:
        raise HTTPException(
            status_code=404,
            detail="Deposit not found."
        )

    return deposit

#


def _confirm_deposit_record(cursor, confirmed_at, deposit_id: int, user_id: int):
    """
    Confirm's deposit in db or raise a 400 error.
    """

    cursor.execute(CONFIRM_DEPOSIT,  (confirmed_at, deposit_id, user_id,))

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail="Deposit is not pending or does not exist."
        )


def _reject_deposit_record(cursor, deposit_id: int, user_id: int):
    """
    Reject's deposit in db or raise a 400 error.
    """

    cursor.execute(REJECT_DEPOSIT,  (deposit_id, user_id,))

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail="Deposit is not pending or does not exist."
        )
