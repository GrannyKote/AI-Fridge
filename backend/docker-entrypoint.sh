#!/bin/sh
set -eu

python -c "
from app.config import settings
host = settings.postgres_host or '(from DATABASE_URL)'
print(f'DB target: {settings.postgres_user}@{host}:{settings.postgres_port}/{settings.postgres_db}', flush=True)
"

if ! python wait_for_db.py; then
  echo "ERROR: cannot connect to PostgreSQL. Check POSTGRES_PASSWORD and postgres volume." >&2
  exit 1
fi

if ! python dedupe_alembic_version.py; then
  echo "ERROR: could not normalize alembic_version table." >&2
  exit 1
fi

echo "Running database migrations (alembic upgrade head)..."
attempt=1
max_attempts=3
while [ "$attempt" -le "$max_attempts" ]; do
  if alembic upgrade head; then
    break
  fi
  if [ "$attempt" -eq "$max_attempts" ]; then
    echo "ERROR: alembic upgrade head failed after ${max_attempts} attempts." >&2
    exit 1
  fi
  echo "Alembic failed (attempt ${attempt}/${max_attempts}), retry in 5s..." >&2
  attempt=$((attempt + 1))
  sleep 5
done

echo "Starting API (uvicorn)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
