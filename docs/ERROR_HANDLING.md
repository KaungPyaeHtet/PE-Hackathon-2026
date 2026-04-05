# Error handling (HTTP responses)

This service returns **JSON** for API-style errors so clients never have to parse HTML for machine-readable failures.

## 404 Not Found

| Source | Response body | When |
|--------|----------------|------|
| Flask `@app.errorhandler(404)` | `{"error": "not_found"}` | Unknown path (no matching route). |
| `abort(404)` in views | Same handler | e.g. `GET /users/<id>` when the user does not exist; missing short code on redirect. |

Log line: `not_found` with `path` in structured logs.

## 500 Internal Server Error

| Source | Response body | When |
|--------|----------------|------|
| `@app.errorhandler(500)` | `{"error": "internal_server_error"}` | Unhandled exception in a request handler. |

The full exception is **logged server-side** (`internal_server_error` with stack trace). The client does **not** receive a Python traceback.

## Other common status codes

| Code | Typical body | Meaning |
|------|----------------|---------|
| 400 | `{"error": "..."}` | Validation (bad JSON shape, missing fields, malformed `details`, etc.). |
| 403 | (framework default) | Rare; not used by core routes today. |
| 405 | (Flask default for wrong method) | e.g. `PATCH /users` when only GET/POST are defined. |
| 410 | `{"error": "gone", "reason": "inactive"}` | Redirect target exists but `is_active` is false. |
| 503 | `{"status": "error", "detail": "database unreachable"}` | `GET /health` when the DB ping fails. |

## Health vs application errors

- **`GET /health`** is the liveness/readiness style check: it returns **503** with a small JSON payload if PostgreSQL cannot be reached.
- Normal CRUD and redirect routes use the patterns above; they do not return raw Werkzeug HTML error pages for JSON APIs when handlers use `jsonify` or registered error handlers.

## Verifying locally

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5000/does-not-exist
# 404

curl -s http://127.0.0.1:5000/does-not-exist
# {"error":"not_found"}
```
