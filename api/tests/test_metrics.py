"""Tests for Prometheus metrics endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import pytest

from routers.metrics import router as metrics_router, REQUEST_COUNT, LICENSE_VALIDATIONS


class TestMetricsEndpoint:
    """Test /metrics Prometheus scrape endpoint."""

    def test_metrics_returns_prometheus_format(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "# HELP" in response.text

    def test_metrics_includes_custom_counters(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)

        # Increment a counter before scraping
        REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200").inc()

        response = client.get("/metrics")
        assert "http_requests_total" in response.text
        assert 'method="GET"' in response.text

    def test_metrics_includes_license_counter(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)

        LICENSE_VALIDATIONS.labels(mode="FULL", tier="PERAK").inc()
        LICENSE_VALIDATIONS.labels(mode="FULL", tier="PERAK").inc()

        response = client.get("/metrics")
        assert "license_validations_total" in response.text
        assert 'mode="FULL"' in response.text
        assert 'tier="PERAK"' in response.text

    def test_metrics_empty_by_default(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)
        response = client.get("/metrics")
        # Should still return valid prometheus format even with no data
        assert response.status_code == 200
        assert response.text.startswith("#")

    def test_request_latency_histogram_exists(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)
        # Record an observation so buckets appear
        from routers.metrics import REQUEST_LATENCY
        REQUEST_LATENCY.labels(method="GET", endpoint="/test").observe(0.05)
        response = client.get("/metrics")
        assert "http_request_duration_seconds" in response.text
        assert "bucket" in response.text

    def test_active_agents_gauge_exists(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)
        response = client.get("/metrics")
        assert "migancore_active_agents" in response.text

    def test_training_cycle_gauge_exists(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)
        response = client.get("/metrics")
        assert "training_cycle_status" in response.text

    def test_db_connections_gauge_exists(self):
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)
        response = client.get("/metrics")
        assert "db_connections_active" in response.text

    def test_counter_increments_correctly(self):
        REQUEST_COUNT.labels(method="POST", endpoint="/chat", status_code="200").inc(5)
        app = FastAPI()
        app.include_router(metrics_router)
        client = TestClient(app)
        response = client.get("/metrics")
        # The counter value should appear in the output
        lines = [l for l in response.text.split("\n") if "http_requests_total{" in l and 'method="POST"' in l]
        assert len(lines) > 0
