# 2-Minute Demo — PE Hackathon
## Theme: How I made it reliable, scalable, and observable

> One sentence each on what you did, then immediately show it working.
> Judges care about **proof**, not explanation. Show first, talk second.

---

## Pre-Demo Checklist (do this before you present)

```bash
# Stack must be running
docker compose up -d

# Seed data loaded
docker compose exec app1 uv run python scripts/load_pe_seed.py

# Verify health
curl http://127.0.0.1/health   # → {"status":"ok"}

# Open these tabs in browser — switch during demo
# http://127.0.0.1:3000   → Grafana dashboards
# http://127.0.0.1:9090   → Prometheus alerts
```

---

## [0:00 – 0:05] Required Intro (say this exact line on camera)

> *"Hey, I'm Kaung and this is my demo for the Production Engineering Hackathon."*

---

## [0:05 – 0:30] Quest 1: Reliability 🛡️

**Say:** *"Reliability means: tests block bad code, and the service survives crashes."*

**Show 1 — Tests are the safety net:**
```bash
uv run pytest tests/ --cov=app -q
```
Point at: **118 tests, 94% coverage, 0 failures.**

**Say:** *"And in CI, if any test fails, the deploy is physically blocked."*

> Point at `.github/workflows/ci.yml` line `needs: test` on GitHub — or just say it.

**Show 2 — Kill a worker, service doesn't go down:**
```bash
docker kill hackathon_app1

curl http://localhost/health
```
Point at: **Still 200 OK.** Nginx routed to app2 instantly.

```bash
docker compose up -d app1    # resurrection
docker compose ps            # both back up
```

**Say:** *"restart: unless-stopped means it heals itself. User sees nothing."*

---

## [0:30 – 1:00] Quest 2: Scalability 🚀

**Say:** *"Scalability means: prove it holds up under real load."*

**Show — Ramp to 200 concurrent users:**
```bash
uv run locust -f loadtests/locustfile.py \
  --host http://127.0.0.1 \
  --users 200 --spawn-rate 50 --run-time 60s --headless
```

Point at the numbers as they scroll:
- **RPS** — requests per second climbing
- **Failures: 0** — zero errors under load
- **P95 latency** — stays under 500ms

**Say:** *"Two workers behind Nginx. Redis caches hot reads. Scales horizontally — add more app containers and Nginx picks them up automatically."*

> If load test takes too long: show the baseline results from `loadtests/BASELINE_AUTO.md` instead and say "here's what we recorded earlier."

---

## [1:00 – 1:40] Quest 3: Incident Response 🚨

**Say:** *"Incident response means: when something breaks, we know immediately and we know what to do."*

**Show 1 — Kill app1, trigger the alert:**
```bash
docker kill hackathon_app1
```

Switch to browser → **http://127.0.0.1:9090/alerts**

Point at: **ServiceDown alert fires within 1 minute** (Prometheus rule: `up == 0 for 1m`)

**Say:** *"Prometheus scrapes /metrics every 15 seconds. The moment an instance disappears, the alert fires."*

**Show 2 — Discord notification (if DISCORD_WEBHOOK_URL is set):**
> Pull up Discord on your phone or screen — show the 🔴 alert message.
> If not set up: show the alertmanager config at `monitoring/alertmanager/alertmanager.yml`

**Show 3 — Grafana dashboard:**
Switch to **http://127.0.0.1:3000**
> Point at: **Demo Snapshot** (availability, RPS, P95, 5xx rate), then traffic/latency panels dropping and recovering.

**Say:** *"We also have runbooks — step-by-step guides for every alert. On-call knows exactly what to do."*

**Bring app1 back:**
```bash
docker compose up -d app1
```
> Point at Grafana: traffic recovers, alert resolves ✅

---

## [1:40 – 2:00] Close

**Say:**
> *"So: 94% test coverage blocks bad deploys. Two workers behind a load balancer survive crashes.
> 200 concurrent users, zero errors. And when something does break,
> we get an alert in Discord within a minute with a runbook telling us exactly how to fix it.
> That's not just a working service — that's a production-grade one."*

---

## Backup Commands

| Situation | Command |
|---|---|
| Stack not running | `docker compose up -d` |
| app1 won't start | `docker compose logs app1` then `docker compose up -d --force-recreate app1` |
| Load test too slow for demo | Open `loadtests/BASELINE_AUTO.md` — show recorded numbers |
| Alert not firing yet | Show Prometheus rules at `monitoring/prometheus/alerts.yml` instead |
| Grafana blank | `docker compose restart grafana` — or just point at Prometheus |
| Discord not set up | Show `monitoring/alertmanager/alertmanager.yml` — explain the config |

---

## The One-Liner (if they ask "so what?")

> *"Tests, load balancer, auto-restart, Prometheus, Discord alerts, runbooks —
> it's not just built, it's operated."*
