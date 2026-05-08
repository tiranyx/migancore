"""Prometheus metrics endpoint for MiganCore observability.

Provides /metrics endpoint compatible with Prometheus scrape protocol.
Custom counters track business-level events (license validation,
training cycles, agent operations).

Usage:
    from routers.metrics import metrics_router, REQUEST_COUNT, LICENSE_VALIDATIONS
    app.include_router(metrics_router)
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
"""

from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

router = APIRouter(tags=["metrics"])

# ─── HTTP Request Metrics ───────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ─── Business Metrics ───────────────────────────────────────────────────────
LICENSE_VALIDATIONS = Counter(
    "license_validations_total",
    "Total license validation attempts",
    ["mode", "tier"],
)

ACTIVE_AGENTS = Gauge(
    "migancore_active_agents",
    "Number of active agents",
    ["tenant_id"],
)

TRAINING_CYCLE_STATUS = Gauge(
    "training_cycle_status",
    "Current training cycle status (0=idle, 1=running, 2=success, 3=failed)",
    ["method"],
)

DB_CONNECTIONS = Gauge(
    "db_connections_active",
    "Active database connections",
)

# ─── Endpoint ───────────────────────────────────────────────────────────────

@router.get("/metrics")
def metrics() -> Response:
    """Prometheus scrape endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
