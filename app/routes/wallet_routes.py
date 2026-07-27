from fastapi import APIRouter, Depends
from typing import List

from app.utils.jwt import get_current_user

from app.services.wallet_services import (
    deposit_funds,
    reject_deposit,
    confirm_deposit
)
from app.Models.wallet_models import (
    DepositFundsRequest,
    DepositFundsResponse
)


wallet_router = APIRouter(
    prefix="/wallet",
    tags=["Wallet"]
)


@wallet_router.post(
    "/deposit",
    response_model=DepositFundsResponse
)
def buy(
    request: DepositFundsRequest,
    user=Depends(get_current_user)
):
    """
    Buy an instrument.
    """
    return deposit_funds(
        user_id=user["user_id"],
        data=request
    )


@wallet_router.post(
    "/deposits/{deposit_id}/confirm",
    response_model=DepositFundsResponse
)
def confirm_deposit_endpoint(
    deposit_id: int,
    user=Depends(get_current_user)
):
    """
    Confirm a deposit.
    """
    return confirm_deposit(
        user_id=user["user_id"],
        deposit_id=deposit_id
    )


@wallet_router.post(
    "/deposits/{deposit_id}/reject",
    response_model=DepositFundsResponse
)
def reject_deposit_endpoint(
    deposit_id: int,
    user=Depends(get_current_user)
):
    """
    Reject a deposit.
    """
    return reject_deposit(
        user_id=user["user_id"],
        deposit_id=deposit_id
    )
