# Architecture Decision Log

Why we made the technical choices we did.

---

## ADR-001: Per-request DB connections over a connection pool

**Decision:** Open a new DB connection per request via Flask's `before_request` / `teardown_appcontext` hooks.

**Context:** Peewee's `DatabaseProxy` pattern and Flask's request lifecycle.

**Reasons:**
- Simple, correct, and the officially recommended Peewee + Flask pattern.
- Avoids connection leak bugs that are common with manual pool management.
- At hackathon scale (50 concurrent VUs in load tests), per-request connections do not exhaust PostgreSQL's default `max_connections = 100`.

**Trade-offs accepted:**
- Each request pays a TCP connection setup cost (~1ms). At higher scale (>200 concurrent users), a connection pool (e.g., PgBouncer) would be needed.

---

## ADR-002: Flask over FastAPI / Django

**Decision:** Use Flask 3.1 as the web framework.

**Context:** The service is a straightforward CRUD + redirect API with no complex async requirements at hackathon scale.

**Reasons:**
- Minimal boilerplate — an app factory and two blueprints get us to a running service in under 200 lines.
- Familiar to the team; no async learning curve.
- Flask + Peewee is a well-documented, officially-supported combination.
- Django's batteries (ORM, admin, auth) add complexity we don't need.
- FastAPI would require `async` throughout the stack, complicating the Peewee integration.

**Trade-offs accepted:**
- No built-in async. Under sustained high concurrency the GIL and synchronous Peewee queries will limit throughput. Gunicorn workers mitigate this at hackathon scale.

---

## ADR-003: Peewee ORM over SQLAlchemy

**Decision:** Use Peewee as the ORM.

**Context:** Need a simple ORM that integrates cleanly with Flask's request lifecycle.

**Reasons:**
- Peewee is far simpler than SQLAlchemy — models are plain Python classes, queries read like SQL.
- The `DatabaseProxy` pattern is purpose-built for per-request connections in Flask.
- No session management complexity (SQLAlchemy sessions require careful scoping with Flask).
- Sufficient for three simple models (User, Url, Event) with basic CRUD.

**Trade-offs accepted:**
- Peewee has a smaller ecosystem than SQLAlchemy. Features like async queries or complex join strategies would require SQLAlchemy.

---

## ADR-004: uv for dependency management over pip / Poetry

**Decision:** Use `uv` as the package manager and virtual environment tool.

**Context:** Need a fast, reproducible install workflow for both local dev and CI.

**Reasons:**
- `uv sync` is 10–100× faster than `pip install` — CI installs run in seconds, not minutes.
- Lock file (`uv.lock`) ensures byte-for-byte reproducible installs across machines and CI.
- Dev / non-dev dependency groups (`--group dev`) avoid shipping test deps to production.
- Single tool replaces `pip` + `virtualenv` + `pip-tools` with one command.

**Trade-offs accepted:**
- `uv` is newer and less battle-tested than pip/Poetry. In the unlikely event of a compatibility issue, fall back to `pip install -r requirements.txt`.

---

## ADR-005: PostgreSQL 16 over MySQL / SQLite

**Decision:** Use PostgreSQL 16 as the database.

**Context:** Need a production-grade relational database.

**Reasons:**
- PostgreSQL has superior index types and query planner for future optimisation (e.g., partial indexes, BRIN for time-series events).
- The hackathon seed data is relational; a document DB or key-value store would add unnecessary complexity.
- SQLite is single-writer and not suitable for multi-worker gunicorn or multi-container deployments.
- PostgreSQL is the default for Peewee's `PostgresqlDatabase` driver and well-supported in CI (`services: postgres`).

**Trade-offs accepted:**
- Requires a running Postgres server (not zero-dependency like SQLite). Mitigated by Docker Compose.

---

## ADR-006: Redis as a fail-open read cache

**Decision:** Add Redis as an optional read-through cache for API list endpoints, with a fail-open design.

**Context:** Under load, repeated `SELECT * FROM urls LIMIT 100` queries are the hot path.

**Reasons:**
- Redis reduces DB load for read-heavy endpoints (user/URL list pages).
- Fail-open (`app/cache.py` returns `None` on any error) means a Redis outage does not take down the API — the app falls back to direct DB queries transparently.
- 128 MB cap with `allkeys-lru` eviction is sufficient for our dataset without risk of memory exhaustion.

**Trade-offs accepted:**
- Cache adds a potential for stale reads (mitigated by short TTL and cache invalidation on write). Cache misses add a round-trip. Fail-open means we can't use Redis for correctness-critical state.

---

## ADR-007: Nginx as a layer-4/7 load balancer over HAProxy / AWS ALB

**Decision:** Run Nginx as the front-door load balancer distributing traffic across two gunicorn app instances.

**Context:** Need high availability and horizontal scale beyond a single process.

**Reasons:**
- Nginx is already in every ops team's toolkit; no new tooling to learn.
- Round-robin upstream to `app1` and `app2` doubles capacity with zero application changes.
- Nginx handles slow clients and connection queuing, protecting gunicorn workers.
- Simple `default.conf` is version-controlled alongside the app — no external infra dependency.

**Trade-offs accepted:**
- Single nginx container is a potential single point of failure. In production, replace with a cloud load balancer (AWS ALB, GCP HTTPS LB) for redundancy.

---

## ADR-008: Prometheus + Grafana + Alertmanager monitoring stack

**Decision:** Ship a pre-configured observability stack (Prometheus scraping the Flask app, Grafana for dashboards, Alertmanager for Discord alerts).

**Context:** Need metrics, alerting, and visualisation without a paid SaaS dependency.

**Reasons:**
- All three are open-source, containerised, and well-documented.
- Prometheus's pull model makes adding new metric targets trivial (just add a scrape config).
- Grafana provisioning-as-code means the dashboard is version-controlled and boots ready-to-use.
- Alertmanager + Discord webhook gives real-time alerts without a paid PagerDuty or OpsGenie account.

**Trade-offs accepted:**
- Adds 3 containers and ~200 MB of images to the stack. For a tiny hackathon service this is overprovisioned but demonstrates production-grade observability.

---

## ADR-009: Docker Compose for full-stack local dev and demo

**Decision:** Provide a `docker-compose.yml` that wires together all services (app × 2, db, redis, nginx, prometheus, grafana, alertmanager).

**Context:** Need a single command to spin up the complete production-like topology for demos and load testing.

**Reasons:**
- `docker compose up -d` reproduces the same topology on any machine with Docker.
- Health checks (`pg_isready`, `redis-cli ping`) ensure services start in the correct order.
- `restart: unless-stopped` on all containers provides crash recovery without a full orchestrator.
- Volume mounts for Postgres, Prometheus, and Grafana data survive container restarts.

**Trade-offs accepted:**
- Not a Kubernetes-grade deployment. For a real production service, move to managed infra (RDS, ElastiCache, a cloud LB). Docker Compose is the right tradeoff for a hackathon demo.