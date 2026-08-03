from fastapi import APIRouter, Depends

from app.services.plan_services import create_plan

from app.Models.plans_models import (
    CreatePlanRequest,
    PlanResponse
)

from app.utils.jwt import require_admin


plan_router = APIRouter(
    prefix="/plan",
    tags=["Plans"]
)


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
