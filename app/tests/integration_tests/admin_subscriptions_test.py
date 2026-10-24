import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.connection import get_connection


@pytest.fixture()
def api():
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def admin_account(api):
    email = f"subs-admin-{uuid.uuid4().hex[:8]}@example.com"
    response = api.post(
        "/admin/register", json={"email": email, "password": "Password123"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    yield {"id": body["id"], "email": email, "token": body["token"]}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE id = %s", (body["id"],))
    conn.commit()
    cursor.close()
    conn.close()


@pytest.fixture()
def funded_user(api, admin_account):
    tag = uuid.uuid4().hex[:8]
    payload = {
        "country": "Nigeria",
        "email": f"subs-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Subscription Test User",
        "phone": f"08{tag}{tag}"[:20],
        "username": f"subsuser{tag}",
        "address1": "1 Test Street",
        "city": "Lagos",
        "state": "Lagos",
        "zip": "100001",
        "accept_terms": True,
    }
    reg = api.post("/auth/register", json=payload)
    assert reg.status_code == 200, reg.text
    body = reg.json()
    user = {"id": body["id"], "token": body["token"]}

    dep = api.post(
        "/wallet/deposit",
        json={
            "deposit": {
                "amount": "100.00",
                "asset_id": 1,
                "payment_method": 1,
            }
        },
        headers=_auth(user["token"]),
    )
    assert dep.status_code == 200, dep.text
    conf = api.post(
        f"/wallet/deposits/{dep.json()['id']}/confirm",
        headers=_auth(admin_account["token"]),
    )
    assert conf.status_code == 200, conf.text

    yield user

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user["id"],))
    conn.commit()
    cursor.close()
    conn.close()


@pytest.fixture()
def plan(api, admin_account):
    title = f"Subscription Plan {uuid.uuid4().hex[:8]}"
    response = api.post(
        "/plan/create",
        json={
            "plan": {
                "title": title,
                "min_amount": "10",
                "duration": 30,
                "roi": "12",
                "risk_management": "STANDARD",
                "description": "Subscription test plan",
            },
            "features": ["Forex"],
        },
        headers=_auth(admin_account["token"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    yield body

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM plans WHERE id = %s", (body["id"],))
    conn.commit()
    cursor.close()
    conn.close()


@pytest.fixture()
def subscription(api, funded_user, plan):
    response = api.post(
        "/subscription/subscribe",
        json={"plan_id": plan["id"], "amount": "100"},
        headers=_auth(funded_user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestAdminSubscriptions:
    def test_lists_the_users_subscriptions(
        self, api, admin_account, funded_user, subscription
    ):
        response = api.get(
            f"/admin/users/{funded_user['id']}/subscriptions",
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 200, response.text
        rows = response.json()
        assert [row["id"] for row in rows] == [subscription["id"]]
        assert {row["user_id"] for row in rows} == {funded_user["id"]}
        assert rows[0]["plan_title"] == subscription["plan_title"]
        assert rows[0]["status"] == "ACTIVE"
        assert Decimal(rows[0]["pool"]) == Decimal("100.00")

    def test_unknown_user_returns_404(self, api, admin_account):
        response = api.get(
            "/admin/users/999999999/subscriptions",
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == "User not found."

    def test_non_admin_is_forbidden(self, api, funded_user):
        response = api.get(
            f"/admin/users/{funded_user['id']}/subscriptions",
            headers=_auth(funded_user["token"]),
        )
        assert response.status_code == 403, response.text
