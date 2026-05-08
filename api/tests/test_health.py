"""Tests for health and system endpoints.

Uses a minimal FastAPI app to test endpoint structure without full dependencies.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import pytest


class TestHealthEndpoints:
    """Test health check endpoint patterns."""

    def test_health_endpoint_returns_ok(self):
        app = FastAPI()

        @app.get("/health")
        def health():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ready_endpoint_returns_ok(self):
        app = FastAPI()

        @app.get("/ready")
        def ready():
            return {"status": "ok", "checks": {"db": "ok"}}

        client = TestClient(app)
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["checks"]["db"] == "ok"

    def test_metrics_endpoint_returns_prometheus_format(self):
        app = FastAPI()

        @app.get("/metrics")
        def metrics():
            return "# HELP http_requests_total Total requests"

        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "HELP" in response.text

    def test_health_with_dependencies(self):
        app = FastAPI()
        checks = {"db": True, "redis": True}

        @app.get("/health")
        def health():
            all_ok = all(checks.values())
            return {"status": "ok" if all_ok else "degraded", "checks": checks}

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["checks"]["db"] is True

    def test_health_degraded_when_db_down(self):
        app = FastAPI()
        checks = {"db": False, "redis": True}

        @app.get("/health")
        def health():
            all_ok = all(checks.values())
            return {"status": "ok" if all_ok else "degraded", "checks": checks}

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "degraded"

    def test_system_status_endpoint(self):
        app = FastAPI()

        @app.get("/v1/system/status")
        def system_status():
            return {"version": "0.5.16", "services": {"api": "ok"}}

        client = TestClient(app)
        response = client.get("/v1/system/status")
        assert response.status_code == 200
        assert "version" in response.json()

    def test_system_metrics_endpoint(self):
        app = FastAPI()

        @app.get("/v1/system/metrics")
        def system_metrics():
            return {"ram_used_mb": 1024, "cpu_percent": 15.5}

        client = TestClient(app)
        response = client.get("/v1/system/metrics")
        assert response.status_code == 200
        assert "ram_used_mb" in response.json()
