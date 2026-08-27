#!/bin/sh
set -e

echo "Starting AI Doctor API"

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
  i=0
  until alembic upgrade head; do
    i=$((i + 1))
    if [ "$i" -ge 20 ]; then
      echo "PostgreSQL is not reachable after retries."
      echo "DATABASE_URL must be your hosted Postgres URL, not localhost:5432."
      echo "On Render/Railway: create a PostgreSQL addon and link it to this service."
      exit 1
    fi
    echo "Waiting for PostgreSQL ($i/20)..."
    sleep 3
  done
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
