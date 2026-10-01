from fastapi import APIRouter, Depends

from app.services.subscription_services import (
    # cancel_subscription,
    get_user_subscriptions,
    subscribe_to_a_plan
)

from app.Models.plans_models import (
    SubscribeRequest,
    SubscriptionResponse,
    SubscriptionsResponse
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


# DISABLED: the cancel flow must not be exposed until the
# blockers below are resolved. The handler is commented out rather
# than deleted, and must be restored together with the
# cancel_subscription import above.
#
#   1. cancel_subscription() returns {"message", "id"} but this
#      handler declared response_model=SubscriptionResponse, so
#      FastAPI raised a 500 ResponseValidationError on every call.
#      It must return a built SubscriptionResponse instead.
#   2. Funds are locked on subscribe (_lock_funds) and never
#      released: _unlock_funds and _consume_lock_funds exist but are
#      never called, so a cancelled subscription would strand the
#      principal in wallet.locked.
#   3. Subscriptions never mature: _complete_subscription is never
#      called and there is no scheduler in this codebase, so
#      expiration_date is never acted on.
#
# NOTE: the (user_id, subscription_id) argument swap in
# _get_active_subscription was already fixed, so blocker 1 is the
# only remaining code defect here. Blockers 2 and 3 need a business
# decision on how principal is treated before restoring this route.
#
# @subscription_router.post(
#     "/cancel/{subscription_id}",
#     response_model=SubscriptionResponse
# )
# def cancel(
#     subscription_id: int,
#     user=Depends(get_current_user)
# ):
#     """
#     Cancel a subscription.
#     """
#     return cancel_subscription(
#         user_id=user.user_id,
#         subscription_id=subscription_id
#     )
