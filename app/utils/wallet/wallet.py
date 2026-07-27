from decimal import Decimal
from fastapi import HTTPException

from app.db.queries.wallet_queries import (
    INSERT_WALLET,
    CONSUME_LOCKED_FUNDS,
    CREDIT_AVAILABLE_BALANCE,
    GET_WALLET,
    DEBIT_AVAILABLE_BALANCE,
    UNLOCK_FUNDS,
    LOCK_FUNDS,
)


def _create_wallet(cursor, user_id: int):
    """
    Create wallet for a user.
    """

    cursor.execute(INSERT_WALLET, (user_id,))


def _validate_amount(amount: Decimal):
    """
    Validates amount.
    """

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero."
        )


def _get_wallet(cursor, user_id: int):
    """
    Fetches a user wallet or raises 404.
    """

    cursor.execute(GET_WALLET, (user_id,))
    wallet = cursor.fetchone()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found."
        )

    return wallet


def _credit_available(
    cursor,
    user_id,
    amount
):
    """
    Credits a user wallet.
    """
    cursor.execute(CREDIT_AVAILABLE_BALANCE, (amount, user_id,))


def _debit_available(
    cursor,
    user_id,
    buy_cost
):
    """
    Validates buy cost against wallet available funds and debits cost price,
    throw 400 error if insufficient funds
    """
    cursor.execute(DEBIT_AVAILABLE_BALANCE, (buy_cost, user_id, buy_cost))

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail='Insufficient funds'
        )


def _lock_funds(
    cursor,
    user_id,
    amount
):
    """
    Locks funds in a user's wallet.
    """
    cursor.execute(LOCK_FUNDS, (amount, amount, user_id,))


def _unlock_funds(
    cursor,
    user_id,
    amount
):
    """
    Unlocks funds in a user's wallet.
    """
    cursor.execute(UNLOCK_FUNDS, (amount, amount, user_id,))


def _consume_lock_funds(
    cursor,
    user_id,
    amount
):
    """
    Consumes locked funds.
    """
    cursor.execute(CONSUME_LOCKED_FUNDS, (amount, user_id,))
