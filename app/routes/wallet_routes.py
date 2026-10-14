from fastapi import APIRouter, Depends, Query

from app.utils.jwt import get_current_user, require_admin

from app.services.wallet_services import (
    deposit_funds,
    reject_deposit,
    confirm_deposit,
    submit_withdrawal,
    get_user_withdrawals,
    get_a_withdraw_record,
    get_user_total_available_balance,
    get_payment_methods,
    get__deposit,
    get_all_deposits,
    get_all_withdrawals,
    confirm_withdrawal,
    reject_withdrawal
)

from app.Models.wallet_models import (
    DepositFundsRequest,
    DepositFundsResponse,
    WithdrawFundsRequest,
    WithdrawFundsResponse,
    UserWithdrawalRecordsResponse,
    AdminDepositResponse,
    AdminWithdrawalRecordsResponse,
    DepositStatus,
    WithdrawStatus,
    PaymentMethodResponse
)


wallet_router = APIRouter(
    prefix="/wallet",
    tags=["Wallet"]
)


# ======================================================
# DEPOSIT
# ======================================================

@wallet_router.post(
    "/deposit",
    response_model=DepositFundsResponse
)
def deposit_endpoint(
    request: DepositFundsRequest,
    user=Depends(get_current_user)
):
    """
    Deposit funds.
    """
    return deposit_funds(
        user_id=user.user_id,
        data=request
    )


@wallet_router.get(
    "/payment-methods",
    response_model=list[PaymentMethodResponse]
)
def get_platform_payment_methods(
    user=Depends(get_current_user)
):
    """
    Get platform payment method.
    """
    return get_payment_methods()


@wallet_router.post(
    "/deposits/{deposit_id}/confirm",
    response_model=DepositFundsResponse
)
def confirm_deposit_endpoint(
    deposit_id: int,
    user=Depends(require_admin)
):
    """
    Confirm a deposit.
    """
    return confirm_deposit(
        deposit_id=deposit_id
    )


@wallet_router.post(
    "/deposits/{deposit_id}/reject",
    response_model=DepositFundsResponse
)
def reject_deposit_endpoint(
    deposit_id: int,
    user=Depends(require_admin)
):
    """
    Reject a deposit.
    """
    return reject_deposit(
        deposit_id=deposit_id
    )


@wallet_router.get(
    "/deposit/{id}",
    response_model=DepositFundsResponse
)
def get_deposit_endpoint(
    id: int,
    user=Depends(get_current_user)
):
    """
    Get a deposit record.
    """
    return get__deposit(deposit_id=id)

# ======================================================
# WITHDRAW
# ======================================================


@wallet_router.post(
    "/withdraw",
    response_model=WithdrawFundsResponse
)
def withdraw_endpoint(
    request: WithdrawFundsRequest,
    user=Depends(get_current_user)
):
    """
    Withdraw funds.
    """
    return submit_withdrawal(
        user_id=user.user_id,
        request=request
    )


@wallet_router.get(
    "/withdraws",
    response_model=list[UserWithdrawalRecordsResponse]
)
def get_user_withdrawals_endpoint(
    user=Depends(get_current_user)
):
    """
    Get user's withdrawal records.
    """
    return get_user_withdrawals(
        user_id=user.user_id
    )


@wallet_router.get(
    "/withdrawal/{id}",
    response_model=WithdrawFundsResponse
)
def get_user_withdrawal_endpoint(
    id: int,
    user=Depends(get_current_user)
):
    """
    Get user's withdrawal record.
    """
    return get_a_withdraw_record(withdraw_id=id)


@wallet_router.get(
    "/available",
    response_model=int
)
def get_user_balance_endpoint(
    user=Depends(get_current_user)
):
    """
    Get user's withdrawal record.
    """
    return get_user_total_available_balance(
        user_id=user.user_id
    )


# ======================================================
# ADMIN
# ======================================================


@wallet_router.get(
    "/admin/deposits",
    response_model=list[AdminDepositResponse]
)
def get_all_deposits_endpoint(
    status: DepositStatus | None = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(require_admin)
):
    """
    Get paginated deposits for admin, optionally filtered by status.
    """
    return get_all_deposits(
        limit=limit,
        offset=offset,
        status=status.value if status else None
    )


@wallet_router.get(
    "/admin/withdrawals",
    response_model=list[AdminWithdrawalRecordsResponse]
)
def get_all_withdrawals_endpoint(
    status: WithdrawStatus | None = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(require_admin)
):
    """
    Get paginated withdrawals for admin, optionally filtered by status.
    """
    return get_all_withdrawals(
        limit=limit,
        offset=offset,
        status=status.value if status else None
    )


@wallet_router.post(
    "/withdrawals/{withdrawal_id}/confirm",
    response_model=WithdrawFundsResponse
)
def confirm_withdrawal_endpoint(
    withdrawal_id: int,
    user=Depends(require_admin)
):
    """
    Confirm a withdrawal: flips status and consumes locked funds.
    """
    return confirm_withdrawal(
        withdrawal_id=withdrawal_id
    )


@wallet_router.post(
    "/withdrawals/{withdrawal_id}/reject",
    response_model=WithdrawFundsResponse
)
def reject_withdrawal_endpoint(
    withdrawal_id: int,
    user=Depends(require_admin)
):
    """
    Reject a withdrawal: flips status and unlocks funds to available.
    """
    return reject_withdrawal(
        withdrawal_id=withdrawal_id
    )
