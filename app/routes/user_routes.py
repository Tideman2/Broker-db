from fastapi import APIRouter, Depends
from app.services.user_services import (
    add_bank_withdraw_destination
)
from app.Models.wallet_models import (
    AddBankDestinationRequest,
    DestinationResponse
)
from app.utils.jwt import get_current_user

user_router = APIRouter(
    prefix="/user",
    tags=["User"]
)

# ======================================================
# DEPOSIT
# ======================================================


@user_router.post(
    "/bank/add",
    response_model=DestinationResponse
)
def deposit_endpoint(
    request: AddBankDestinationRequest,
    user=Depends(get_current_user)
):
    """
    Deposit funds.
    """
    return add_bank_withdraw_destination(
        user_id=user["user_id"],
        destination=request
    )
