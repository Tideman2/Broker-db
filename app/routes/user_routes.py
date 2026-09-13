from fastapi import APIRouter, Depends
from app.services.user_services import (
    add_bank_withdraw_destination,
    add_crypto_withdraw_destination,
    get_withdraw_destinations
)

from app.services.wallet_services import (
    get_recent_deposits
)

from app.Models.wallet_models import (
    AddBankDestinationRequest,
    DestinationResponse,
    AddCryptoDestinationRequest,
    DepositResponse
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
        user_id=user.user_id,
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
        user_id=user.user_id,
        destination=request
    )


@user_router.get(
    "/withdraw-destinations",
    response_model=list[DestinationResponse]
)
def get_withdraw_destinations_endpoint(
    user=Depends(get_current_user)
):
    """
    Get user destinations endpoint.
    """

    return get_withdraw_destinations(
        user_id=user.user_id,
    )


@user_router.get(
    "/deposits",
    response_model=list[DepositResponse]
)
def get_deposits_endpoint(
    limit: int = 10,
    offset: int = 0,
    user=Depends(get_current_user)
):
    """
    Get paginated deposits for the current user.
    """

    return get_recent_deposits(
        user_id=user.user_id,
        limit=limit,
        offset=offset
    )
