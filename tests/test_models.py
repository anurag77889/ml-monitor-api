import pytest
from fastapi.testclient import TestClient


class TestCreateModel:
    def test_create_model_success(
        self, client: TestClient, auth_headers: dict
    ):
        response = client.post("/models/", json={
            "name": "Fraud Detector",
            "version": "2.0.0",
            "description": "Detects fraudulent transactions",
            "model_type": "classification",
            "drift_threshold": 0.1,
        }, headers=auth_headers)
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Fraud Detector"
        assert body["version"] == "2.0.0"
        assert body["status"] == "staging"      # default
        assert body["drift_threshold"] == 0.1

    def test_create_model_unauthenticated(self, client: TestClient):
        response = client.post("/models/", json={
            "name": "No Auth Model",
            "version": "1.0.0",
            "model_type": "regression",
        })
        assert response.status_code == 403

    def test_create_model_missing_required_fields(
        self, client: TestClient, auth_headers: dict
    ):
        response = client.post("/models/", json={
            "name": "Incomplete Model",
            # missing version and model_type
        }, headers=auth_headers)
        assert response.status_code == 422


class TestListModels:
    def test_list_models_empty(self, client: TestClient, auth_headers: dict):
        response = client.get("/models/", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_models_returns_own_models_only(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        # Register a second user and their model
        client.post("/auth/register", json={
            "email": "other@example.com",
            "username": "otheruser",
            "password": "password123",
        })
        login = client.post("/auth/login", json={
            "email": "other@example.com",
            "password": "password123",
        })
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        client.post("/models/", json={
            "name": "Other User Model",
            "version": "1.0.0",
            "model_type": "regression",
        }, headers=other_headers)

        # First user should only see their own model
        response = client.get("/models/", headers=auth_headers)
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Test Churn Model"

    def test_list_models_filter_by_status(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        # Promote to production
        model_id = registered_model["id"]
        client.patch(
            f"/models/{model_id}",
            json={"status": "production"},
            headers=auth_headers,
        )
        response = client.get(
            "/models/?status=production",
            headers=auth_headers,
        )
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "production"

    def test_list_models_pagination(
        self, client: TestClient, auth_headers: dict
    ):
        # Create 3 models
        for i in range(3):
            client.post("/models/", json={
                "name": f"Model {i}",
                "version": "1.0.0",
                "model_type": "classification",
            }, headers=auth_headers)

        response = client.get("/models/?skip=0&limit=2", headers=auth_headers)
        body = response.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2


class TestUpdateModel:
    def test_update_model_success(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        response = client.patch(
            f"/models/{model_id}",
            json={"status": "production", "drift_threshold": 0.1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "production"
        assert body["drift_threshold"] == 0.1
        assert body["name"] == registered_model["name"]  # unchanged

    def test_update_model_invalid_status(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        response = client.patch(
            f"/models/{model_id}",
            json={"status": "invalid_status"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_update_model_forbidden(
        self,
        client: TestClient,
        registered_model: dict,
    ):
        # Second user tries to update first user's model
        client.post("/auth/register", json={
            "email": "attacker@example.com",
            "username": "attacker",
            "password": "password123",
        })
        login = client.post("/auth/login", json={
            "email": "attacker@example.com",
            "password": "password123",
        })
        attacker_headers = {
            "Authorization": f"Bearer {login.json()['access_token']}"
        }
        model_id = registered_model["id"]
        response = client.patch(
            f"/models/{model_id}",
            json={"status": "production"},
            headers=attacker_headers,
        )
        assert response.status_code == 403


class TestDeleteModel:
    def test_delete_model_success(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        response = client.delete(f"/models/{model_id}", headers=auth_headers)
        assert response.status_code == 204

        # Confirm it's gone
        get_response = client.get(f"/models/{model_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_model_forbidden(
        self,
        client: TestClient,
        registered_model: dict,
    ):
        client.post("/auth/register", json={
            "email": "attacker@example.com",
            "username": "attacker",
            "password": "password123",
        })
        login = client.post("/auth/login", json={
            "email": "attacker@example.com",
            "password": "password123",
        })
        attacker_headers = {
            "Authorization": f"Bearer {login.json()['access_token']}"
        }
        model_id = registered_model["id"]
        response = client.delete(
            f"/models/{model_id}",
            headers=attacker_headers,
        )
        assert response.status_code == 403