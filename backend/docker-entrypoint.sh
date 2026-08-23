#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
# Use uv run to ensure venv python is used; fallback to python if uv not in PATH
if command -v uv >/dev/null 2>&1; then
  uv run alembic upgrade head || {
    echo "[entrypoint] WARNING: alembic upgrade failed — continuing to start server"
  }
else
  python -m alembic upgrade head || {
    echo "[entrypoint] WARNING: alembic upgrade failed — continuing to start server"
  }
fi

echo "[entrypoint] Starting FastAPI server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
