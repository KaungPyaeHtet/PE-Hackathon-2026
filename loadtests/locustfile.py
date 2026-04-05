"""
Load test scenarios for the URL shortener service.

Usage:
  # Bronze — 50 concurrent users, 60 s
  uv run locust -f loadtests/locustfile.py --host http://127.0.0.1:5000 \
    --users 50 --spawn-rate 50 --run-time 60s --headless

  # Silver — 200 concurrent users, 90 s
  uv run locust -f loadtests/locustfile.py --host http://127.0.0.1:5000 \
    --users 200 --spawn-rate 50 --run-time 90s --headless

  # Gold — 500 concurrent users, 120 s
  uv run locust -f loadtests/locustfile.py --host http://127.0.0.1:5000 \
    --users 500 --spawn-rate 50 --run-time 120s --headless
"""

from locust import HttpUser, between, task


class AppUser(HttpUser):
    """Simulates a realistic mix of read-heavy API traffic."""

    wait_time = between(0.1, 0.5)

    # Populated at test start so all VUs share the same IDs
    _url_id: int | None = None
    _short_code: str | None = None

    def on_start(self):
        """Seed: grab an existing URL to use in read tasks."""
        with self.client.get("/urls?limit=1", name="GET /urls (seed)", catch_response=True) as r:
            if r.status_code == 200:
                rows = r.json()
                if rows:
                    AppUser._url_id = rows[0]["id"]
                    AppUser._short_code = rows[0]["short_code"]
                r.success()

    # ── Read tasks (high weight — reflects real traffic) ──────────────────────

    @task(4)
    def health(self):
        self.client.get("/health", name="GET /health")

    @task(5)
    def list_urls(self):
        self.client.get("/urls?limit=20", name="GET /urls")

    @task(5)
    def list_users(self):
        self.client.get("/users?limit=20", name="GET /users")

    @task(3)
    def list_events(self):
        self.client.get("/events?limit=20", name="GET /events")

    @task(6)
    def get_url_by_id(self):
        if self._url_id:
            self.client.get(f"/urls/{self._url_id}", name="GET /urls/<id>")

    @task(6)
    def redirect(self):
        if self._short_code:
            self.client.get(
                f"/s/{self._short_code}",
                name="GET /s/<code>",
                allow_redirects=False,
            )

    @task(1)
    def index(self):
        self.client.get("/", name="GET /")
