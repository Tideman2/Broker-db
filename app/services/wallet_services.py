from decimal import Decimal
from datetime import datetime, UTC
from fastapi import HTTPException

from app.db.connection import get_connection

# from app.utils.wallet_helpers import (
#     _validate_amount,
#     _validate_payment_method,
#     _get_deposit_record,
#     _validate_asset,
#     _create_deposit_record,
#     _build_deposit_response,
#     _credit_available,
#     _confirm_deposit_record,
#     _reject_deposit_record
# )

from app.utils.wallet import (
    _validate_payment_method,
    _get_deposit_record,
    _validate_asset,
    _create_deposit_record,
    _build_deposit_response,
    _credit_available,
    _confirm_deposit_record,
    _reject_deposit_record,
    _validate_amount
)

from app.Models.wallet_models import DepositFundsRequest, DepositFundsResponse


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


def submit_withdrawal(
    user_id: int,
    deposit_id: int
):
    """
    Submit funds withdrawal.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Validate balance
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
