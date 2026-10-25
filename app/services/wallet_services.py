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
    _unlock_funds,
    _consume_lock_funds,
    _get_withdraw_destination,
    _get_asset_by_symbol,
    _create_withdraw_record,
    _get_withdrawal_record,
    _confirm_withdrawal_record,
    _reject_withdrawal_record,
    _build_withdraw_response,
    _build_withdrawals_response,
    _build_paymment_methods_response,
    _get_recent_deposits,
    _get_all_deposits,
    _get_all_withdrawals,
    _build_deposits_response,
    _build_admin_deposits_response,
    _build_admin_withdrawals_response
)

from app.Models.wallet_models import (
    DepositFundsRequest,
    DepositFundsResponse,
    WithdrawFundsRequest,
    Withdraw,
    MoneyFlowItem,
    MoneyFlowResponse
)
from app.utils.wallet.withdraws import _get_user_withdrawal_records

from app.services.pagination_service import PaginationRequest

from app.db.queries.payment_method import (GET_PAYMENT_METHODS)
from app.db.queries.wallet_queries import (
    GET_LATEST_MONEY_IN,
    GET_LATEST_MONEY_OUT
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
        _confirm_deposit_record(cursor, confirmed_at, deposit_id)

        # Get confirmed deposit
        deposit = _get_deposit_record(cursor, deposit_id)

        # Credit wallet
        amount = deposit["amount"].quantize(Decimal("0.01"))
        user_id = deposit["user_id"]
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


def get_recent_deposits(user_id: int, limit: int, offset: int):
    """
    wallet service to get recent deposits
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        pagination = PaginationRequest(_get_recent_deposits)

        pagination_data = pagination.runCallback(
            cursor=cursor,
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        return _build_deposits_response(pagination_data)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def get__deposit(deposit_id):
    """
    wallet service to get a deposit
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        deposit = _get_deposit_record(cursor, deposit_id)

        return _build_deposit_response(deposit)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def reject_deposit(
    deposit_id: int
):
    """
    Rejects deposit.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        _reject_deposit_record(cursor, deposit_id)

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
        destination = _get_withdraw_destination(
            cursor, request.destination_id, user_id)

        if destination["asset_id"] is None:
            asset = _get_asset_by_symbol(cursor, "USDT")
            asset_id = asset["id"]
        else:
            asset_id = destination["asset_id"]

        # create withdrawal record
        withdraw = Withdraw(
            user_id=user_id,
            asset_id=asset_id,
            destination_id=request.destination_id,
            amount=request.amount,
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


def get_user_total_available_balance(
        user_id: int
):
    """
    Get a withdrawal record.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        wallet = _get_wallet(cursor, user_id)

        return wallet["available"]

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def get_user_withdrawals(
    user_id: int
):
    """
    Get user's withdrawal records.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        withdrawals = _get_user_withdrawal_records(cursor, user_id)

        return _build_withdrawals_response(withdrawals)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def get_a_withdraw_record(
        withdraw_id: int
):
    """
    Get a withdrawal record.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        withdraw = _get_withdrawal_record(cursor, withdraw_id)

        return _build_withdraw_response(withdraw)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


# ======================================================
# MONEY FLOW
# ======================================================

def _build_money_flow_item(row: dict, direction: str) -> MoneyFlowItem:
    """
    Normalizes a money flow query row into an API item.
    """

    return MoneyFlowItem(
        id=row["id"],
        type=row["type"],
        direction=direction,
        amount=row["amount"].quantize(Decimal("0.01")),
        asset_symbol=row["asset_symbol"],
        status=row["status"],
        occurred_at=row["occurred_at"]
    )


def get_money_flow(
    user_id: int
) -> MoneyFlowResponse:
    """
    Returns the latest four settled money movements in and out.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(GET_LATEST_MONEY_IN, (user_id, user_id))
        money_in = [
            _build_money_flow_item(row, "IN")
            for row in cursor.fetchall()
        ]

        cursor.execute(GET_LATEST_MONEY_OUT, (user_id, user_id))
        money_out = [
            _build_money_flow_item(row, "OUT")
            for row in cursor.fetchall()
        ]

        return MoneyFlowResponse(
            money_in=money_in,
            money_out=money_out
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def get_payment_methods():
    """
    Get available payment methods.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(GET_PAYMENT_METHODS)

        payment_methods = cursor.fetchall()

        if not payment_methods:
            raise HTTPException(
                status_code=404,
                detail="No payment methods found."
            )

        return _build_paymment_methods_response(payment_methods)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


# ======================================================
# ADMIN
# ======================================================


def get_all_deposits(
    limit: int,
    offset: int,
    status: str | None = None
):
    """
    Admin service to get paginated deposits, optionally filtered by status.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        pagination = PaginationRequest(_get_all_deposits)

        pagination_data = pagination.runCallback(
            cursor=cursor,
            limit=limit,
            offset=offset,
            status=status
        )

        return _build_admin_deposits_response(pagination_data)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def get_all_withdrawals(
    limit: int,
    offset: int,
    status: str | None = None
):
    """
    Admin service to get paginated withdrawals, optionally filtered by status.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        pagination = PaginationRequest(_get_all_withdrawals)

        pagination_data = pagination.runCallback(
            cursor=cursor,
            limit=limit,
            offset=offset,
            status=status
        )

        return _build_admin_withdrawals_response(pagination_data)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def confirm_withdrawal(
    withdrawal_id: int
):
    """
    Confirms withdrawal: flips status to confirmed and consumes locked funds.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        confirmed_at = datetime.now(UTC)
        _confirm_withdrawal_record(cursor, confirmed_at, withdrawal_id)

        withdrawal = _get_withdrawal_record(cursor, withdrawal_id)

        _consume_lock_funds(
            cursor, withdrawal["user_id"], withdrawal["amount"])

        conn.commit()

        return _build_withdraw_response(withdrawal)

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


def reject_withdrawal(
    withdrawal_id: int
):
    """
    Rejects withdrawal: flips status to rejected and unlocks funds to available.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        _reject_withdrawal_record(cursor, withdrawal_id)

        withdrawal = _get_withdrawal_record(cursor, withdrawal_id)

        _unlock_funds(cursor, withdrawal["user_id"], withdrawal["amount"])

        conn.commit()

        return _build_withdraw_response(withdrawal)

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
