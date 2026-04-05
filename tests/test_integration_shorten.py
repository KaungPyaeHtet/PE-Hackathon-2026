"""Tier 2 Silver: integration-style check — API create + ORM read (short link = POST /urls)."""

import json

from app.models import Event, Url
from tests.conftest import TEST_USER_ID


def test_post_urls_persists_row_and_emits_created_event(client):
    """POST /urls (shorten) → row in `urls` and analytics `created` event in DB."""
    rv = client.post(
        "/urls",
        json={
            "user_id": TEST_USER_ID,
            "original_url": "https://integration.example/shorten-path",
            "title": "Integration shorten",
        },
    )
    assert rv.status_code == 201
    data = rv.get_json()
    url_id = data["id"]
    short_code = data["short_code"]

    row = Url.get_by_id(url_id)
    assert row.short_code == short_code
    assert row.original_url == "https://integration.example/shorten-path"
    assert row.user_id == TEST_USER_ID

    ev = (
        Event.select()
        .where((Event.url_id == url_id) & (Event.event_type == "created"))
        .get()
    )

    d = json.loads(ev.details)
    assert d["short_code"] == short_code

    row.delete_instance()
