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
    email = f"dest-admin-{uuid.uuid4().hex[:8]}@example.com"
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
def make_user(api):
    created = []

    def _make():
        tag = uuid.uuid4().hex[:8]
        payload = {
            "country": "Nigeria",
            "email": f"dest-user-{tag}@example.com",
            "password": "Password123",
            "full_name": "Destination Test User",
            "phone": f"08{tag}{tag}"[:20],
            "username": f"destuser{tag}",
            "address1": "1 Test Street",
            "city": "Lagos",
            "state": "Lagos",
            "zip": "100001",
            "accept_terms": True,
        }
        response = api.post("/auth/register", json=payload)
        assert response.status_code == 200, response.text
        body = response.json()
        created.append(body["id"])
        return {"id": body["id"], "token": body["token"]}

    yield _make

    conn = get_connection()
    cursor = conn.cursor()
    for user_id in created:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()


def _add_bank_destination(api, user, label="Test Bank"):
    response = api.post(
        "/user/bank/add",
        json={
            "destination_details": {"label": label, "type": "BANK"},
            "bank_destination": {
                "bank_name": "Test Bank",
                "account_name": "Destination Test User",
                "account_number": uuid.uuid4().hex[:12],
            },
        },
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _add_crypto_destination(api, user, label="Test Wallet"):
    response = api.post(
        "/user/crypto/add",
        json={
            "destination_details": {"label": label, "type": "CRYPTO"},
            "crypto_destination": {
                "asset_id": 1,
                "address": f"0x{uuid.uuid4().hex}",
            },
        },
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _fund(api, admin_account, user, amount="1000.00"):
    deposit = api.post(
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
    assert deposit.status_code == 200, deposit.text

    confirmed = api.post(
        f"/wallet/deposits/{deposit.json()['id']}/confirm",
        headers=_auth(admin_account["token"]),
    )
    assert confirmed.status_code == 200, confirmed.text


def _withdraw(api, user, destination, amount="10.00"):
    response = api.post(
        "/wallet/withdraw",
        json={"amount": amount, "destination_id": destination["id"]},
        headers=_auth(user["token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _confirm_withdrawal(api, admin_account, withdrawal_id):
    response = api.post(
        f"/wallet/withdrawals/{withdrawal_id}/confirm",
        headers=_auth(admin_account["token"]),
    )
    assert response.status_code == 200, response.text


def _reject_withdrawal(api, admin_account, withdrawal_id):
    response = api.post(
        f"/wallet/withdrawals/{withdrawal_id}/reject",
        headers=_auth(admin_account["token"]),
    )
    assert response.status_code == 200, response.text


class TestUpdateWithdrawDestination:
    def test_updates_bank_destination_label(self, api, make_user):
        user = make_user()
        destination = _add_bank_destination(api, user)

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={"label": "Renamed Bank"},
            headers=_auth(user["token"]),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["label"] == "Renamed Bank"
        assert body["bank_name"] == destination["bank_name"]

        listed = api.get(
            "/user/withdraw-destinations", headers=_auth(user["token"])
        )
        assert listed.status_code == 200, listed.text
        assert [item["label"] for item in listed.json()] == ["Renamed Bank"]

    def test_updates_bank_destination_details(self, api, make_user):
        user = make_user()
        destination = _add_bank_destination(api, user)

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={
                "bank_destination": {
                    "bank_name": "Updated Bank",
                    "account_name": "Updated Name",
                    "account_number": "9998887776",
                }
            },
            headers=_auth(user["token"]),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["bank_name"] == "Updated Bank"
        assert body["account_name"] == "Updated Name"
        assert body["account_number"] == "9998887776"

    def test_updates_crypto_destination_details(self, api, make_user):
        user = make_user()
        destination = _add_crypto_destination(api, user)
        new_address = f"0x{uuid.uuid4().hex}"

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={
                "crypto_destination": {
                    "asset_id": 2,
                    "address": new_address,
                }
            },
            headers=_auth(user["token"]),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["asset_id"] == 2
        assert body["address"] == new_address

    def test_rejects_crypto_details_for_bank_destination(
        self, api, make_user
    ):
        user = make_user()
        destination = _add_bank_destination(api, user)

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={
                "crypto_destination": {
                    "asset_id": 2,
                    "address": f"0x{uuid.uuid4().hex}",
                }
            },
            headers=_auth(user["token"]),
        )

        assert response.status_code == 400, response.text

    def test_rejects_duplicate_label(self, api, make_user):
        user = make_user()
        first = _add_bank_destination(api, user, label="First")
        second = _add_bank_destination(api, user, label="Second")

        response = api.patch(
            f"/user/withdraw-destinations/{second['id']}",
            json={"label": first["label"]},
            headers=_auth(user["token"]),
        )

        assert response.status_code == 409, response.text

    def test_allows_keeping_the_same_label(self, api, make_user):
        user = make_user()
        destination = _add_bank_destination(api, user)

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={"label": destination["label"]},
            headers=_auth(user["token"]),
        )

        assert response.status_code == 200, response.text

    def test_rejects_empty_payload(self, api, make_user):
        user = make_user()
        destination = _add_bank_destination(api, user)

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={},
            headers=_auth(user["token"]),
        )

        assert response.status_code == 400, response.text

    def test_rejects_updating_another_users_destination(
        self, api, make_user
    ):
        owner = make_user()
        other = make_user()
        destination = _add_bank_destination(api, owner)

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={"label": "Stolen"},
            headers=_auth(other["token"]),
        )

        assert response.status_code == 404, response.text

    def test_allows_edit_after_confirmed_withdrawal(
        self, api, admin_account, make_user
    ):
        user = make_user()
        destination = _add_bank_destination(api, user)
        _fund(api, admin_account, user)
        withdrawal = _withdraw(api, user, destination)
        _confirm_withdrawal(api, admin_account, withdrawal["id"])

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={"label": "Renamed"},
            headers=_auth(user["token"]),
        )

        assert response.status_code == 200, response.text

    def test_rejects_edit_while_withdrawal_is_pending(
        self, api, admin_account, make_user
    ):
        user = make_user()
        destination = _add_bank_destination(api, user)
        _fund(api, admin_account, user)
        _withdraw(api, user, destination)

        response = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={"label": "Renamed"},
            headers=_auth(user["token"]),
        )

        assert response.status_code == 409, response.text


class TestDeleteWithdrawDestination:
    def test_deletes_unused_destination(self, api, make_user):
        user = make_user()
        destination = _add_bank_destination(api, user)

        response = api.delete(
            f"/user/withdraw-destinations/{destination['id']}",
            headers=_auth(user["token"]),
        )

        assert response.status_code == 204, response.text

        listed = api.get(
            "/user/withdraw-destinations", headers=_auth(user["token"])
        )
        assert listed.status_code == 200, listed.text
        assert listed.json() == []

    def test_blocks_delete_when_withdrawal_is_pending(
        self, api, admin_account, make_user
    ):
        user = make_user()
        destination = _add_bank_destination(api, user)
        _fund(api, admin_account, user)
        _withdraw(api, user, destination)

        response = api.delete(
            f"/user/withdraw-destinations/{destination['id']}",
            headers=_auth(user["token"]),
        )

        assert response.status_code == 409, response.text

    def test_blocks_delete_when_withdrawal_is_confirmed(
        self, api, admin_account, make_user
    ):
        user = make_user()
        destination = _add_bank_destination(api, user)
        _fund(api, admin_account, user)
        withdrawal = _withdraw(api, user, destination)
        _confirm_withdrawal(api, admin_account, withdrawal["id"])

        response = api.delete(
            f"/user/withdraw-destinations/{destination['id']}",
            headers=_auth(user["token"]),
        )

        assert response.status_code == 409, response.text

    def test_blocks_delete_when_withdrawal_is_rejected(
        self, api, admin_account, make_user
    ):
        user = make_user()
        destination = _add_bank_destination(api, user)
        _fund(api, admin_account, user)
        withdrawal = _withdraw(api, user, destination)
        _reject_withdrawal(api, admin_account, withdrawal["id"])

        response = api.delete(
            f"/user/withdraw-destinations/{destination['id']}",
            headers=_auth(user["token"]),
        )

        assert response.status_code == 409, response.text

    def test_rejects_deleting_another_users_destination(
        self, api, make_user
    ):
        owner = make_user()
        other = make_user()
        destination = _add_bank_destination(api, owner)

        response = api.delete(
            f"/user/withdraw-destinations/{destination['id']}",
            headers=_auth(other["token"]),
        )

        assert response.status_code == 404, response.text


class TestDestinationAuthorization:
    def test_requires_authentication(self, api, make_user):
        user = make_user()
        destination = _add_bank_destination(api, user)

        update = api.patch(
            f"/user/withdraw-destinations/{destination['id']}",
            json={"label": "Renamed"},
        )
        delete = api.delete(
            f"/user/withdraw-destinations/{destination['id']}"
        )

        assert update.status_code == 401
        assert delete.status_code == 401

    def test_withdrawal_rejects_another_users_destination(
        self, api, admin_account, make_user
    ):
        owner = make_user()
        other = make_user()
        destination = _add_bank_destination(api, owner)
        _fund(api, admin_account, other)

        response = api.post(
            "/wallet/withdraw",
            json={"amount": "10.00", "destination_id": destination["id"]},
            headers=_auth(other["token"]),
        )

        assert response.status_code == 404, response.text
