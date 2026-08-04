from decimal import Decimal
from app.Models.plans_models import (
    PlanResponse,
    SubscriptionResponse
)


def _build_subscription_response(
    subscription: dict
) -> SubscriptionResponse:

    return SubscriptionResponse(
        id=subscription["id"],
        user_id=subscription["user_id"],
        plan_id=subscription["plan_id"],
        plan_title=subscription["title"],
        invested_amount=subscription["invested_amount"].quantize(
            Decimal("0.01")
        ),
        expiration_date=subscription["expiration_date"],
        status=subscription["status"],
        created_at=subscription["created_at"],
    )


def _build_subscription_list(
    subscriptions: list[dict]
) -> list[SubscriptionResponse]:

    return [
        _build_subscription_response(subscription)
        for subscription in subscriptions
    ]


def _build_plan_response(
    plan: dict,
    features: list[dict]
) -> PlanResponse:

    return PlanResponse(
        id=plan["id"],
        title=plan["title"],
        min_amount=plan["min_amount"].quantize(Decimal("0.01")),
        duration=plan["duration"],
        roi=plan["roi"],
        risk_management=plan["risk_management"],
        description=plan["description"],
        status=plan["status"],
        features=[
            feature["feature"]
            for feature in features
        ],
        created_at=plan["created_at"],
        updated_at=plan["updated_at"],
    )
