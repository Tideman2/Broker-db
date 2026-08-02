from decimal import Decimal
from fastapi import HTTPException
from app.db.queries.subscriptions_queries import (
    GET_SUBSCRIPTION,
    GET_USER_SUBSCRIPTIONS,
    GET_ACTIVE_SUBSCRIPTION,
    INSERT_SUBSCRIPTION,
    COMPLETE_SUBSCRIPTION,
    CANCEL_SUBSCRIPTION,
    GET_ACTIVE_SUBSCRIPTION_BY_USER_AND_PLAN
)

from app.Models.plans_models import (
    Subscription
)


def _complete_subscription(
    cursor,
    subscription_id: int
):
    """
    Marks an active subscription as completed.
    """

    cursor.execute(
        COMPLETE_SUBSCRIPTION,
        (subscription_id,)
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail="Subscription cannot be completed."
        )


def _cancel_subscription(
    cursor,
    subscription_id: int
):
    """
    Cancels an active subscription.
    """

    cursor.execute(
        CANCEL_SUBSCRIPTION,
        (subscription_id,)
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail="Subscription cannot be cancelled."
        )


def _create_subscription(
    cursor,
    subscription: Subscription
):
    """
    Creates an subscription.
    """

    cursor.execute(
        INSERT_SUBSCRIPTION,
        (
            subscription.user_id,
            subscription.plan_id,
            subscription.invested_amount,
            subscription.expiration_date,
        )
    )


def _get_subscription(
    cursor,
    subscription_id: int
):
    """
    Fetch subscription or raise 404.
    """
    cursor.execute(
        GET_SUBSCRIPTION,
        (subscription_id,)
    )

    subscription = cursor.fetchone()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found."
        )

    return subscription


def _get_active_subscription(
    cursor,
    user_id: int,
    subscription_id: int
):
    """
    Returns the user's active subscription
    for a particular plan.
    """

    cursor.execute(
        GET_ACTIVE_SUBSCRIPTION,
        (
            user_id,
            subscription_id,
        )
    )

    return cursor.fetchone()


def _validate_no_active_subscription(
    cursor,
    user_id: int,
    plan_id: int
):
    """
    User cannot have more than one active subscription
    to the same plan.
    """

    cursor.execute(
        GET_ACTIVE_SUBSCRIPTION_BY_USER_AND_PLAN,
        (user_id, plan_id,)
    )

    subscription = cursor.fetchone()

    if subscription:
        raise HTTPException(
            status_code=400,
            detail="You already have an active subscription to this plan."
        )


def _validate_subscription_status(
    subscription: dict,
    expected_status: str
):
    """
    Ensures subscription is in the expected status.
    """

    if subscription["status"] != expected_status:
        raise HTTPException(
            status_code=400,
            detail=f"Subscription must be {expected_status}."
        )


def _get_user_subscriptions(
    cursor,
    user_id: int
):
    cursor.execute(
        GET_USER_SUBSCRIPTIONS,
        (user_id,)
    )

    return cursor.fetchall()


def _calculate_subscription_profit(
    invested_amount: Decimal,
    current_value: Decimal
) -> Decimal:
    """
    Calculates profit/loss.
    """

    return current_value - invested_amount
