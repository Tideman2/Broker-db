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

from app.db.queries.payment_method import GET_PAYMENT_METHOD
from app.db.queries.asset_queries import GET_ASSET
from app.db.queries.deposits_queries import (
    ADD_DEPOSIT,
    GET_DEPOSIT,
    CONFIRM_DEPOSIT,
    REJECT_DEPOSIT
)

from app.Models.wallet_models import Deposit, DepositFundsResponse, DepositStatus


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


# PAYMENT METHOD HELPERS

def _validate_payment_method(cursor, method_id: int):
    """
    checks if payment method exists or raises 404.
    """

    cursor.execute(GET_PAYMENT_METHOD, (method_id,))
    payment_method = cursor.fetchone()

    if not payment_method:
        raise HTTPException(
            status_code=404,
            detail="payment method not found."
        )

    return payment_method


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


def _create_deposit_record(cursor, user_id: int, deposit: Deposit):
    """
    Creates a deposit record with status pending.
    """

    cursor.execute(ADD_DEPOSIT, (
        user_id, deposit.amount, deposit.asset_id,
        deposit.payment_method
    ))


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


def _build_deposit_response(deposit: dict) -> DepositFundsResponse:

    return DepositFundsResponse(
        id=deposit["id"],
        amount=deposit["amount"].quantize(Decimal("0.01")),
        status=DepositStatus[deposit["status"]],

        created_at=deposit["created_at"],
        confirmed_at=deposit["confirmed_at"],

        asset_id=deposit["asset_id"],
        asset_symbol=deposit["asset_symbol"],
        asset_name=deposit["asset_name"],

        payment_method_id=deposit["payment_method_id"],
        payment_method_name=deposit["payment_method_name"],
        payment_method_type=deposit["payment_method_type"],

        bank_name=deposit["bank_name"],
        account_name=deposit["account_name"],
        account_number=deposit["account_number"],
    )
