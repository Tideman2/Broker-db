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
        "country": "United States",
        "email": f"settings-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "Settings Test User",
        "phone": f"0800{tag[:7]}",
        "username": f"settingsuser{tag}",
        "address1": "1 Settings Street",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
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


class TestValidationErrorShape:
    def test_validation_error_detail_is_a_string(self, api):
        response = api.post("/auth/login", json={"email": "not-an-email"})

        assert response.status_code == 422, response.text
        body = response.json()
        assert isinstance(body["detail"], str), body


class TestProfileName:
    def test_patch_name_updates_profile(self, api, user_account):
        response = api.patch(
            "/auth/user",
            json={"full_name": "Jane Updated"},
            headers=_auth(user_account["token"]),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["full_name"] == "Jane Updated"
        assert body["id"] == user_account["id"]
        assert body["email"] == user_account["email"]
        assert body["role"] == "USER"

    def test_patch_name_is_persisted(self, api, user_account):
        api.patch(
            "/auth/user",
            json={"full_name": "Persisted Name"},
            headers=_auth(user_account["token"]),
        )

        fetched = api.get("/auth/user", headers=_auth(user_account["token"]))

        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["full_name"] == "Persisted Name"

    def test_patch_name_trims_whitespace(self, api, user_account):
        response = api.patch(
            "/auth/user",
            json={"full_name": "  Jane Trimmed  "},
            headers=_auth(user_account["token"]),
        )

        assert response.status_code == 200, response.text
        assert response.json()["full_name"] == "Jane Trimmed"

    def test_patch_blank_name_is_rejected(self, api, user_account):
        response = api.patch(
            "/auth/user",
            json={"full_name": "   "},
            headers=_auth(user_account["token"]),
        )

        assert response.status_code == 422, response.text
        assert response.json() == {
            "detail": "full_name: Full name cannot be blank."
        }

    def test_patch_name_requires_auth(self, api):
        response = api.patch("/auth/user", json={"full_name": "No Auth"})

        assert response.status_code in (401, 403), response.text


class TestChangePassword:
    def test_change_password_succeeds(self, api, user_account):
        response = api.post(
            "/auth/change-password",
            json={
                "current_password": user_account["password"],
                "new_password": "NewPassword456",
            },
            headers=_auth(user_account["token"]),
        )

        assert response.status_code == 200, response.text
        assert response.json() == {"message": "Password updated."}

    def test_new_password_works_and_old_password_fails(self, api, user_account):
        api.post(
            "/auth/change-password",
            json={
                "current_password": user_account["password"],
                "new_password": "NewPassword456",
            },
            headers=_auth(user_account["token"]),
        )

        old_login = api.post(
            "/auth/login",
            json={
                "email": user_account["email"],
                "password": user_account["password"],
            },
        )
        new_login = api.post(
            "/auth/login",
            json={
                "email": user_account["email"],
                "password": "NewPassword456",
            },
        )

        assert old_login.status_code == 401, old_login.text
        assert new_login.status_code == 200, new_login.text

    def test_change_password_revokes_current_session(self, api, user_account):
        api.post(
            "/auth/change-password",
            json={
                "current_password": user_account["password"],
                "new_password": "NewPassword456",
            },
            headers=_auth(user_account["token"]),
        )

        revoked = api.get(
            "/auth/user", headers=_auth(user_account["token"])
        )

        assert revoked.status_code == 401, revoked.text

    def test_change_password_revokes_refresh_token(self, api, user_account):
        api.post(
            "/auth/change-password",
            json={
                "current_password": user_account["password"],
                "new_password": "NewPassword456",
            },
            headers=_auth(user_account["token"]),
        )

        refresh = api.post(
            "/auth/refresh", json={"token": user_account["refresh_token"]}
        )

        assert refresh.status_code == 401, refresh.text

    def test_wrong_current_password_is_rejected(self, api, user_account):
        response = api.post(
            "/auth/change-password",
            json={
                "current_password": "WrongPassword123",
                "new_password": "NewPassword456",
            },
            headers=_auth(user_account["token"]),
        )

        assert response.status_code == 400, response.text
        assert response.json() == {
            "detail": "Current password is incorrect."
        }

    def test_short_new_password_is_rejected(self, api, user_account):
        response = api.post(
            "/auth/change-password",
            json={
                "current_password": user_account["password"],
                "new_password": "short",
            },
            headers=_auth(user_account["token"]),
        )

        assert response.status_code == 422, response.text
        assert isinstance(response.json()["detail"], str), response.json()

    def test_change_password_requires_auth(self, api):
        response = api.post(
            "/auth/change-password",
            json={
                "current_password": "Password123",
                "new_password": "NewPassword456",
            },
        )

        assert response.status_code in (401, 403), response.text
