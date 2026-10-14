import os
import uuid

import pytest
import redis as sync_redis
from fastapi.testclient import TestClient

from app.main import app
from app.db.connection import get_connection
from app.utils.otp import generate_otp


def _unique_email(prefix="admin"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture()
def api():
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def redis_reader():
    return sync_redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True,
    )


@pytest.fixture()
def admin_account(api):
    email = _unique_email()
    password = "Password123"
    response = api.post(
        "/admin/register", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    yield {
        "id": body["id"],
        "email": email,
        "password": password,
        "token": body["token"],
        "refresh_token": body.get("refresh_token"),
    }
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE id = %s", (body["id"],))
    conn.commit()
    cursor.close()
    conn.close()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestAdminAuthParity:
    def test_register_returns_access_and_refresh_tokens(self, admin_account):
        assert admin_account["token"]
        assert admin_account["refresh_token"]

    def test_me_returns_current_admin(self, api, admin_account):
        response = api.get("/admin/me", headers=_auth(admin_account["token"]))
        assert response.status_code == 200, response.text
        assert response.json()["email"] == admin_account["email"]

    def test_me_rejects_anonymous(self, api):
        response = api.get("/admin/me")
        assert response.status_code in (401, 403)

    def test_refresh_issues_working_token(self, api, admin_account):
        response = api.post(
            "/admin/refresh", json={"token": admin_account["refresh_token"]}
        )
        assert response.status_code == 200, response.text
        new_token = response.json()["token"]
        me = api.get("/admin/me", headers=_auth(new_token))
        assert me.status_code == 200, me.text

    def test_full_password_reset_loop(self, api, admin_account, redis_reader):
        email = admin_account["email"]

        forgot = api.post("/admin/forgot-password", json={"email": email})
        assert forgot.status_code == 200, forgot.text

        secret = redis_reader.get(f"user:{admin_account['id']}:otp:ADMIN")
        assert secret, "OTP secret was not stored for admin"

        verify = api.post(
            "/admin/verify-otp",
            json={"email": email, "otp": generate_otp(secret)},
        )
        assert verify.status_code == 200, verify.text
        reset_token = verify.json()["password_reset_token"]

        new_password = "NewPassword456"
        reset = api.post(
            "/admin/reset-password",
            json={
                "email": email,
                "new_password": new_password,
                "reset_token": reset_token,
            },
        )
        assert reset.status_code == 200, reset.text

        login = api.post(
            "/admin/login", json={"email": email, "password": new_password}
        )
        assert login.status_code == 200, login.text

    def test_logout_revokes_session(self, api, admin_account, redis_reader):
        response = api.post(
            "/admin/logout", headers=_auth(admin_account["token"])
        )
        assert response.status_code == 200, response.text

        stored = redis_reader.get(
            f"user:{admin_account['id']}:access_token:ADMIN"
        )
        assert stored is None

        me = api.get("/admin/me", headers=_auth(admin_account["token"]))
        assert me.status_code == 401, me.text
