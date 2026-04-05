"""Prometheus scrape endpoint and related wiring."""

import pytest


def test_prom_returns_prometheus_text(client):
    rv = client.get("/prom")
    assert rv.status_code == 200
    assert b"http_requests_total" in rv.data
    assert rv.content_type.startswith("application/openmetrics") or "text/plain" in rv.content_type
