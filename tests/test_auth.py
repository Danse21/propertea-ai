import pytest

CREDS = {"username": "alice", "password": "hunter2hunter2"}


def test_register_returns_a_token(client):
    r = client.post("/auth/register", json=CREDS)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "alice"
    assert len(body["token"]) > 20
    assert "password" not in body and "password_hash" not in body


def test_duplicate_username_is_409(client):
    client.post("/auth/register", json=CREDS)
    assert client.post("/auth/register", json=CREDS).status_code == 409


def test_login_issues_a_fresh_token_and_retires_the_old_one(client):
    first = client.post("/auth/register", json=CREDS).json()["token"]
    second = client.post("/auth/login", json=CREDS).json()["token"]

    assert first != second
    assert client.get("/datasets", headers={"X-Session-Id": second}).status_code == 200
    assert client.get("/datasets", headers={"X-Session-Id": first}).status_code == 401


def test_login_with_wrong_password_is_401(client):
    client.post("/auth/register", json=CREDS)
    r = client.post("/auth/login", json={**CREDS, "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_unknown_user_is_401(client):
    assert client.post("/auth/login", json=CREDS).status_code == 401


def test_password_is_not_stored_in_plaintext(client, db_session):
    from app.models import User

    client.post("/auth/register", json=CREDS)
    user = db_session.query(User).one()
    assert user.password_hash != CREDS["password"]
    assert user.password_hash.startswith("$2b$")


def test_logout_invalidates_the_token(client):
    token = client.post("/auth/register", json=CREDS).json()["token"]
    headers = {"X-Session-Id": token}

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/datasets", headers=headers).status_code == 401


@pytest.mark.parametrize("headers", [{}, {"X-Session-Id": "not-a-real-token"}])
def test_owned_routes_reject_missing_or_bogus_tokens(client, headers):
    assert client.get("/datasets", headers=headers).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "al", "password": "hunter2hunter2"},
        {"username": "alice", "password": "short"},
        {"username": "alice", "password": "é" * 40},
    ],
)
def test_bad_credentials_are_422(client, payload):
    assert client.post("/auth/register", json=payload).status_code == 422
