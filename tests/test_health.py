"""Smoke tests that run in CI (Postgres available via env)."""

import pytest

from app import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health_ok(client):
    rv = client.get("/health")
    assert rv.status_code == 200
    assert rv.get_json() == {"status": "ok"}


def test_dashboard_page_renders(client):
    rv = client.get("/dashboard")
    assert rv.status_code == 200
    assert b"dashboard.js" in rv.data
    assert b"live api" in rv.data.lower()
