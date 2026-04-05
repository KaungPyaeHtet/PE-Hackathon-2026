# Failure modes & resilience (Tier 3 — The Immortal)

This document describes **what breaks**, **what the user sees**, and **how the platform recovers**.

## 1. Application process killed (chaos / OOM / crash)

**What happens:** A worker handling HTTP traffic exits unexpectedly.

**User impact:** In-flight requests fail (connection reset or 502 from a reverse proxy).

**Recovery (Docker Compose):** All app-related services use `restart: unless-stopped` in `docker-compose.yml` (`app1`, `app2`, `db`, `redis`, `nginx`, observability stack). Docker restarts the container; new requests go to healthy workers behind nginx.

**Demo (local):**

```bash
docker compose up -d
docker kill hackathon_app1
# Within seconds: docker restarts app1 (check `docker compose ps`).
```

## 2. PostgreSQL unavailable

**What happens:** The database is down or the network to it is broken.

**User impact:**

- `GET /health` → **503** JSON: `{"status":"error","detail":"database unreachable"}`.
- Other routes may error when Peewee tries to query (typically **500** with `{"error":"internal_server_error"}` after connection failure), depending on where the failure surfaces.

**Recovery:** Restore Postgres; app processes reconnect on the next request (Peewee `connect` hooks in `app/database.py`).

## 3. Redis unavailable

**What happens:** Cache helper cannot connect or `PING` fails.

**User impact:** **None** for correctness — `app/cache.py` is **fail-open**: reads return `None`, writes and invalidations are no-ops. The app is intended to fall back to database behavior (cache is optional).

**Recovery:** When Redis returns, the next successful `_get()` reconnects and repopulates from traffic.

## 4. Bad client input (garbage data)

**What happens:** Invalid JSON, wrong types, missing required fields, illegal `details` on `POST /events`, etc.

**User impact:** **4xx** responses with **JSON** `error` (or field-specific messages) — not an HTML stack trace. See [`ERROR_HANDLING.md`](ERROR_HANDLING.md).

**Tests:** `tests/test_graceful_errors.py` and validation tests in `tests/test_api_integration.py`.

## 5. Nginx / load balancer up, all app workers down

**What happens:** Nginx cannot reach `app1:5000` / `app2:5000`.

**User impact:** **502 Bad Gateway** (HTML from nginx), not Flask JSON.

**Recovery:** Restart app containers; nginx continues to retry upstreams per its config.

## 6. CI / deploy gate (Tier 2 — The Gatekeeper)

**What happens:** A commit introduces failing tests or coverage below **70%**.

**User impact:** GitHub Actions workflow **CI** fails (`pytest --cov-fail-under=70`). The **`deploy`** job in the same workflow **does not run** (it `needs: test`). You should require this check green before merging to `main` (branch protection) so broken code never reaches production deploy steps.

**Screenshot tip:** Open the failed run on GitHub → the `deploy` job is skipped/failed parent shows the gate working.

## Coverage targets

| Tier | Minimum line coverage (pytest-cov) |
|------|--------------------------------------|
| Silver | 50% (historical baseline; project now enforces higher in CI) |
| Gold | **70%** (`pyproject.toml` + `.github/workflows/ci.yml`) |

Run locally:

```bash
uv run pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=70
```
