from fastapi import APIRouter, Depends

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
    get__deposit
)

from app.Models.wallet_models import (
    DepositFundsRequest,
    DepositFundsResponse,
    WithdrawFundsRequest,
    WithdrawFundsResponse,
    UserWithdrawalRecordsResponse,
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
        user_id=user.user_id,
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
        user_id=user.user_id,
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
