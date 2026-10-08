#!/bin/sh
set -eu

echo "Running database migrations (alembic upgrade head)..."
if ! alembic upgrade head; then
  echo "ERROR: alembic upgrade head failed. See traceback above." >&2
  echo "Hint: check DATABASE_URL / POSTGRES_PASSWORD match the initialized postgres volume." >&2
  exit 1
fi

echo "Starting API (uvicorn)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
