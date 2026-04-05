"""Shared fixtures for all tests.

Session-scoped DB setup: tables are created once, test data seeded with IDs
in the 9000-range to avoid clashing with real seed data. Everything is torn
down at the end of the session.
"""

from datetime import datetime, timezone

import pytest

from app import create_app
from app.database import db
from app.models import Event, Url, User

_NOW = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Fixed IDs used across tests so tests can reference them by name
TEST_USER_ID = 9001
TEST_URL_ID = 9001
TEST_SHORT_CODE = "tstcode"
TEST_EVENT_ID = 9001

# A second URL used for update/delete tests (so we don't destroy the primary fixture)
TEST_URL_ID_2 = 9002
TEST_SHORT_CODE_2 = "tstcd02"


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture(scope="session")
def _db(app):
    """Create tables and seed test rows once for the whole session."""
    with app.app_context():
        db.create_tables([User, Url, Event], safe=True)

        User.insert(
            id=TEST_USER_ID,
            username="testuser",
            email="test@example.com",
            created_at=_NOW,
        ).on_conflict_ignore().execute()

        Url.insert(
            id=TEST_URL_ID,
            user_id=TEST_USER_ID,
            short_code=TEST_SHORT_CODE,
            original_url="https://example.com/original",
            title="Test URL",
            is_active=True,
            created_at=_NOW,
            updated_at=_NOW,
        ).on_conflict_ignore().execute()

        Url.insert(
            id=TEST_URL_ID_2,
            user_id=TEST_USER_ID,
            short_code=TEST_SHORT_CODE_2,
            original_url="https://example.com/second",
            title="Second URL",
            is_active=True,
            created_at=_NOW,
            updated_at=_NOW,
        ).on_conflict_ignore().execute()

        Event.insert(
            id=TEST_EVENT_ID,
            url_id=TEST_URL_ID,
            user_id=TEST_USER_ID,
            event_type="click",
            timestamp=_NOW,
            details="{}",
        ).on_conflict_ignore().execute()

        yield

        # Teardown — cascade order matters
        Event.delete().where(Event.id == TEST_EVENT_ID).execute()
        Url.delete().where(Url.id << [TEST_URL_ID, TEST_URL_ID_2]).execute()
        User.delete().where(User.id == TEST_USER_ID).execute()


@pytest.fixture()
def client(app, _db):
    return app.test_client()
