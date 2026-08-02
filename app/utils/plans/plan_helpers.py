from decimal import Decimal
from fastapi import HTTPException

from app.db.queries.plans_queries import (
    GET_PLAN,
    GET_PLANS,
    GET_PLAN_FEATURES,
    GET_PLAN_FEATURE,
    GET_PLAN_FEATURE_BY_NAME,
    GET_ACTIVE_PLAN_BY_ID,
    INSERT_PLAN,
    INSERT_PLAN_FEATURE,
    UPDATE_PLAN,
    UPDATE_PLAN_FEATURE,
    DELETE_PLAN,
    DELETE_PLAN_FEATURE,
    ACTIVATE_PLAN,
    DEACTIVATE_PLAN
)


from app.Models.plans_models import (
    Plan
)


def _validate_active_plan(cursor, plan_id: int):
    """
    Ensures a plan exists and is active.
    """

    cursor.execute(GET_ACTIVE_PLAN_BY_ID, (plan_id,))
    plan = cursor.fetchone()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Active plan not found."
        )

    return plan


def _validate_plan(cursor, plan_id: int):
    """
    Ensures a plan exists and returns it.
    """

    cursor.execute(GET_PLAN, (plan_id,))
    plan = cursor.fetchone()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found."
        )

    return plan


def _validate_minimum_investment(
    amount: Decimal,
    minimum: Decimal
):
    """
    Validates the investment amount.
    """

    if amount < minimum:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum investment is {minimum}."
        )


def _validate_plan_feature_unique(
    cursor,
    plan_id: int,
    feature: str
):
    """
    Feature must be unique within a plan.
    """

    cursor.execute(
        GET_PLAN_FEATURE_BY_NAME,
        (
            plan_id,
            feature,
        )
    )

    if cursor.fetchone():
        raise HTTPException(
            status_code=400,
            detail="Feature already exists."
        )


# ============================
# Reads
# ============================

def _get_plan(cursor, plan_id: int):
    """
    Fetch a plan.
    """

    return _validate_plan(cursor, plan_id)


def _get_plans(cursor):
    """
    Returns all plans.
    """

    cursor.execute(GET_PLANS)

    return cursor.fetchall()


def _get_plan_features(
    cursor,
    plan_id: int
):
    """
    Returns plan features.
    """

    cursor.execute(
        GET_PLAN_FEATURES,
        (plan_id,)
    )

    return cursor.fetchall()


def _get_plan_feature(
    cursor,
    feature_id: int
):
    """
    Returns a feature.
    """

    cursor.execute(
        GET_PLAN_FEATURE,
        (feature_id,)
    )

    feature = cursor.fetchone()

    if not feature:
        raise HTTPException(
            status_code=404,
            detail="Feature not found."
        )

    return feature


# ============================
# Writes
# ============================

def _create_plan(
    cursor,
    plan: Plan
):
    """
    Creates a plan.
    """

    cursor.execute(
        INSERT_PLAN,
        (
            plan.title,
            plan.min_amount,
            plan.duration,
            plan.roi,
            plan.risk_management,
            plan.description,
        )
    )


def _add_plan_feature(
    cursor,
    plan_id: int,
    feature: str
):
    """
    Adds a feature.
    """

    cursor.execute(
        INSERT_PLAN_FEATURE,
        (
            plan_id,
            feature,
        )
    )


# ============================
# Updates
# ============================


def _update_plan(
    cursor,
    plan: Plan,
    plan_id: int
):
    """
    Updates a plan.
    """

    cursor.execute(
        UPDATE_PLAN,
        (
            plan.title,
            plan.min_amount,
            plan.duration,
            plan.roi,
            plan.risk_management,
            plan.description,
            plan_id,
        )
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Plan not found."
        )


def _activate_plan(
    cursor,
    plan_id: int
):
    """
    Activates a plan.
    """

    cursor.execute(
        ACTIVATE_PLAN,
        (plan_id,)
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Plan not found."
        )


def _deactivate_plan(
    cursor,
    plan_id: int
):
    """
    Deactivates a plan.
    """

    cursor.execute(
        DEACTIVATE_PLAN,
        (plan_id,)
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Plan not found."
        )


def _update_plan_feature(
    cursor,
    feature_id: int,
    feature: str
):
    """
    Updates a feature.
    """

    cursor.execute(
        UPDATE_PLAN_FEATURE,
        (
            feature,
            feature_id,
        )
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Feature not found."
        )


# ============================
# Deletes
# ============================


def _delete_plan_feature(
    cursor,
    feature_id: int
):
    """
    Deletes a feature.
    """

    cursor.execute(
        DELETE_PLAN_FEATURE,
        (feature_id,)
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Feature not found."
        )


def _delete_plan(
    cursor,
    plan_id: int
):
    """
    Deletes a plan if it has no subscriptions.
    """

    cursor.execute(
        DELETE_PLAN,
        (plan_id,)
    )

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=400,
            detail="Plan has subscriptions or does not exist."
        )
