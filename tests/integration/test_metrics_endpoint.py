"""Integration test: verify /metrics endpoint returns Prometheus-style output."""

from __future__ import annotations


def test_metrics_endpoint_returns_text(client) -> None:  # noqa: ANN001
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_metrics_endpoint_after_request_shows_counters(client) -> None:  # noqa: ANN001
    # Make a health request first to generate metrics
    client.get("/api/v1/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "http_requests_total" in body
