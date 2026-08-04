from datetime import datetime, timedelta, UTC
from fastapi import HTTPException

from app.db.connection import get_connection

from app.Models.plans_models import (
    SubscribeRequest,
    Subscription
)

from app.utils.plans import (
    _create_subscription,
    _validate_active_plan,
    _validate_minimum_investment,
    _build_subscription_response,
    _get_subscription,
    _validate_no_active_subscription,
    _get_active_subscription,
    _cancel_subscription
)

from app.utils.wallet import (
    _get_wallet,
    _validate_available_balance,
    _lock_funds
)


def subscribe_to_a_plan(
    user_id: int,
    data: SubscribeRequest
):
    """
    Subscribes user to a plan.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        #  Plan must exist.
        # check if plan is active
        plan = _validate_active_plan(cursor, data.plan_id)
        _validate_minimum_investment(data.amount, plan["min_amount"])

        wallet = _get_wallet(cursor, user_id)
        _validate_available_balance(data.amount, wallet["available"])

        _validate_no_active_subscription(
            cursor,
            user_id,
            data.plan_id
        )

        _lock_funds(cursor, user_id, data.amount)

        # compute expitration date using plan duration
        expiration_date = datetime.now(UTC) + timedelta(days=plan["duration"])

        new_subscription = Subscription(
            user_id=user_id,
            plan_id=data.plan_id,
            invested_amount=data.amount,
            expiration_date=expiration_date
        )

        _create_subscription(cursor, new_subscription)

        subscription_id = cursor.lastrowid
        subscription = _get_subscription(cursor, subscription_id)

        conn.commit()
        return _build_subscription_response(subscription)

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def cancel_subscription(
        user_id: int,
        subscription_id: int
):
    """
    Cancel a subscription.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Subscription must exist.
        _get_active_subscription(
            cursor, user_id, subscription_id)

        _cancel_subscription(cursor, subscription_id)

        conn.commit()
        return {"message": "Subscription cancelled", "id": subscription_id}

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()
