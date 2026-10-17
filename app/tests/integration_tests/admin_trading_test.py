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
    email = f"trade-admin-{uuid.uuid4().hex[:8]}@example.com"
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
        "email": f"trade-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Trade Test User",
        "phone": f"08{tag}{tag}"[:20],
        "username": f"tradeuser{tag}",
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
def cheap_instrument(api, admin_account):
    symbol = f"TRD{uuid.uuid4().hex[:8].upper()}"
    response = api.post(
        "/instruments",
        json={
            "symbol": symbol,
            "name": "Trade Test Instrument",
            "category_id": 1,
            "current_price": "5.00",
        },
        headers=_auth(admin_account["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestAdminTrading:
    def test_admin_buys_on_behalf(
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
        assert response.status_code == 200, response.text
        assert response.json()["transaction_id"]

        holdings = api.get(
            "/portfolio/holdings", headers=_auth(funded_user["token"])
        )
        assert holdings.status_code == 200, holdings.text
        row = next(
            h
            for h in holdings.json()
            if h["instrument_id"] == cheap_instrument["id"]
        )
        assert float(row["net_quantity"]) == 2.0

    def test_admin_buy_unknown_user_returns_404(
        self, api, admin_account, cheap_instrument
    ):
        response = api.post(
            "/portfolio/admin/buy/999999999",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "1",
            },
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 404, response.text

    def test_admin_sells_on_behalf(
        self, api, admin_account, funded_user, cheap_instrument
    ):
        buy = api.post(
            f"/portfolio/admin/buy/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "2",
            },
            headers=_auth(admin_account["token"]),
        )
        assert buy.status_code == 200, buy.text

        sell = api.post(
            f"/portfolio/admin/sell/{funded_user['id']}",
            json={
                "instrument_id": cheap_instrument["id"],
                "quantity": "1",
            },
            headers=_auth(admin_account["token"]),
        )
        assert sell.status_code == 200, sell.text

        holdings = api.get(
            "/portfolio/holdings", headers=_auth(funded_user["token"])
        )
        assert holdings.status_code == 200, holdings.text
        row = next(
            h
            for h in holdings.json()
            if h["instrument_id"] == cheap_instrument["id"]
        )
        assert float(row["net_quantity"]) == 1.0

    def test_non_admin_forbidden(self, api, funded_user, cheap_instrument):
        headers = _auth(funded_user["token"])
        assert (
            api.post(
                f"/portfolio/admin/buy/{funded_user['id']}",
                json={
                    "instrument_id": cheap_instrument["id"],
                    "quantity": "1",
                },
                headers=headers,
            ).status_code
            == 403
        )
        assert (
            api.post(
                f"/portfolio/admin/sell/{funded_user['id']}",
                json={
                    "instrument_id": cheap_instrument["id"],
                    "quantity": "1",
                },
                headers=headers,
            ).status_code
            == 403
        )
