from fastapi import APIRouter, Depends
from typing import List

from app.services.subscription_services import (
    subscribe_to_a_plan
)
from app.Models.plans_models import (
    SubscribeRequest,
    SubscriptionResponse
)

from app.utils.jwt import get_current_user, require_admin


subscription_router = APIRouter(
    prefix="/subscription",
    tags=["Subscription"]
)


@subscription_router.post(
    "/subscribe",
    response_model=SubscriptionResponse
)
def subscribe(
    request: SubscribeRequest,
    user=Depends(get_current_user)
):
    """
    Subscribe to a plan.
    """
    return subscribe_to_a_plan(
        user_id=user.user_id,
        data=request
    )
