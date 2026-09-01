from fastapi import HTTPException
from app.db.connection import get_connection

from app.Models.plans_models import (
    CreatePlanRequest,
    UpdatePlanRequest
)

from app.utils.plans import (
    _validate_plan_title_is_unique,
    _create_plan,
    _validate_plan_feature_unique,
    _add_plan_feature,
    _validate_positive,
    _build_plan_response,
    _get_plan,
    _get_plan_features,
    _validate_plan,
    _validate_plan_title_unique_for_update,
    _update_plan,
    _delete_plan_features
)


def create_plan(
        user_id: int,
        request: CreatePlanRequest
):
    """
    Create a new plan.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Admin must exist.
        cursor.execute("SELECT id FROM admins WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Admin not found")

        # Title must be unique.
        _validate_plan_title_is_unique(cursor, request.plan.title)

        # min amount, roi and duration must be valid
        _validate_positive(request.plan.min_amount, "Minimum amount")
        _validate_positive(request.plan.roi, "ROI")
        _validate_positive(request.plan.duration, "Duration")

        _create_plan(cursor, request.plan)
        plan_id = cursor.lastrowid

        for feature in request.features:
            _validate_plan_feature_unique(
                cursor,
                plan_id,
                feature
            )

            _add_plan_feature(
                cursor,
                plan_id,
                feature
            )

        plan = _get_plan(cursor, plan_id)
        features = _get_plan_features(cursor, plan_id)
        conn.commit()

        return _build_plan_response(plan, features)

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


def update_plan(
        user_id: int,
        request: UpdatePlanRequest
):
    """
    Update an existing plan.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        plan_id = request.plan_id
        # Plan must exist.
        _validate_plan(cursor, plan_id)

        # Title must be unique.
        _validate_plan_title_unique_for_update(
            cursor, plan_id, request.plan.title)

        # min amount, roi and duration must be valid
        _validate_positive(request.plan.min_amount, "Minimum amount")
        _validate_positive(request.plan.roi, "ROI")
        _validate_positive(request.plan.duration, "Duration")

        _update_plan(cursor, request.plan, plan_id)

        _delete_plan_features(cursor, plan_id)

        for feature in request.features:
            _validate_plan_feature_unique(
                cursor,
                plan_id,
                feature
            )

            _add_plan_feature(
                cursor,
                plan_id,
                feature
            )

        plan = _get_plan(cursor, plan_id)
        features = _get_plan_features(cursor, plan_id)
        conn.commit()

        return _build_plan_response(plan, features)

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
