import pytest
from fastapi.testclient import TestClient


class TestRegister:
    def test_register_success(self, client: TestClient):
        response = client.post("/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "securepassword",
        })
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "new@example.com"
        assert body["username"] == "newuser"
        assert "password" not in body
        assert "hashed_password" not in body

    def test_register_duplicate_email(self, client: TestClient, registered_user: dict):
        response = client.post("/auth/register", json={
            "email": "test@example.com",   # same email as registered_user
            "username": "different",
            "password": "password123",
        })
        assert response.status_code == 409

    def test_register_duplicate_username(self, client: TestClient, registered_user: dict):
        response = client.post("/auth/register", json={
            "email": "different@example.com",
            "username": "testuser",         # same username as registered_user
            "password": "password123",
        })
        assert response.status_code == 409

    def test_register_invalid_email(self, client: TestClient):
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "username": "someuser",
            "password": "password123",
        })
        assert response.status_code == 422

    def test_register_short_password(self, client: TestClient):
        response = client.post("/auth/register", json={
            "email": "user@example.com",
            "username": "someuser",
            "password": "short",            # less than 8 chars
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient, registered_user: dict):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, registered_user: dict):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        response = client.post("/auth/login", json={
            "email": "ghost@example.com",
            "password": "password123",
        })
        assert response.status_code == 401

    def test_login_returns_no_password(self, client: TestClient, registered_user: dict):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        body = response.json()
        assert "password" not in body
        assert "hashed_password" not in body


class TestGetMe:
    def test_get_me_success(self, client: TestClient, auth_headers: dict):
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "test@example.com"
        assert body["username"] == "testuser"

    def test_get_me_no_token(self, client: TestClient):
        response = client.get("/auth/me")
        assert response.status_code == 403

    def test_get_me_invalid_token(self, client: TestClient):
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalidtoken"}
        )
        assert response.status_code == 401