#!/bin/sh
set -e

mkdir -p /app/data /app/logs/archive /app/uploads/teams

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting API..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
