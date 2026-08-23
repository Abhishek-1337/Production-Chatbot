# syntax=docker/dockerfile:1
FROM python:3.14-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    HF_HUB_OFFLINE=0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN mkdir -p /app/chroma_db && chmod -R 777 /app/chroma_db

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
USER root
RUN chmod +x /app/docker-entrypoint.sh && chown appuser:appuser /app/docker-entrypoint.sh
USER appuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]
