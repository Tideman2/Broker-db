from fastapi import APIRouter, Depends

from app.services.subscription_services import (
    cancel_subscription,
    get_subscription_summaries,
    get_user_subscriptions,
    subscribe_to_a_plan
)

from app.Models.plans_models import (
    SubscribeRequest,
    SubscriptionResponse,
    SubscriptionsResponse,
    SubscriptionSummaryResponse
)

from app.utils.jwt import get_current_user


subscription_router = APIRouter(
    prefix="/subscription",
    tags=["Subscription"]
)


@subscription_router.get(
    "",
    response_model=SubscriptionsResponse
)
def get_subscriptions_endpoint(
    user=Depends(get_current_user)
):
    """
    Get the current user's subscriptions.
    """
    return get_user_subscriptions(user_id=user.user_id)


@subscription_router.get(
    "/summary",
    response_model=list[SubscriptionSummaryResponse]
)
def get_subscription_summaries_endpoint(
    user=Depends(get_current_user)
):
    """
    Get a profit summary for the current user's active subscriptions.
    """
    return get_subscription_summaries(user_id=user.user_id)


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


@subscription_router.post(
    "/cancel/{subscription_id}",
    response_model=SubscriptionResponse
)
def cancel(
    subscription_id: int,
    user=Depends(get_current_user)
):
    """
    Cancel a subscription.

    Settles the subscription immediately: open positions are liquidated
    back into the subscription pool, the pool is returned to the user's
    available balance, and the subscription is marked CANCELLED.
    """
    return cancel_subscription(
        user_id=user.user_id,
        subscription_id=subscription_id
    )
