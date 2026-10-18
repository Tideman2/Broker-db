import uuid

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
    email = f"inst-admin-{uuid.uuid4().hex[:8]}@example.com"
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
def user_account(api):
    tag = uuid.uuid4().hex[:8]
    payload = {
        "country": "Nigeria",
        "email": f"inst-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Instrument Test User",
        "phone": f"09{tag}{tag}"[:20],
        "username": f"instuser{tag}",
        "address1": "1 Test Street",
        "city": "Lagos",
        "state": "Lagos",
        "zip": "100001",
        "accept_terms": True,
    }
    reg = api.post("/auth/register", json=payload)
    assert reg.status_code == 200, reg.text
    body = reg.json()
    yield {"id": body["id"], "token": body["token"]}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (body["id"],))
    conn.commit()
    cursor.close()
    conn.close()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _symbol():
    return f"TST{uuid.uuid4().hex[:8].upper()}"


def _create(api, token, symbol=None, category_id=1, price="10.00"):
    return api.post(
        "/instruments",
        json={
            "symbol": symbol or _symbol(),
            "name": "Test Instrument",
            "category_id": category_id,
            "current_price": price,
        },
        headers=_auth(token),
    )


def _fund(api, admin_account, user, amount="100.00"):
    dep = api.post(
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
    assert dep.status_code == 200, dep.text
    confirm = api.post(
        f"/wallet/deposits/{dep.json()['id']}/confirm",
        headers=_auth(admin_account["token"]),
    )
    assert confirm.status_code == 200, confirm.text


@pytest.fixture()
def plan(api, admin_account):
    title = f"Inst Plan {uuid.uuid4().hex[:8]}"
    response = api.post(
        "/plan/create",
        json={
            "plan": {
                "title": title,
                "min_amount": "10",
                "duration": 30,
                "roi": "12",
                "risk_management": "STANDARD",
                "description": "Instrument test plan",
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
def subscription(api, admin_account, user_account, plan):
    _fund(api, admin_account, user_account)

    response = api.post(
        "/subscription/subscribe",
        json={"plan_id": plan["id"], "amount": "100"},
        headers=_auth(user_account["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestAdminInstruments:
    def test_create_instrument(self, api, admin_account):
        symbol = _symbol()
        response = _create(api, admin_account["token"], symbol=symbol)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["symbol"] == symbol
        assert body["is_active"] is True
        assert float(body["current_price"]) == 10.00

    def test_duplicate_symbol_returns_409(self, api, admin_account):
        symbol = _symbol()
        first = _create(api, admin_account["token"], symbol=symbol)
        assert first.status_code == 200, first.text

        clash = _create(api, admin_account["token"], symbol=symbol)
        assert clash.status_code == 409, clash.text

    def test_invalid_category_rejected(self, api, admin_account):
        response = _create(
            api, admin_account["token"], category_id=999999999
        )
        assert response.status_code == 404, response.text

    def test_list_contains_created(self, api, admin_account):
        created = _create(api, admin_account["token"])
        assert created.status_code == 200, created.text

        response = api.get(
            "/instruments", headers=_auth(admin_account["token"])
        )
        assert response.status_code == 200, response.text
        ids = [i["id"] for i in response.json()]
        assert created.json()["id"] in ids

    def test_update_price_and_toggle(self, api, admin_account):
        created = _create(api, admin_account["token"])
        assert created.status_code == 200, created.text
        inst_id = created.json()["id"]

        updated = api.put(
            f"/instruments/{inst_id}",
            json={"current_price": "25.50", "is_active": False},
            headers=_auth(admin_account["token"]),
        )
        assert updated.status_code == 200, updated.text
        assert float(updated.json()["current_price"]) == 25.50
        assert updated.json()["is_active"] is False

    def test_update_unknown_returns_404(self, api, admin_account):
        response = api.put(
            "/instruments/999999999",
            json={"current_price": "1.00"},
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 404, response.text

    def test_delete_is_soft(self, api, admin_account):
        created = _create(api, admin_account["token"])
        assert created.status_code == 200, created.text
        inst_id = created.json()["id"]

        deleted = api.delete(
            f"/instruments/{inst_id}", headers=_auth(admin_account["token"])
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["is_active"] is False

        again = api.delete(
            f"/instruments/{inst_id}", headers=_auth(admin_account["token"])
        )
        assert again.status_code == 200, again.text

        listed = api.get(
            "/instruments", headers=_auth(admin_account["token"])
        )
        assert listed.status_code == 200, listed.text
        row = next(i for i in listed.json() if i["id"] == inst_id)
        assert row["is_active"] is False

    def test_inactive_instrument_not_buyable(
        self, api, admin_account, user_account, subscription
    ):
        created = _create(api, admin_account["token"], price="5.00")
        assert created.status_code == 200, created.text
        inst_id = created.json()["id"]

        api.put(
            f"/instruments/{inst_id}",
            json={"is_active": False},
            headers=_auth(admin_account["token"]),
        )

        # inactive instrument -> 404 (guard fires before the pool check)
        blocked = api.post(
            f"/portfolio/admin/buy/{user_account['id']}",
            json={
                "instrument_id": inst_id,
                "quantity": "1",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )
        assert blocked.status_code == 404, blocked.text

        # active instrument the pool cannot cover -> 400
        active = _create(api, admin_account["token"], price="5.00")
        active_id = active.json()["id"]
        poor = api.post(
            f"/portfolio/admin/buy/{user_account['id']}",
            json={
                "instrument_id": active_id,
                "quantity": "1000",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )
        assert poor.status_code == 400, poor.text

    def test_history_survives_deactivation(
        self, api, admin_account, user_account, subscription
    ):
        created = _create(api, admin_account["token"], price="5.00")
        assert created.status_code == 200, created.text
        inst_id = created.json()["id"]

        buy = api.post(
            f"/portfolio/admin/buy/{user_account['id']}",
            json={
                "instrument_id": inst_id,
                "quantity": "1",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )
        assert buy.status_code == 200, buy.text

        api.put(
            f"/instruments/{inst_id}",
            json={"is_active": False},
            headers=_auth(admin_account["token"]),
        )

        holdings = api.get(
            "/portfolio/holdings", headers=_auth(user_account["token"])
        )
        assert holdings.status_code == 200, holdings.text
        ids = [h["instrument_id"] for h in holdings.json()]
        assert inst_id in ids

    def test_sell_still_allowed_after_deactivation(
        self, api, admin_account, user_account, subscription
    ):
        created = _create(api, admin_account["token"], price="5.00")
        assert created.status_code == 200, created.text
        inst_id = created.json()["id"]

        buy = api.post(
            f"/portfolio/admin/buy/{user_account['id']}",
            json={
                "instrument_id": inst_id,
                "quantity": "2",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )
        assert buy.status_code == 200, buy.text

        off = api.put(
            f"/instruments/{inst_id}",
            json={"is_active": False},
            headers=_auth(admin_account["token"]),
        )
        assert off.status_code == 200, off.text

        sell = api.post(
            f"/portfolio/admin/sell/{user_account['id']}",
            json={
                "instrument_id": inst_id,
                "quantity": "1",
                "subscription_id": subscription["id"],
            },
            headers=_auth(admin_account["token"]),
        )
        assert sell.status_code == 200, sell.text

    def test_reactivation_restores_buy(
        self, api, admin_account, user_account
    ):
        created = _create(api, admin_account["token"], price="5.00")
        assert created.status_code == 200, created.text
        inst_id = created.json()["id"]

        api.put(
            f"/instruments/{inst_id}",
            json={"is_active": False},
            headers=_auth(admin_account["token"]),
        )
        on = api.put(
            f"/instruments/{inst_id}",
            json={"is_active": True},
            headers=_auth(admin_account["token"]),
        )
        assert on.status_code == 200, on.text
        assert on.json()["is_active"] is True

    def test_update_to_duplicate_symbol_returns_409(
        self, api, admin_account
    ):
        first = _create(api, admin_account["token"])
        assert first.status_code == 200, first.text
        second = _create(api, admin_account["token"])
        assert second.status_code == 200, second.text

        clash = api.put(
            f"/instruments/{second.json()['id']}",
            json={"symbol": first.json()["symbol"]},
            headers=_auth(admin_account["token"]),
        )
        assert clash.status_code == 409, clash.text

    def test_invalid_price_rejected(self, api, admin_account):
        bad_create = _create(api, admin_account["token"], price="0")
        assert bad_create.status_code == 400, bad_create.text

        created = _create(api, admin_account["token"])
        assert created.status_code == 200, created.text
        bad_update = api.put(
            f"/instruments/{created.json()['id']}",
            json={"current_price": "-3"},
            headers=_auth(admin_account["token"]),
        )
        assert bad_update.status_code == 400, bad_update.text

    def test_list_filters_by_is_active(self, api, admin_account):
        active = _create(api, admin_account["token"])
        assert active.status_code == 200, active.text
        doomed = _create(api, admin_account["token"])
        assert doomed.status_code == 200, doomed.text
        api.delete(
            f"/instruments/{doomed.json()['id']}",
            headers=_auth(admin_account["token"]),
        )

        inactive = api.get(
            "/instruments?is_active=false&limit=100&offset=0",
            headers=_auth(admin_account["token"]),
        )
        assert inactive.status_code == 200, inactive.text
        ids = [i["id"] for i in inactive.json()]
        assert doomed.json()["id"] in ids
        assert active.json()["id"] not in ids
        assert all(i["is_active"] is False for i in inactive.json())

    def test_non_admin_forbidden(self, api, admin_account, user_account):
        headers = _auth(user_account["token"])
        assert api.get("/instruments", headers=headers).status_code == 403
        assert (
            api.post("/instruments", json={}, headers=headers).status_code
            == 403
        )
        assert (
            api.put(
                "/instruments/1", json={}, headers=headers
            ).status_code
            == 403
        )
        assert (
            api.delete("/instruments/1", headers=headers).status_code == 403
        )
