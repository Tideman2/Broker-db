from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class PlanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class SubscriptionStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class RiskManagement(str, Enum):
    STANDARD = "STANDARD"
    ADVANCED_HEDGING = "ADVANCED_HEDGING"
    TAILORED_MULTI_LAYER = "TAILORED_MULTI_LAYER"


class Plan(BaseModel):
    title: str
    min_amount: Decimal
    duration: int
    roi: Decimal
    risk_management: RiskManagement
    description: str

# ============================
# Request Models
# ============================


class CreatePlanRequest(BaseModel):
    plan: Plan
    features: list[str]


class UpdatePlanRequest(BaseModel):
    plan: Plan
    features: list[str]


class SubscribeRequest(BaseModel):
    plan_id: int
    amount: Decimal


# ============================
# Response Models
# ============================

class PlanResponse(BaseModel):
    id: int

    title: str
    min_amount: Decimal
    duration: int
    roi: Decimal

    risk_management: RiskManagement
    description: str

    status: PlanStatus

    features: list[str]

    created_at: datetime
    updated_at: datetime


class PlansResponse(BaseModel):
    plans: list[PlanResponse]


class SubscriptionResponse(BaseModel):
    id: int

    user_id: int

    plan_id: int
    plan_title: str

    invested_amount: Decimal

    expiration_date: datetime

    status: SubscriptionStatus

    created_at: datetime
    updated_at: datetime


class SubscriptionsResponse(BaseModel):
    subscriptions: list[SubscriptionResponse]


class SubscriptionSummaryResponse(BaseModel):
    subscription_id: int

    principal: Decimal
    current_value: Decimal

    profit_loss: Decimal

    roi_percent: Decimal

    status: SubscriptionStatus

# ============================
# Entity Models
# ============================


class Subscription(BaseModel):
    user_id: int
    plan_id: int

    invested_amount: Decimal
    expiration_date: datetime
