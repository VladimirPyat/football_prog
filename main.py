"""FastAPI application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import admin_contest, admin_misc, admin_results, admin_rounds, auth, predictions, rounds
from config.settings import get_settings

settings = get_settings()

app = FastAPI(title="Football Predictions API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(rounds.router, prefix=API_PREFIX)
app.include_router(predictions.router, prefix=API_PREFIX)
app.include_router(admin_misc.router, prefix=API_PREFIX)
app.include_router(admin_rounds.router, prefix=API_PREFIX)
app.include_router(admin_results.router, prefix=API_PREFIX)
app.include_router(admin_contest.router, prefix=API_PREFIX)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
