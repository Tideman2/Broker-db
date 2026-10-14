import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def api():
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def admin_account(api):
    email = f"ppl-admin-{uuid.uuid4().hex[:8]}@example.com"
    response = api.post(
        "/admin/register", json={"email": email, "password": "Password123"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    yield {"id": body["id"], "email": email, "token": body["token"]}


@pytest.fixture()
def user_account(api):
    from app.db.connection import get_connection

    tag = uuid.uuid4().hex[:8]
    payload = {
        "country": "Nigeria",
        "email": f"ppl-user-{tag}@example.com",
        "password": "Password123",
        "full_name": "People Test User",
        "phone": "08000000000",
        "username": f"ppluser{tag}",
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


class TestAdminPeople:
    def test_list_users_contains_seeded_user(
        self, api, admin_account, user_account
    ):
        response = api.get(
            "/admin/users?limit=10&offset=0",
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 200, response.text
        ids = [u["id"] for u in response.json()]
        assert user_account["id"] in ids

    def test_get_user_by_id(self, api, admin_account, user_account):
        response = api.get(
            f"/admin/users/{user_account['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 200, response.text
        assert response.json()["email"] == user_account["email"]

    def test_get_unknown_user_returns_404(self, api, admin_account):
        response = api.get(
            "/admin/users/999999999", headers=_auth(admin_account["token"])
        )
        assert response.status_code == 404, response.text

    def test_delete_user_removes_row(self, api, admin_account, user_account):
        response = api.delete(
            f"/admin/users/{user_account['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 200, response.text

        gone = api.get(
            f"/admin/users/{user_account['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert gone.status_code == 404, gone.text

    def test_deleted_user_refresh_rejected(
        self, api, admin_account, user_account
    ):
        delete = api.delete(
            f"/admin/users/{user_account['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert delete.status_code == 200, delete.text

        refresh = api.post(
            "/auth/refresh", json={"token": user_account["refresh_token"]}
        )
        assert refresh.status_code == 401, refresh.text

    def test_deleted_admin_refresh_rejected(self, api, admin_account):
        second = api.post(
            "/admin/register",
            json={
                "email": f"ppl-doomed3-{uuid.uuid4().hex[:8]}@example.com",
                "password": "Password123",
            },
        )
        assert second.status_code == 200, second.text
        doomed_refresh = second.json()["refresh_token"]

        api.delete(
            f"/admin/{second.json()['id']}",
            headers=_auth(admin_account["token"]),
        )

        refresh = api.post("/admin/refresh", json={"token": doomed_refresh})
        assert refresh.status_code == 401, refresh.text

    def test_logout_rejects_refresh(self, api, admin_account):
        session = api.post(
            "/admin/login",
            json={"email": admin_account["email"], "password": "Password123"},
        ).json()

        logout = api.post("/admin/logout", headers=_auth(session["token"]))
        assert logout.status_code == 200, logout.text

        refresh = api.post(
            "/admin/refresh", json={"token": session["refresh_token"]}
        )
        assert refresh.status_code == 401, refresh.text

    def test_password_change_rejects_old_refresh(self, api, admin_account):
        session = api.post(
            "/admin/login",
            json={"email": admin_account["email"], "password": "Password123"},
        ).json()

        response = api.patch(
            f"/admin/{admin_account['id']}",
            json={"password": "ChangedPass321"},
            headers=_auth(session["token"]),
        )
        assert response.status_code == 200, response.text

        refresh = api.post(
            "/admin/refresh", json={"token": session["refresh_token"]}
        )
        assert refresh.status_code == 401, refresh.text

    def test_addressless_user_returns_nulls(
        self, api, admin_account, user_account
    ):
        from app.db.connection import get_connection

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_addresses WHERE user_id = %s",
            (user_account["id"],),
        )
        conn.commit()
        cursor.close()
        conn.close()

        response = api.get(
            f"/admin/users/{user_account['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 200, response.text
        assert response.json()["address1"] is None

    def test_admin_refresh_rejected_on_user_endpoint(
        self, api, admin_account
    ):
        session = api.post(
            "/admin/login",
            json={"email": admin_account["email"], "password": "Password123"},
        ).json()

        replay = api.post(
            "/auth/refresh", json={"token": session["refresh_token"]}
        )
        assert replay.status_code == 403, replay.text

    def test_duplicate_admin_register_returns_409(self, api, admin_account):
        clash = api.post(
            "/admin/register",
            json={"email": admin_account["email"], "password": "Password123"},
        )
        assert clash.status_code == 409, clash.text

    def test_admin_register_rejects_invalid_email(self, api):
        response = api.post(
            "/admin/register",
            json={"email": "not-an-email", "password": "Password123"},
        )
        assert response.status_code == 422, response.text

    def test_non_admin_forbidden_on_people_routes(
        self, api, admin_account, user_account
    ):
        headers = _auth(user_account["token"])
        assert api.get("/admin/users", headers=headers).status_code == 403
        assert (
            api.get(
                f"/admin/users/{user_account['id']}", headers=headers
            ).status_code
            == 403
        )
        assert (
            api.delete(
                f"/admin/users/{user_account['id']}", headers=headers
            ).status_code
            == 403
        )
        assert api.get("/admin/list", headers=headers).status_code == 403

    def test_list_admins_contains_seeded_admin(self, api, admin_account):
        response = api.get(
            "/admin/list", headers=_auth(admin_account["token"])
        )
        assert response.status_code == 200, response.text
        ids = [a["id"] for a in response.json()]
        assert admin_account["id"] in ids

    def test_update_admin_email_and_password(self, api, admin_account):
        new_email = f"ppl-renamed-{uuid.uuid4().hex[:8]}@example.com"
        response = api.patch(
            f"/admin/{admin_account['id']}",
            json={"email": new_email, "password": "RenamedPass789"},
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 200, response.text
        assert response.json()["email"] == new_email

        login = api.post(
            "/admin/login",
            json={"email": new_email, "password": "RenamedPass789"},
        )
        assert login.status_code == 200, login.text

    def test_admin_cannot_delete_self(self, api, admin_account):
        response = api.delete(
            f"/admin/{admin_account['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert response.status_code == 400, response.text

    def test_deleted_user_session_revoked(
        self, api, admin_account, user_account
    ):
        me = api.get(
            "/auth/user",
            headers=_auth(user_account["token"]),
        )
        assert me.status_code == 200, me.text

        delete = api.delete(
            f"/admin/users/{user_account['id']}",
            headers=_auth(admin_account["token"]),
        )
        assert delete.status_code == 200, delete.text

        revoked = api.get(
            "/auth/user",
            headers=_auth(user_account["token"]),
        )
        assert revoked.status_code == 401, revoked.text

    def test_deleted_admin_session_revoked(self, api, admin_account):
        second = api.post(
            "/admin/register",
            json={
                "email": f"ppl-doomed2-{uuid.uuid4().hex[:8]}@example.com",
                "password": "Password123",
            },
        )
        assert second.status_code == 200, second.text
        doomed_token = second.json()["token"]
        doomed_id = second.json()["id"]

        assert (
            api.get("/admin/me", headers=_auth(doomed_token)).status_code
            == 200
        )

        delete = api.delete(
            f"/admin/{doomed_id}", headers=_auth(admin_account["token"])
        )
        assert delete.status_code == 200, delete.text

        revoked = api.get("/admin/me", headers=_auth(doomed_token))
        assert revoked.status_code == 401, revoked.text

    def test_password_change_revokes_old_session(self, api, admin_account):
        old_token = admin_account["token"]

        response = api.patch(
            f"/admin/{admin_account['id']}",
            json={"password": "ChangedPass321"},
            headers=_auth(old_token),
        )
        assert response.status_code == 200, response.text

        revoked = api.get("/admin/me", headers=_auth(old_token))
        assert revoked.status_code == 401, revoked.text

        login = api.post(
            "/admin/login",
            json={
                "email": response.json()["email"],
                "password": "ChangedPass321",
            },
        )
        assert login.status_code == 200, login.text

    def test_update_admin_duplicate_email_returns_409(
        self, api, admin_account
    ):
        second = api.post(
            "/admin/register",
            json={
                "email": f"ppl-clash-{uuid.uuid4().hex[:8]}@example.com",
                "password": "Password123",
            },
        )
        assert second.status_code == 200, second.text
        try:
            clash = api.patch(
                f"/admin/{second.json()['id']}",
                json={"email": admin_account["email"]},
                headers=_auth(admin_account["token"]),
            )
            assert clash.status_code == 409, clash.text
        finally:
            api.delete(
                f"/admin/{second.json()['id']}",
                headers=_auth(admin_account["token"]),
            )

    def test_delete_other_admin(self, api, admin_account):
        second = api.post(
            "/admin/register",
            json={
                "email": f"ppl-doomed-{uuid.uuid4().hex[:8]}@example.com",
                "password": "Password123",
            },
        )
        assert second.status_code == 200, second.text
        doomed_id = second.json()["id"]

        response = api.delete(
            f"/admin/{doomed_id}", headers=_auth(admin_account["token"])
        )
        assert response.status_code == 200, response.text

        listed = api.get(
            "/admin/list", headers=_auth(admin_account["token"])
        )
        assert listed.status_code == 200, listed.text
        assert doomed_id not in [a["id"] for a in listed.json()]
