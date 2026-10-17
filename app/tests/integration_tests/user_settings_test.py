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
