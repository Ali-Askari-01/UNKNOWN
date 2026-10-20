#!/bin/sh
set -eu

if [ "${BACKEND_RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Running database migrations because BACKEND_RUN_MIGRATIONS=true"
  alembic upgrade head
fi
workers="$(python -c 'from app.core.config import get_settings; print(get_settings().workers)')"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "$workers" --timeout-graceful-shutdown 30
