import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.connection import get_connection


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def api():
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def admin_account(api):
    email = f"flow-admin-{uuid.uuid4().hex[:8]}@example.com"
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
def user(api):
    tag = uuid.uuid4().hex[:8]
    payload = {
        "country": "Nigeria",
        "email": f"flow-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Flow Test User",
        "phone": f"08{tag}{tag}"[:20],
        "username": f"flowuser{tag}",
        "address1": "1 Test Street",
        "city": "Lagos",
        "state": "Lagos",
        "zip": "100001",
        "accept_terms": True,
    }
    response = api.post("/auth/register", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    yield {"id": body["id"], "token": body["token"]}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (body["id"],))
    conn.commit()
    cursor.close()
    conn.close()


@pytest.fixture()
def funded_user(api, admin_account, user):
    _deposit(api, admin_account, user, "1000.00")
    return user


@pytest.fixture()
def plan(api, admin_account):
    title = f"Flow Plan {uuid.uuid4().hex[:8]}"
    response = api.post(
        "/plan/create",
        json={
            "plan": {
                "title": title,
                "min_amount": "10",
                "duration": 30,
                "roi": "12",
                "risk_management": "STANDARD",
                "description": "Money flow test plan",
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
    symbol = f"FLW{uuid.uuid4().hex[:8].upper()}"
    response = api.post(
        "/instruments",
        json={
            "symbol": symbol,
            "name": "Flow Test Instrument",
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


@pytest.fixture()
def bank_destination(api, user):
    response = api.post(
        "/user/bank/add",
        json={
            "destination_details": {"label": "Flow Bank", "type": "BANK"},
            "bank_destination": {
                "bank_name": "Flow Bank",
                "account_name": "Flow Test User",
                "account_number": "0123456789",
            },
        },
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _deposit(api, admin_account, user, amount):
    response = api.post(
        "/wallet/deposit",
        json={
            "deposit": {
                "amount": amount,
                "asset_id": 1,
                "payment_method": 1,
            }
        },
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text

    confirmed = api.post(
        f"/wallet/deposits/{response.json()['id']}/confirm",
        headers=_auth(admin_account["token"]),
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def _withdraw_and_confirm(api, admin_account, user, destination, amount):
    response = api.post(
        "/wallet/withdraw",
        json={"amount": amount, "destination_id": destination["id"]},
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text

    confirmed = api.post(
        f"/wallet/withdrawals/{response.json()['id']}/confirm",
        headers=_auth(admin_account["token"]),
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def _subscribe(api, user, plan, amount):
    response = api.post(
        "/subscription/subscribe",
        json={"plan_id": plan["id"], "amount": amount},
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _subscription_row(subscription_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM subscriptions WHERE id = %s", (subscription_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


class TestMoneyFlow:
    def test_returns_only_the_latest_four_on_each_side(
        self, api, admin_account, funded_user, bank_destination
    ):
        for amount in ("10.00", "20.00", "30.00", "40.00"):
            _deposit(api, admin_account, funded_user, amount)

        for amount in ("1.00", "2.00", "3.00", "4.00", "5.00"):
            _withdraw_and_confirm(
                api, admin_account, funded_user, bank_destination, amount
            )

        response = api.get(
            "/wallet/money-flow", headers=_auth(funded_user["token"])
        )

        assert response.status_code == 200, response.text
        body = response.json()

        assert [float(item["amount"]) for item in body["money_in"]] == [
            40.0,
            30.0,
            20.0,
            10.0,
        ]
        assert [item["type"] for item in body["money_in"]] == ["DEPOSIT"] * 4
        assert [item["direction"] for item in body["money_in"]] == ["IN"] * 4

        assert [float(item["amount"]) for item in body["money_out"]] == [
            5.0,
            4.0,
            3.0,
            2.0,
        ]
        assert [item["type"] for item in body["money_out"]] == [
            "WITHDRAWAL"
        ] * 4
        assert [item["direction"] for item in body["money_out"]] == ["OUT"] * 4

    def test_settlement_returns_payout_as_money_in(
        self, api, funded_user, plan
    ):
        subscription = _subscribe(api, funded_user, plan, "100.00")

        response = api.post(
            f"/subscription/cancel/{subscription['id']}",
            headers=_auth(funded_user["token"]),
        )
        assert response.status_code == 200, response.text

        row = _subscription_row(subscription["id"])
        assert float(row["settled_amount"]) == 100.0
        assert row["settled_at"] is not None

        response = api.get(
            "/wallet/money-flow", headers=_auth(funded_user["token"])
        )
        assert response.status_code == 200, response.text
        body = response.json()

        payouts = [
            item
            for item in body["money_in"]
            if item["type"] == "SUBSCRIPTION_PAYOUT"
        ]
        assert len(payouts) == 1
        assert float(payouts[0]["amount"]) == 100.0
        assert payouts[0]["direction"] == "IN"
        assert payouts[0]["status"] == "CANCELLED"

        investments = [
            item
            for item in body["money_out"]
            if item["type"] == "SUBSCRIPTION_INVESTMENT"
        ]
        assert len(investments) == 1
        assert float(investments[0]["amount"]) == 100.0
        assert investments[0]["direction"] == "OUT"

    def test_excludes_unsettled_deposits_and_withdrawals(
        self, api, admin_account, funded_user, bank_destination
    ):
        pending_deposit = api.post(
            "/wallet/deposit",
            json={
                "deposit": {
                    "amount": "500.00",
                    "asset_id": 1,
                    "payment_method": 1,
                }
            },
            headers=_auth(funded_user["token"]),
        )
        assert pending_deposit.status_code == 200, pending_deposit.text

        rejected_deposit = api.post(
            "/wallet/deposit",
            json={
                "deposit": {
                    "amount": "600.00",
                    "asset_id": 1,
                    "payment_method": 1,
                }
            },
            headers=_auth(funded_user["token"]),
        )
        assert rejected_deposit.status_code == 200, rejected_deposit.text
        rejected = api.post(
            f"/wallet/deposits/{rejected_deposit.json()['id']}/reject",
            headers=_auth(admin_account["token"]),
        )
        assert rejected.status_code == 200, rejected.text

        pending_withdrawal = api.post(
            "/wallet/withdraw",
            json={"amount": "7.00", "destination_id": bank_destination["id"]},
            headers=_auth(funded_user["token"]),
        )
        assert pending_withdrawal.status_code == 200, pending_withdrawal.text

        rejected_withdrawal = api.post(
            "/wallet/withdraw",
            json={"amount": "8.00", "destination_id": bank_destination["id"]},
            headers=_auth(funded_user["token"]),
        )
        assert rejected_withdrawal.status_code == 200, rejected_withdrawal.text
        rejected = api.post(
            f"/wallet/withdrawals/{rejected_withdrawal.json()['id']}/reject",
            headers=_auth(admin_account["token"]),
        )
        assert rejected.status_code == 200, rejected.text

        response = api.get(
            "/wallet/money-flow", headers=_auth(funded_user["token"])
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert [float(item["amount"]) for item in body["money_in"]] == [
            1000.0
        ]
        assert body["money_out"] == []

    def test_trades_are_not_reported(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100.00")

        buy = api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )
        assert buy.status_code == 200, buy.text

        sell = api.post(
            f"/portfolio/admin/sell/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "1",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )
        assert sell.status_code == 200, sell.text

        response = api.get(
            "/wallet/money-flow", headers=_auth(funded_user["token"])
        )
        assert response.status_code == 200, response.text
        body = response.json()

        types = {
            item["type"]
            for item in body["money_in"] + body["money_out"]
        }
        assert types == {"DEPOSIT", "SUBSCRIPTION_INVESTMENT"}

    def test_returns_empty_lists_for_user_without_activity(self, api, user):
        response = api.get(
            "/wallet/money-flow", headers=_auth(user["token"])
        )

        assert response.status_code == 200, response.text
        assert response.json() == {"money_in": [], "money_out": []}

    def test_requires_authentication(self, api):
        response = api.get("/wallet/money-flow")

        assert response.status_code == 401
