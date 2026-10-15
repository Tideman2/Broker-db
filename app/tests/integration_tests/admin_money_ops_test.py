import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.connection import get_connection

client_context = TestClient


@pytest.fixture()
def api():
    with client_context(app) as client:
        yield client


@pytest.fixture()
def admin_account(api):
    email = f"ops-admin-{uuid.uuid4().hex[:8]}@example.com"
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
    """Registers a user, deposits 100 and has admin confirm it."""
    tag = uuid.uuid4().hex[:8]
    payload = {
        "country": "Nigeria",
        "email": f"ops-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Ops Test User",
        "phone": "08000000000",
        "username": f"opsuser{tag}",
        "address1": "1 Test Street",
        "city": "Lagos",
        "state": "Lagos",
        "zip": "100001",
        "accept_terms": True,
    }
    reg = api.post("/auth/register", json=payload)
    assert reg.status_code == 200, reg.text
    user = {"id": reg.json()["id"], "token": reg.json()["token"]}

    dep = api.post(
        "/wallet/deposit",
        json={"deposit": {"amount": "100.00", "asset_id": 1, "payment_method": 1}},
        headers={"Authorization": f"Bearer {user['token']}"},
    )
    assert dep.status_code == 200, dep.text
    deposit_id = dep.json()["id"]

    conf = api.post(
        f"/wallet/deposits/{deposit_id}/confirm",
        headers={"Authorization": f"Bearer {admin_account['token']}"},
    )
    assert conf.status_code == 200, conf.text

    yield {**user, "deposit_id": deposit_id}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user["id"],))
    conn.commit()
    cursor.close()
    conn.close()


@pytest.fixture()
def pending_withdrawal(api, funded_user):
    """Creates a 40.00 pending withdrawal on the funded user."""
    tag = uuid.uuid4().hex[:8]
    dest = api.post(
        "/user/bank/add",
        json={
            "destination_details": {"label": f"ops-{tag}", "type": "BANK"},
            "bank_destination": {
                "bank_name": "Ops Bank",
                "account_name": "Ops Test User",
                "account_number": "0123456789",
            },
        },
        headers={"Authorization": f"Bearer {funded_user['token']}"},
    )
    assert dest.status_code == 200, dest.text

    wd = api.post(
        "/wallet/withdraw",
        json={"amount": "40.00", "destination_id": dest.json()["id"]},
        headers={"Authorization": f"Bearer {funded_user['token']}"},
    )
    assert wd.status_code == 200, wd.text
    assert wd.json()["status"] == "pending"
    return {"id": wd.json()["id"], "user_id": funded_user["id"]}


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


class TestAdminMoneyOps:
    def test_admin_lists_deposits_with_status_filter(
        self, api, admin_account, funded_user
    ):
        response = api.get(
            "/wallet/admin/deposits?status=pending&limit=10&offset=0",
            headers={"Authorization": f"Bearer {admin_account['token']}"},
        )
        assert response.status_code == 200, response.text
        # funded_user's deposit was confirmed, so seed a fresh pending one
        dep = api.post(
            "/wallet/deposit",
            json={
                "deposit": {
                    "amount": "10.00",
                    "asset_id": 1,
                    "payment_method": 1,
                }
            },
            headers={"Authorization": f"Bearer {funded_user['token']}"},
        )
        assert dep.status_code == 200, dep.text
        response = api.get(
            "/wallet/admin/deposits?status=pending&limit=10&offset=0",
            headers={"Authorization": f"Bearer {admin_account['token']}"},
        )
        assert response.status_code == 200, response.text
        ids = [d["id"] for d in response.json()]
        assert dep.json()["id"] in ids
        assert all(d["status"] == "pending" for d in response.json())

    def test_admin_lists_withdrawals_with_status_filter(
        self, api, admin_account, pending_withdrawal
    ):
        response = api.get(
            "/wallet/admin/withdrawals?status=pending&limit=10&offset=0",
            headers={"Authorization": f"Bearer {admin_account['token']}"},
        )
        assert response.status_code == 200, response.text
        ids = [w["id"] for w in response.json()]
        assert pending_withdrawal["id"] in ids

    def test_non_admin_forbidden_on_money_ops(
        self, api, funded_user, pending_withdrawal
    ):
        headers = {"Authorization": f"Bearer {funded_user['token']}"}
        assert (
            api.get("/wallet/admin/deposits", headers=headers).status_code
            == 403
        )
        assert (
            api.get("/wallet/admin/withdrawals", headers=headers).status_code
            == 403
        )
        assert (
            api.post(
                f"/wallet/withdrawals/{pending_withdrawal['id']}/confirm",
                headers=headers,
            ).status_code
            == 403
        )
        assert (
            api.post(
                f"/wallet/withdrawals/{pending_withdrawal['id']}/reject",
                headers=headers,
            ).status_code
            == 403
        )

    def test_confirm_withdrawal_consumes_locked(
        self, api, admin_account, pending_withdrawal
    ):
        before = _wallet(pending_withdrawal["user_id"])
        assert float(before["locked"]) == 40.0

        response = api.post(
            f"/wallet/withdrawals/{pending_withdrawal['id']}/confirm",
            headers={"Authorization": f"Bearer {admin_account['token']}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "confirmed"

        after = _wallet(pending_withdrawal["user_id"])
        assert float(after["locked"]) == 0.0
        assert float(after["available"]) == float(before["available"])

        again = api.post(
            f"/wallet/withdrawals/{pending_withdrawal['id']}/confirm",
            headers={"Authorization": f"Bearer {admin_account['token']}"},
        )
        assert again.status_code == 400, again.text

    def test_reject_withdrawal_restores_available(
        self, api, admin_account, pending_withdrawal
    ):
        response = api.post(
            f"/wallet/withdrawals/{pending_withdrawal['id']}/reject",
            headers={"Authorization": f"Bearer {admin_account['token']}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "rejected"

        wallet = _wallet(pending_withdrawal["user_id"])
        assert float(wallet["locked"]) == 0.0
        assert float(wallet["available"]) == 100.0
