FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY config ./config
COPY alembic ./alembic
COPY alembic.ini ./
COPY main.py ./
COPY src ./src
COPY static ./static
COPY config/contest_defaults.json ./config/contest_defaults.json
COPY docker/entrypoint-api.sh /entrypoint-api.sh

RUN uv sync --no-dev --frozen && chmod +x /entrypoint-api.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint-api.sh"]
