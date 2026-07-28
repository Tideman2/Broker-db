from decimal import Decimal
from datetime import datetime, UTC
from fastapi import HTTPException

from app.db.connection import get_connection

from app.utils.wallet import (
    _validate_payment_method,
    _get_deposit_record,
    _validate_asset,
    _create_deposit_record,
    _build_deposit_response,
    _credit_available,
    _confirm_deposit_record,
    _reject_deposit_record,
    _validate_amount,
    _get_wallet,
    _validate_available_balance,
    _lock_funds,
    _get_withdraw_destination,
    _get_asset_by_symbol,
    _create_withdraw_record,
    _get_withdrawal_record,
    _build_withdraw_response
)

from app.Models.wallet_models import (
    DepositFundsRequest,
    DepositFundsResponse,
    WithdrawFundsRequest,
    Withdraw
)

# ======================================================
# DEPOSITS
# ======================================================


def deposit_funds(
    user_id: int,
    data: DepositFundsRequest
) -> DepositFundsResponse:
    """
    Validate and begins to deposit funds.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Validate amount
        _validate_amount(data.deposit.amount)

        # check payment method
        _validate_payment_method(cursor, data.deposit.payment_method)

        # check if asset exists
        _validate_asset(cursor, data.deposit.asset_id)

        # Begin deposit flow, create deposit record
        _create_deposit_record(
            cursor,
            user_id,
            data.deposit
        )

        deposit_id = cursor.lastrowid

        # Build response
        deposit = _get_deposit_record(cursor, deposit_id)

        conn.commit()

        return _build_deposit_response(deposit=deposit)

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


def confirm_deposit(
    user_id: int,
    deposit_id: int
):
    """
    Confirms deposit.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # confirm deposit
        confirmed_at = datetime.now(UTC)
        _confirm_deposit_record(cursor, confirmed_at, deposit_id, user_id)

        # Get confirmed deposit
        deposit = _get_deposit_record(cursor, deposit_id)

        # Credit wallet
        amount = deposit["amount"].quantize(Decimal("0.01"))
        _credit_available(cursor, user_id, amount)

        conn.commit()

        return _build_deposit_response(deposit)

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


def reject_deposit(
    user_id: int,
    deposit_id: int
):
    """
    Rejects deposit.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        _reject_deposit_record(cursor, deposit_id, user_id)

        deposit = _get_deposit_record(cursor, deposit_id)

        conn.commit()
        return _build_deposit_response(deposit)

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


# ======================================================
# WITHDRAWALS
# ======================================================

def submit_withdrawal(
    user_id: int,
    request: WithdrawFundsRequest
):
    """
    Submit funds withdrawal.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        wallet = _get_wallet(cursor, user_id)

        # Validate balance
        _validate_available_balance(request.amount, wallet["available"])

        # Increase locked balance and reduce available balance
        _lock_funds(cursor, user_id, request.amount)

        # Get withdraw destination
        destination = _get_withdraw_destination(cursor, request.destination_id)

        if destination["asset_id"] is None:
            asset = _get_asset_by_symbol(cursor, "USDT")
            asset_id = asset["id"]
        else:
            asset_id = destination["asset_id"]

        # create withdrawal record
        withdraw = Withdraw(
            withdraw=Withdraw(
                user_id=user_id,
                asset_id=asset_id,
                destination_id=request.destination_id,
                amount=request.amount,
            )
        )

        _create_withdraw_record(cursor, withdraw)
        withdraw_id = cursor.lastrowid
        withdraw = _get_withdrawal_record(cursor, withdraw_id)
        conn.commit()

        return _build_withdraw_response(withdraw)

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
