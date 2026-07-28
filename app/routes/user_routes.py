from fastapi import APIRouter, Depends
from app.services.user_services import (
    add_bank_withdraw_destination,
    add_crypto_withdraw_destination
)
from app.Models.wallet_models import (
    AddBankDestinationRequest,
    DestinationResponse,
    AddCryptoDestinationRequest
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
def add_bank_destination_endpoint(
    request: AddBankDestinationRequest,
    user=Depends(get_current_user)
):
    """
    Add bank destination endpoint.
    """
    return add_bank_withdraw_destination(
        user_id=user["user_id"],
        destination=request
    )


@user_router.post(
    "/crypto/add",
    response_model=DestinationResponse
)
def add_crypto_destination_endpoint(
    request: AddCryptoDestinationRequest,
    user=Depends(get_current_user)
):
    """
    Add crypto destination endpoint.
    """

    return add_crypto_withdraw_destination(
        user_id=user["user_id"],
        destination=request
    )
