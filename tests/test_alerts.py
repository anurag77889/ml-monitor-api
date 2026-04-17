import pytest
from fastapi.testclient import TestClient

from app.models.alert import Alert
from tests.conftest import TestingSessionLocal


def _seed_alert(model_id: int, alert_type: str, severity: str) -> None:
    """Directly insert an alert into the test DB — bypasses background tasks."""
    db = TestingSessionLocal()
    try:
        alert = Alert(
            alert_type=alert_type,
            message=f"Test {alert_type} alert",
            severity=severity,
            triggered_value=0.8,
            ml_model_id=model_id,
        )
        db.add(alert)
        db.commit()
    finally:
        db.close()


class TestListAlerts:
    def test_list_alerts_empty(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        response = client.get(
            f"/models/{model_id}/alerts/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0

    def test_list_alerts_with_data(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        _seed_alert(model_id, "drift_detected", "high")
        _seed_alert(model_id, "low_confidence", "medium")

        response = client.get(
            f"/models/{model_id}/alerts/",
            headers=auth_headers,
        )
        body = response.json()
        assert body["total"] == 2

    def test_filter_by_severity(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        _seed_alert(model_id, "drift_detected", "high")
        _seed_alert(model_id, "low_confidence", "medium")

        response = client.get(
            f"/models/{model_id}/alerts/?severity=high",
            headers=auth_headers,
        )
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["severity"] == "high"

    def test_filter_unresolved(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        _seed_alert(model_id, "drift_detected", "high")

        response = client.get(
            f"/models/{model_id}/alerts/?is_resolved=false",
            headers=auth_headers,
        )
        body = response.json()
        assert body["total"] == 1


class TestResolveAlert:
    def test_resolve_alert_success(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        _seed_alert(model_id, "drift_detected", "high")

        # Get the alert ID
        alerts = client.get(
            f"/models/{model_id}/alerts/",
            headers=auth_headers,
        )
        alert_id = alerts.json()["items"][0]["id"]

        response = client.patch(
            f"/models/{model_id}/alerts/{alert_id}/resolve",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_resolved"] is True
        assert body["resolved_at"] is not None

    def test_resolve_alert_idempotent(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        _seed_alert(model_id, "drift_detected", "high")

        alerts = client.get(f"/models/{model_id}/alerts/", headers=auth_headers)
        alert_id = alerts.json()["items"][0]["id"]

        # Resolve twice — both should succeed
        r1 = client.patch(
            f"/models/{model_id}/alerts/{alert_id}/resolve",
            headers=auth_headers,
        )
        r2 = client.patch(
            f"/models/{model_id}/alerts/{alert_id}/resolve",
            headers=auth_headers,
        )
        assert r1.status_code == 200
        assert r2.status_code == 200


class TestBulkResolve:
    def test_bulk_resolve_all(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        _seed_alert(model_id, "drift_detected", "high")
        _seed_alert(model_id, "low_confidence", "medium")
        _seed_alert(model_id, "high_latency", "critical")

        response = client.patch(
            f"/models/{model_id}/alerts/resolve-all",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["resolved_count"] == 3

        # Confirm all resolved
        alerts = client.get(
            f"/models/{model_id}/alerts/?is_resolved=false",
            headers=auth_headers,
        )
        assert alerts.json()["total"] == 0


class TestAlertStats:
    def test_alert_stats(
        self,
        client: TestClient,
        registered_model: dict,
        auth_headers: dict,
    ):
        model_id = registered_model["id"]
        _seed_alert(model_id, "drift_detected", "high")
        _seed_alert(model_id, "drift_detected", "critical")
        _seed_alert(model_id, "low_confidence", "medium")

        response = client.get(
            f"/models/{model_id}/alerts/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total_alerts"] == 3
        assert body["unresolved_alerts"] == 3
        assert body["by_severity"]["high"] == 1
        assert body["by_severity"]["critical"] == 1
        assert body["by_type"]["drift_detected"] == 2
        assert body["by_type"]["low_confidence"] == 1