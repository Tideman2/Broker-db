from fastapi import APIRouter, Depends

from app.services.plan_services import (
    create_plan,
    get_plans,
    update_plan
)

from app.Models.plans_models import (
    CreatePlanRequest,
    PlanResponse,
    PlansResponse,
    UpdatePlanRequest
)

from app.utils.jwt import get_current_user, require_admin


plan_router = APIRouter(
    prefix="/plan",
    tags=["Plans"]
)


@plan_router.get(
    "",
    response_model=PlansResponse
)
def get_plans_endpoint(
    user=Depends(get_current_user)
):
    """
    Get plans. Users receive active plans only, admins receive all plans.
    """
    return get_plans(user=user)


@plan_router.post(
    "/create",
    response_model=PlanResponse
)
def create_plan_endpoint(
    request: CreatePlanRequest,
    user=Depends(require_admin)
):
    """
    Create a new plan.
    """
    return create_plan(
        user_id=user.user_id,
        request=request
    )


@plan_router.post(
    "/update",
    response_model=PlanResponse
)
def update_plan_endpoint(
    request: UpdatePlanRequest,
    user=Depends(require_admin)
):
    """
    Update an existing plan.
    """
    return update_plan(
        user_id=user.user_id,
        request=request
    )
