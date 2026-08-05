
from decimal import Decimal

import pytest
from fastapi import HTTPException
from app.routes import plan_routes
from fastapi.testclient import TestClient
from app.main import app
from app.utils.jwt import create_token
# from app.db.connection import get_connection
# from app.services.plan_services import (
#     delete_plan
# )
from app.Models.plans_models import (
    CreatePlanRequest,
    Plan
)

EXPIRED_USER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoiQURNSU4iLCJleHAiOjE3ODU3NjE1OTh9.5WvoQEZIbrw-74zs6yOyfNUH_29xrv08QcVRMyzePEk"
EXPIRED_ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJyb2xlIjoiQURNSU4iLCJleHAiOjE3ODU3Nzk1NTR9.fz4-RkP-TOVKDfaY9ls-qCT1QARjTPPMqx0WCTJkuC8"
client = TestClient(app)
ADMIN_TOKEN = create_token(user_id=1, role="ADMIN")
USER_TOKEN = create_token(user_id=2, role="USER")

plan_request = CreatePlanRequest(
    plan=Plan(
        title="Pro",
        min_amount=Decimal("5000"),
        duration=30,
        roi=Decimal("12"),
        risk_management="STANDARD",
        description="Institutional strategy"
    ),
    features=[
        "Forex",
        "Crypto"
    ]
)


class TestPlan:
    def test_create_plan_admin(self):
        """
        Test creating a plan with an admin token.
        """

        headers = {
            "Authorization": f"Bearer {ADMIN_TOKEN}"
        }

        try:
            response = client.post(
                "/plan/create",
                json=plan_request.model_dump(mode="json"),
                headers=headers,
            )

            assert response.status_code == 200

        finally:
            # delete_plan(...)
            pass

    def test_create_plan_non_admin(self):
        """
        Test creating a plan with a non-admin token.
        """
        headers = {
            "Authorization": f"Bearer {USER_TOKEN}"
        }

        response = client.post(
            "/plan/create",
            json=plan_request.model_dump(mode="json"),
            headers=headers,
        )

        assert response.status_code == 403
        assert response.json() == {
            "detail": "Admin privileges required."
        }

    def test_create_plan_expired_token(self):
        """
        Test creating a plan with an expired token.
        """
        headers = {
            "Authorization": f"Bearer {EXPIRED_ADMIN_TOKEN}"
        }

        response = client.post(
            "/plan/create",
            json=plan_request.model_dump(mode="json"),
            headers=headers,
        )

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Expired signature"
        }

    def test_create_plan_title_not_unique(self):
        """
        Test creating a plan with an existing title.
        """
        headers = {
            "Authorization": f"Bearer {ADMIN_TOKEN}"
        }

        response = client.post(
            "/plan/create",
            json=plan_request.model_dump(mode="json"),
            headers=headers,
        )

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Plan title already used."
        }
