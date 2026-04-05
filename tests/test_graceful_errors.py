"""Tier 3 Gold: bad inputs → JSON errors, not 500 tracebacks (where applicable)."""

import pytest

from app.models import Url


def test_unknown_route_json_404(client):
    rv = client.get("/totally/missing/route")
    assert rv.status_code == 404
    assert rv.get_json() == {"error": "not_found"}
    assert rv.is_json


def test_post_users_invalid_json_body(client):
    rv = client.post(
        "/users",
        data="{not valid json",
        content_type="application/json",
    )
    assert rv.status_code == 400
    body = rv.get_json()
    assert "error" in body
    assert rv.is_json


def test_post_events_invalid_json(client):
    rv = client.post(
        "/events",
        data="[",
        content_type="application/json",
    )
    assert rv.status_code in (400, 500)
    assert rv.is_json


def test_post_urls_malformed_json_body_json_error(client):
    """Invalid JSON on POST /urls → silent parse yields {} → validation error as JSON."""
    rv = client.post(
        "/urls",
        data="{not-json",
        content_type="application/json",
    )
    assert rv.status_code == 400
    assert "error" in rv.get_json()


def test_post_urls_non_json_content_type(client):
    rv = client.post(
        "/urls",
        data="not-json",
        content_type="text/plain",
    )
    assert rv.status_code == 400
    assert "error" in rv.get_json()


@pytest.mark.parametrize("path", ["/users", "/urls", "/events"])
def test_patch_not_allowed(client, path):
    rv = client.patch(path)
    assert rv.status_code == 405
