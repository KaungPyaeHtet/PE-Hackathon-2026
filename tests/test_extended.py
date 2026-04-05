"""Extended tests targeting uncovered branches for Gold-tier (≥70%) coverage.

Covers:
- POST /events and its validation paths
- GET /events filters (user_id, event_type)
- DELETE /users/<id>
- POST /users/bulk
- PUT /users validation errors (non-string fields)
- GET /metrics and GET /logs endpoints
- Graceful JSON error responses for bad inputs
"""

import io

import pytest

from tests.conftest import TEST_EVENT_ID, TEST_SHORT_CODE, TEST_URL_ID, TEST_USER_ID


# ── Metrics endpoint ───────────────────────────────────────────────────────────


def test_metrics_returns_cpu_and_memory(client):
    rv = client.get("/metrics")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "cpu" in data
    assert "memory" in data
    assert "process" in data
    assert "percent" in data["cpu"]
    assert "used_mb" in data["memory"]
    assert "rss_mb" in data["process"]


# ── Logs endpoint ──────────────────────────────────────────────────────────────


def test_logs_returns_structure(client):
    rv = client.get("/logs")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "logs" in data
    assert "lines_returned" in data
    assert "log_file" in data


def test_logs_lines_param(client):
    rv = client.get("/logs?lines=5")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["lines_returned"] <= 5


def test_logs_bad_lines_param(client):
    """Non-integer ?lines= must not crash — falls back to default."""
    rv = client.get("/logs?lines=abc")
    assert rv.status_code == 200


# ── Events — POST ──────────────────────────────────────────────────────────────


def test_create_event_success(client):
    rv = client.post("/events", json={
        "event_type": "click",
        "url_id": TEST_URL_ID,
        "user_id": TEST_USER_ID,
    })
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["event_type"] == "click"
    assert data["url_id"] == TEST_URL_ID
    # Cleanup
    from app.models import Event
    Event.delete().where(Event.id == data["id"]).execute()


def test_create_event_with_details(client):
    rv = client.post("/events", json={
        "event_type": "view",
        "url_id": TEST_URL_ID,
        "user_id": TEST_USER_ID,
        "details": {"browser": "firefox"},
    })
    assert rv.status_code == 201
    data = rv.get_json()
    assert data["event_type"] == "view"
    from app.models import Event
    Event.delete().where(Event.id == data["id"]).execute()


def test_create_event_missing_event_type(client):
    rv = client.post("/events", json={"url_id": TEST_URL_ID, "user_id": TEST_USER_ID})
    assert rv.status_code == 400
    assert "event_type" in rv.get_json()["error"]


def test_create_event_bad_url_id(client):
    rv = client.post("/events", json={
        "event_type": "click",
        "url_id": "not-an-int",
        "user_id": TEST_USER_ID,
    })
    assert rv.status_code == 400


def test_create_event_bad_user_id(client):
    rv = client.post("/events", json={
        "event_type": "click",
        "url_id": TEST_URL_ID,
        "user_id": "not-an-int",
    })
    assert rv.status_code == 400


def test_create_event_url_not_found(client):
    rv = client.post("/events", json={
        "event_type": "click",
        "url_id": 99999999,
        "user_id": TEST_USER_ID,
    })
    assert rv.status_code == 404
    assert rv.get_json()["error"] == "url not found"


def test_create_event_user_not_found(client):
    rv = client.post("/events", json={
        "event_type": "click",
        "url_id": TEST_URL_ID,
        "user_id": 99999999,
    })
    assert rv.status_code == 404
    assert rv.get_json()["error"] == "user not found"


# ── Events — GET filters ────────────────────────────────────────────────────────


def test_list_events_filter_by_user(client):
    rv = client.get(f"/events?user_id={TEST_USER_ID}")
    assert rv.status_code == 200
    rows = rv.get_json()
    assert isinstance(rows, list)
    assert any(r["id"] == TEST_EVENT_ID for r in rows)


def test_list_events_filter_by_event_type(client):
    rv = client.get("/events?event_type=click")
    assert rv.status_code == 200
    rows = rv.get_json()
    assert isinstance(rows, list)
    assert all(r["event_type"] == "click" for r in rows)


def test_list_events_filter_by_unknown_event_type(client):
    rv = client.get("/events?event_type=doesnotexist")
    assert rv.status_code == 200
    assert rv.get_json() == []


# ── Users — DELETE ─────────────────────────────────────────────────────────────


def test_delete_user(client):
    """Create a user, delete it, confirm it's gone."""
    create_rv = client.post("/users", json={"username": "todelete", "email": "del@example.com"})
    assert create_rv.status_code == 201
    user_id = create_rv.get_json()["id"]

    del_rv = client.delete(f"/users/{user_id}")
    assert del_rv.status_code == 204

    get_rv = client.get(f"/users/{user_id}")
    assert get_rv.status_code == 404


def test_delete_user_not_found(client):
    rv = client.delete("/users/99999999")
    assert rv.status_code == 404


# ── Users — PUT validation ─────────────────────────────────────────────────────


def test_update_user_non_string_username(client):
    rv = client.put(f"/users/{TEST_USER_ID}", json={"username": 12345})
    assert rv.status_code == 422
    assert "username" in rv.get_json()["errors"]


def test_update_user_non_string_email(client):
    rv = client.put(f"/users/{TEST_USER_ID}", json={"email": ["not", "a", "string"]})
    assert rv.status_code == 422
    assert "email" in rv.get_json()["errors"]


# ── Users — POST /users/bulk ───────────────────────────────────────────────────


def test_bulk_import_users_success(client):
    csv_content = "id,username,email,created_at\n99901,bulkuser1,bulk1@test.com,2024-01-01 00:00:00\n99902,bulkuser2,bulk2@test.com,2024-01-01 00:00:00\n"
    data = {"file": (io.BytesIO(csv_content.encode()), "users.csv")}
    rv = client.post("/users/bulk", data=data, content_type="multipart/form-data")
    assert rv.status_code == 201
    result = rv.get_json()
    assert result["imported"] == 2
    # Cleanup
    from app.models import User
    User.delete().where(User.id << [99901, 99902]).execute()


def test_bulk_import_users_empty_csv(client):
    csv_content = "id,username,email,created_at\n"
    data = {"file": (io.BytesIO(csv_content.encode()), "users.csv")}
    rv = client.post("/users/bulk", data=data, content_type="multipart/form-data")
    assert rv.status_code == 200
    assert rv.get_json()["imported"] == 0


def test_bulk_import_users_missing_file(client):
    rv = client.post("/users/bulk", data={}, content_type="multipart/form-data")
    assert rv.status_code == 400
    assert "error" in rv.get_json()


# ── Graceful error responses ───────────────────────────────────────────────────


def test_create_user_empty_strings(client):
    rv = client.post("/users", json={"username": "  ", "email": "  "})
    assert rv.status_code == 400
    data = rv.get_json()
    assert data["error"] == "validation_error"


def test_create_user_non_string_fields(client):
    rv = client.post("/users", json={"username": 123, "email": 456})
    assert rv.status_code == 422


def test_all_error_responses_are_json(client):
    """Every error path must return JSON, never an HTML stack trace."""
    endpoints = [
        ("GET", "/users/99999999"),
        ("GET", "/urls/99999999"),
        ("GET", "/does-not-exist"),
        ("DELETE", "/users/99999999"),
        ("DELETE", "/urls/99999999"),
    ]
    for method, path in endpoints:
        rv = client.open(path, method=method)
        assert rv.content_type.startswith("application/json"), (
            f"{method} {path} returned non-JSON content-type: {rv.content_type}"
        )
        data = rv.get_json()
        assert data is not None, f"{method} {path} returned non-parseable JSON"
