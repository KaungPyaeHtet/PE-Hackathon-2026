FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first (layer cache — only reinstalls when deps change)
COPY pyproject.toml ./
COPY uv.lock* ./

# Install production deps only
RUN uv sync --no-dev

# Copy application source
COPY app/    ./app/
COPY scripts/ ./scripts/
COPY run.py  ./

EXPOSE 5000

# 4 sync workers; tune via GUNICORN_WORKERS env var if needed
CMD [".venv/bin/gunicorn", "app:create_app()", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "30"]
