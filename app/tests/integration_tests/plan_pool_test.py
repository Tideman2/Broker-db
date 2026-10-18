import uuid
from datetime import datetime, timedelta, UTC

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.connection import get_connection
from app.services.settlement_service import run_expiry_sweep


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
def second_plan(api, admin_account):
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
                "description": "Pool test plan two",
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


def _pool(subscription_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT pool FROM subscriptions WHERE id = %s", (subscription_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return float(row["pool"])


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


def _force_expire(subscription_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subscriptions SET expiration_date = %s WHERE id = %s",
        (datetime.now(UTC) - timedelta(days=1), subscription_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def _last_transaction(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM transactions WHERE user_id = %s ORDER BY id DESC LIMIT 1",
        (user_id,),
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


class TestAdminTradingUnderSubscription:
    def test_admin_buy_debits_pool(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")

        response = api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

        assert response.status_code == 200, response.text
        assert _pool(subscription["id"]) == 90.0

    def test_admin_buy_records_subscription_id(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")

        api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

        assert (
            _last_transaction(funded_user["id"])["subscription_id"]
            == subscription["id"]
        )

    def test_admin_buy_requires_subscription_id(
        self, api, admin_account, funded_user, cheap_instrument
    ):
        response = api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
            },
            headers=_auth(admin_account["token"]),
        )

        assert response.status_code == 422, response.text

    def test_admin_buy_unknown_subscription_returns_404(
        self, api, admin_account, funded_user, cheap_instrument
    ):
        response = api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
                "subscription_id": 999999999,
            },
            headers=_auth(admin_account["token"]),
        )

        assert response.status_code == 404, response.text

    def test_admin_buy_insufficient_pool(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")

        response = api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "1000",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

        assert response.status_code == 400, response.text
        assert response.json() == {
            "detail": "Insufficient subscription pool."
        }
        assert _pool(subscription["id"]) == 100.0

    def test_admin_sell_credits_pool(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

        response = api.post(
            f"/portfolio/admin/sell/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "1",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

        assert response.status_code == 200, response.text
        assert _pool(subscription["id"]) == 95.0

    def test_user_buy_route_removed(self, api, funded_user, cheap_instrument):
        response = api.post(
            "/portfolio/buy",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "1",
            },
            headers=_auth(funded_user["token"]),
        )

        assert response.status_code in (404, 405), response.text

    def test_user_sell_route_removed(self, api, funded_user, cheap_instrument):
        response = api.post(
            "/portfolio/sell",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "1",
            },
            headers=_auth(funded_user["token"]),
        )

        assert response.status_code in (404, 405), response.text


class TestCancelSettlement:
    def _buy(self, api, admin_account, user, instrument, subscription, qty):
        return api.post(
            f"/portfolio/admin/buy/{user['id']}",
            json={
                "instrument_id": instrument["id"],
                "quantity": qty,
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

    def test_cancel_settles_immediately(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        self._buy(
            api, admin_account, funded_user, cheap_instrument, subscription, "2"
        )
        available_before = float(_wallet(funded_user["id"])["available"])

        response = api.post(
            f"/subscription/cancel/{subscription['id']}",
            headers=_auth(funded_user["token"]),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "CANCELLED"
        assert float(body["pool"]) == 0.0

        # 90 pool + 10 liquidation proceeds (2 @ 5) return to available
        available_after = float(_wallet(funded_user["id"])["available"])
        assert available_after - available_before == 100.0

    def test_cancel_liquidates_open_positions(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        self._buy(
            api, admin_account, funded_user, cheap_instrument, subscription, "2"
        )

        api.post(
            f"/subscription/cancel/{subscription['id']}",
            headers=_auth(funded_user["token"]),
        )

        liquidation = _last_transaction(funded_user["id"])
        assert liquidation["type"] == "SELL"
        assert liquidation["subscription_id"] == subscription["id"]
        assert float(liquidation["quantity"]) == 2.0

    def test_cancel_without_positions_releases_pool(
        self, api, funded_user, plan
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        available_before = float(_wallet(funded_user["id"])["available"])

        api.post(
            f"/subscription/cancel/{subscription['id']}",
            headers=_auth(funded_user["token"]),
        )

        assert _pool(subscription["id"]) == 0.0
        available_after = float(_wallet(funded_user["id"])["available"])
        assert available_after - available_before == 100.0

    def test_cancel_unknown_subscription_rejected(self, api, funded_user):
        response = api.post(
            "/subscription/cancel/999999999",
            headers=_auth(funded_user["token"]),
        )

        assert response.status_code in (401, 404), response.text

    def test_cancelled_subscription_cannot_be_traded(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        api.post(
            f"/subscription/cancel/{subscription['id']}",
            headers=_auth(funded_user["token"]),
        )

        response = self._buy(
            api, admin_account, funded_user, cheap_instrument, subscription, "1"
        )

        assert response.status_code == 404, response.text


class TestExpirySettlement:
    def _buy(self, api, admin_account, user, instrument, subscription, qty):
        return api.post(
            f"/portfolio/admin/buy/{user['id']}",
            json={
                "instrument_id": instrument["id"],
                "quantity": qty,
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

    def test_expiry_sweep_settles_due_subscription(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        self._buy(
            api, admin_account, funded_user, cheap_instrument, subscription, "2"
        )
        available_before = float(_wallet(funded_user["id"])["available"])
        _force_expire(subscription["id"])

        settled = run_expiry_sweep()

        assert settled == 1
        row = _subscription_row(subscription["id"])
        assert row["status"] == "COMPLETED"
        assert float(row["pool"]) == 0.0

        # 90 pool + 10 liquidation proceeds (2 @ 5) return to available
        available_after = float(_wallet(funded_user["id"])["available"])
        assert available_after - available_before == 100.0

        liquidation = _last_transaction(funded_user["id"])
        assert liquidation["type"] == "SELL"
        assert liquidation["subscription_id"] == subscription["id"]

    def test_expiry_sweep_leaves_unexpired_subscription_alone(
        self, api, funded_user, plan
    ):
        subscription = _subscribe(api, funded_user, plan, "100")

        settled = run_expiry_sweep()

        assert settled == 0
        row = _subscription_row(subscription["id"])
        assert row["status"] == "ACTIVE"
        assert float(row["pool"]) == 100.0

    def test_expired_subscription_cannot_be_traded(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        _force_expire(subscription["id"])
        run_expiry_sweep()

        response = self._buy(
            api, admin_account, funded_user, cheap_instrument, subscription, "1"
        )

        assert response.status_code == 404, response.text


class TestSubscriptionSummary:
    def _buy(self, api, admin_account, user, instrument, subscription, qty):
        return api.post(
            f"/portfolio/admin/buy/{user['id']}",
            json={
                "instrument_id": instrument["id"],
                "quantity": qty,
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

    def _summary(self, api, user, subscription_id):
        response = api.get(
            "/subscription/summary", headers=_auth(user["token"])
        )
        assert response.status_code == 200, response.text
        return next(
            s
            for s in response.json()
            if s["subscription_id"] == subscription_id
        )

    def test_summary_of_fresh_subscription(
        self, api, funded_user, plan
    ):
        subscription = _subscribe(api, funded_user, plan, "100")

        summary = self._summary(api, funded_user, subscription["id"])

        assert float(summary["principal"]) == 100.0
        assert float(summary["current_value"]) == 100.0
        assert float(summary["profit_loss"]) == 0.0
        assert float(summary["roi_percent"]) == 0.0
        assert summary["status"] == "ACTIVE"

    def test_summary_marks_positions_to_market(
        self, api, admin_account, funded_user, plan, cheap_instrument
    ):
        subscription = _subscribe(api, funded_user, plan, "100")
        self._buy(
            api, admin_account, funded_user, cheap_instrument, subscription, "2"
        )

        # 90 pool + 2 units @ 5 = 100, unchanged
        summary = self._summary(api, funded_user, subscription["id"])
        assert float(summary["current_value"]) == 100.0

        # Move the market price to 7.50 -> 2 units now worth 15
        update = api.put(
            f"/instruments/{cheap_instrument['id']}",
            json={"current_price": "7.50"},
            headers=_auth(admin_account["token"]),
        )
        assert update.status_code == 200, update.text

        summary = self._summary(api, funded_user, subscription["id"])
        assert float(summary["current_value"]) == 105.0
        assert float(summary["profit_loss"]) == 5.0
        assert float(summary["roi_percent"]) == 5.0

    def test_summary_only_covers_active_subscriptions(
        self, api, funded_user, plan
    ):
        subscription = _subscribe(api, funded_user, plan, "100")

        api.post(
            f"/subscription/cancel/{subscription['id']}",
            headers=_auth(funded_user["token"]),
        )

        response = api.get(
            "/subscription/summary", headers=_auth(funded_user["token"])
        )

        assert response.status_code == 200, response.text
        assert response.json() == []


class TestSubscriptionScopedSelling:
    def _buy(self, api, admin_account, user, instrument, subscription, qty):
        return api.post(
            f"/portfolio/admin/buy/{user['id']}",
            json={
                "instrument_id": instrument["id"],
                "quantity": qty,
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )

    def test_sell_cannot_exceed_subscription_holdings(
        self,
        api,
        admin_account,
        funded_user,
        plan,
        second_plan,
        cheap_instrument,
    ):
        sub_one = _subscribe(api, funded_user, plan, "100")
        sub_two = _subscribe(api, funded_user, second_plan, "100")

        # The user holds two units in total, but only one under sub_one.
        self._buy(api, admin_account, funded_user, cheap_instrument, sub_one, "1")
        self._buy(api, admin_account, funded_user, cheap_instrument, sub_two, "1")

        response = api.post(
            f"/portfolio/admin/sell/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
                "subscription_id": sub_one["id"],
            },
            headers=_auth(admin_account["token"]),
        )

        assert response.status_code == 400, response.text
        assert response.json()["detail"] == "Insufficient quantity."
        assert _pool(sub_one["id"]) == 95.0
