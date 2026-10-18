import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.connection import get_connection


@pytest.fixture()
def api():
    with TestClient(app) as client:
        yield client


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_account(api):
    email = f"pool-admin-{uuid.uuid4().hex[:8]}@example.com"
    response = api.post(
        "/admin/register", json={"email": email, "password": "Password123"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    yield {"id": body["id"], "token": body["token"]}

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
        "email": f"pool-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Pool Test User",
        "phone": f"08{tag}{tag}"[:20],
        "username": f"pooluser{tag}",
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
                "amount": "1000.00",
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
    title = f"Pool Plan {uuid.uuid4().hex[:8]}"
    response = api.post(
        "/plan/create",
        json={
            "plan": {
                "title": title,
                "min_amount": "10",
                "duration": 30,
                "roi": "12",
                "risk_management": "STANDARD",
                "description": "Pool test plan",
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
def cheap_instrument(api, admin_account):
    symbol = f"POL{uuid.uuid4().hex[:8].upper()}"
    response = api.post(
        "/instruments",
        json={
            "symbol": symbol,
            "name": "Pool Test Instrument",
            "category_id": 1,
            "current_price": "5.00",
        },
        headers=_auth(admin_account["token"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    yield body

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM instruments WHERE id = %s", (body["id"],))
    conn.commit()
    cursor.close()
    conn.close()


def _wallet(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT available, locked FROM wallet WHERE user_id = %s", (user_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def _subscribe(api, user, plan, amount="100"):
    response = api.post(
        "/subscription/subscribe",
        json={"plan_id": plan["id"], "amount": amount},
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestSubscriptionPool:
    def test_subscribe_moves_available_into_pool(
        self, api, admin_account, funded_user, plan
    ):
        before = _wallet(funded_user["id"])

        body = _subscribe(api, funded_user, plan, "100")

        after = _wallet(funded_user["id"])
        assert float(before["available"]) - float(after["available"]) == 100.0
        assert float(after["locked"]) == float(before["locked"])
        assert float(body["pool"]) == 100.0

    def test_subscription_read_includes_pool(
        self, api, admin_account, funded_user, plan
    ):
        _subscribe(api, funded_user, plan, "100")

        response = api.get(
            "/subscription", headers=_auth(funded_user["token"])
        )

        assert response.status_code == 200, response.text
        subscriptions = response.json()["subscriptions"]
        assert len(subscriptions) == 1
        assert float(subscriptions[0]["pool"]) == 100.0
