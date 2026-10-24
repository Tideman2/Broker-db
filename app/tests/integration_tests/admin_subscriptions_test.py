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
                "amount": "200.00",
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
def plan_b(api, admin_account):
    title = f"Subscription Plan B {uuid.uuid4().hex[:8]}"
    response = api.post(
        "/plan/create",
        json={
            "plan": {
                "title": title,
                "min_amount": "10",
                "duration": 30,
                "roi": "12",
                "risk_management": "STANDARD",
                "description": "Subscription test plan B",
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


@pytest.fixture()
def subscription_b(api, funded_user, plan_b):
    response = api.post(
        "/subscription/subscribe",
        json={"plan_id": plan_b["id"], "amount": "100"},
        headers=_auth(funded_user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def cheap_instrument(api, admin_account):
    symbol = f"SUB{uuid.uuid4().hex[:8].upper()}"
    response = api.post(
        "/instruments",
        json={
            "symbol": symbol,
            "name": "Subscription Test Instrument",
            "category_id": 1,
            "current_price": "5.00",
        },
        headers=_auth(admin_account["token"]),
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


def _buy(api, token, user_id, instrument_id, subscription_id, quantity):
    return api.post(
        f"/portfolio/admin/buy/{user_id}",
        json={
            "instrument_id": instrument_id,
            "quantity": quantity,
            "subscription_id": subscription_id,
        },
        headers=_auth(token),
    )


def _sell(api, token, user_id, instrument_id, subscription_id, quantity):
    return api.post(
        f"/portfolio/admin/sell/{user_id}",
        json={
            "instrument_id": instrument_id,
            "quantity": quantity,
            "subscription_id": subscription_id,
        },
        headers=_auth(token),
    )


def _holdings(api, token, subscription_id):
    return api.get(
        f"/admin/subscriptions/{subscription_id}/holdings",
        headers=_auth(token),
    )


class TestSubscriptionHoldings:
    def test_returns_only_that_subscriptions_open_positions(
        self,
        api,
        admin_account,
        funded_user,
        cheap_instrument,
        subscription,
        subscription_b,
    ):
        first_buy = _buy(
            api,
            admin_account["token"],
            funded_user["id"],
            cheap_instrument["id"],
            subscription["id"],
            "2",
        )
        assert first_buy.status_code == 200, first_buy.text

        second_buy = _buy(
            api,
            admin_account["token"],
            funded_user["id"],
            cheap_instrument["id"],
            subscription_b["id"],
            "3",
        )
        assert second_buy.status_code == 200, second_buy.text

        first = _holdings(api, admin_account["token"], subscription["id"])
        second = _holdings(api, admin_account["token"], subscription_b["id"])

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert float(first.json()[0]["net_quantity"]) == 2.0
        assert float(second.json()[0]["net_quantity"]) == 3.0

    def test_closed_position_is_excluded(
        self, api, admin_account, funded_user, cheap_instrument, subscription
    ):
        buy = _buy(
            api,
            admin_account["token"],
            funded_user["id"],
            cheap_instrument["id"],
            subscription["id"],
            "1",
        )
        assert buy.status_code == 200, buy.text

        sell = _sell(
            api,
            admin_account["token"],
            funded_user["id"],
            cheap_instrument["id"],
            subscription["id"],
            "1",
        )
        assert sell.status_code == 200, sell.text

        response = _holdings(api, admin_account["token"], subscription["id"])
        assert response.status_code == 200, response.text
        assert response.json() == []

    def test_inactive_instrument_still_appears(
        self, api, admin_account, funded_user, cheap_instrument, subscription
    ):
        buy = _buy(
            api,
            admin_account["token"],
            funded_user["id"],
            cheap_instrument["id"],
            subscription["id"],
            "1",
        )
        assert buy.status_code == 200, buy.text

        deactivate = api.delete(
            f"/instruments/{cheap_instrument['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert deactivate.status_code == 200, deactivate.text

        response = _holdings(api, admin_account["token"], subscription["id"])
        assert response.status_code == 200, response.text
        [row] = response.json()
        assert row["instrument_id"] == cheap_instrument["id"]
        assert row["is_active"] is False
        assert float(row["net_quantity"]) == 1.0

    def test_empty_subscription_returns_empty_list(
        self, api, admin_account, subscription
    ):
        response = _holdings(api, admin_account["token"], subscription["id"])
        assert response.status_code == 200, response.text
        assert response.json() == []

    def test_unknown_subscription_returns_404(self, api, admin_account):
        response = _holdings(api, admin_account["token"], 999999999)
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == "Subscription not found."

    def test_non_admin_is_forbidden(self, api, funded_user, subscription):
        response = _holdings(api, funded_user["token"], subscription["id"])
        assert response.status_code == 403, response.text
