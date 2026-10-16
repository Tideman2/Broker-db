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
def user_account(api):
    tag = uuid.uuid4().hex[:8]
    payload = {
        "country": "Nigeria",
        "email": f"logout-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Logout Test User",
        "phone": "08000000000",
        "username": f"logoutuser{tag}",
        "address1": "1 Test Street",
        "city": "Lagos",
        "state": "Lagos",
        "zip": "100001",
        "accept_terms": True,
    }
    reg = api.post("/auth/register", json=payload)
    assert reg.status_code == 200, reg.text
    body = reg.json()
    yield {
        "id": body["id"],
        "email": payload["email"],
        "password": payload["password"],
        "token": body["token"],
        "refresh_token": body.get("refresh_token"),
    }

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (body["id"],))
    conn.commit()
    cursor.close()
    conn.close()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestUserLogout:
    def test_register_returns_refresh_token(self, user_account):
        assert user_account["token"]
        assert user_account["refresh_token"]

    def test_logout_returns_200(self, api, user_account):
        response = api.post(
            "/auth/logout", headers=_auth(user_account["token"])
        )
        assert response.status_code == 200, response.text

    def test_access_revoked_after_logout(self, api, user_account):
        assert (
            api.get("/auth/user", headers=_auth(user_account["token"])).status_code
            == 200
        )

        api.post("/auth/logout", headers=_auth(user_account["token"]))

        revoked = api.get("/auth/user", headers=_auth(user_account["token"]))
        assert revoked.status_code == 401, revoked.text

    def test_refresh_revoked_after_logout(self, api, user_account):
        api.post("/auth/logout", headers=_auth(user_account["token"]))

        refresh = api.post(
            "/auth/refresh", json={"token": user_account["refresh_token"]}
        )
        assert refresh.status_code == 401, refresh.text

    def test_fresh_login_works_after_logout(self, api, user_account):
        api.post("/auth/logout", headers=_auth(user_account["token"]))

        login = api.post(
            "/auth/login",
            json={
                "email": user_account["email"],
                "password": user_account["password"],
            },
        )
        assert login.status_code == 200, login.text
        me = api.get(
            "/auth/user", headers=_auth(login.json()["token"])
        )
        assert me.status_code == 200, me.text

    def test_logout_requires_auth(self, api):
        response = api.post("/auth/logout")
        assert response.status_code in (401, 403), response.text
