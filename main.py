"""FastAPI application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.v1 import (
    admin_contest,
    admin_misc,
    admin_results,
    admin_rounds,
    admin_users,
    auth,
    contest_ops,
    contest_participants,
    contest_teams,
    contests,
    me,
    predictions,
    rounds,
)
from api.error_handlers import register_error_handlers
from config.settings import get_settings
from core.logging_config import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title="Football Predictions API", version="1.1.0")
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(me.router, prefix=API_PREFIX)
app.include_router(contests.router, prefix=API_PREFIX)
app.include_router(contest_teams.router, prefix=API_PREFIX)
app.include_router(contest_participants.router, prefix=API_PREFIX)
app.include_router(contest_ops.router, prefix=API_PREFIX)
app.include_router(rounds.router, prefix=API_PREFIX)
app.include_router(predictions.router, prefix=API_PREFIX)
app.include_router(admin_misc.router, prefix=API_PREFIX)
app.include_router(admin_rounds.router, prefix=API_PREFIX)
app.include_router(admin_results.router, prefix=API_PREFIX)
app.include_router(admin_contest.router, prefix=API_PREFIX)
app.include_router(admin_users.router, prefix=API_PREFIX)

settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.static_assets_dir.mkdir(parents=True, exist_ok=True)
(settings.upload_dir / "teams").mkdir(parents=True, exist_ok=True)

app.mount(
    f"{settings.static_url_prefix}/assets",
    StaticFiles(directory=settings.static_assets_dir),
    name="static_assets",
)


@app.get(f"{settings.static_url_prefix}/teams/{{file_path:path}}", include_in_schema=False)
async def serve_team_logo(file_path: str) -> FileResponse:
    """Serve uploaded team logos from the configured upload directory."""
    teams_root = (get_settings().upload_dir / "teams").resolve()
    target = (teams_root / file_path).resolve()
    if not str(target).startswith(str(teams_root)):
        raise HTTPException(status_code=404, detail="Not found")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(target)


@app.get("/health")
async def health() -> dict[str, str]:
    """Проверка доступности сервиса."""
    return {"status": "ok"}
