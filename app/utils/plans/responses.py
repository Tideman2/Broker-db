from decimal import Decimal
from app.Models.plans_models import (
    PlanResponse,
    PlansResponse,
    SubscriptionResponse,
    SubscriptionsResponse,
    SubscriptionSummaryResponse
)

from app.utils.plans.settlement import _market_value_of_open_positions


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
        pool=subscription["pool"].quantize(Decimal("0.01")),
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


def _build_subscriptions_response(
    subscriptions: list[SubscriptionResponse]
) -> SubscriptionsResponse:

    return SubscriptionsResponse(subscriptions=subscriptions)


def _build_subscription_summary(
    cursor,
    subscription: dict
) -> SubscriptionSummaryResponse:
    """
    Builds a per-subscription summary: the pooled cash plus the market
    value of open positions, measured against the amount invested.
    """

    principal = subscription["invested_amount"]

    current_value = (
        subscription["pool"]
        + _market_value_of_open_positions(cursor, subscription["id"])
    )

    profit_loss = current_value - principal

    if principal:
        roi_percent = profit_loss / principal * Decimal("100")
    else:
        roi_percent = Decimal("0")

    return SubscriptionSummaryResponse(
        subscription_id=subscription["id"],
        principal=principal.quantize(Decimal("0.01")),
        current_value=current_value.quantize(Decimal("0.01")),
        profit_loss=profit_loss.quantize(Decimal("0.01")),
        roi_percent=roi_percent.quantize(Decimal("0.01")),
        status=subscription["status"],
    )


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


def _build_plans_response(
    plans: list[PlanResponse]
) -> PlansResponse:

    return PlansResponse(plans=plans)

