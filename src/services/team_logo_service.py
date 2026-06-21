"""Team logo validation, resize, persistence, and URL resolution."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from core.exceptions import NotFoundError, ValidationError
from database.models import Team
from services.contest_lifecycle_service import require_unlocked

logger = logging.getLogger(__name__)

ALLOWED_MIME = {"image/png", "image/jpeg", "image/gif"}


def resolve_team_logo_url(logo_url: str | None, settings: Settings) -> str:
    """Return stored logo URL or configured default when unset in DB."""
    return logo_url if logo_url else settings.default_team_logo_url


def _center_crop_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return img.crop((left, top, left + side, top + side))


def _logo_disk_path(settings: Settings, contest_id: int, team_id: int) -> Path:
    return settings.upload_dir / "teams" / str(contest_id) / f"{team_id}.jpg"


def _public_logo_url(settings: Settings, contest_id: int, team_id: int) -> str:
    prefix = settings.static_url_prefix.rstrip("/")
    return f"{prefix}/teams/{contest_id}/{team_id}.jpg"


def delete_uploaded_logo_if_custom(logo_url: str | None, settings: Settings) -> None:
    """Remove uploaded logo file when clearing custom logo_url."""
    if not logo_url:
        return
    teams_prefix = f"{settings.static_url_prefix.rstrip('/')}/teams/"
    if not logo_url.startswith(teams_prefix):
        return
    relative = logo_url[len(teams_prefix) :]
    file_path = settings.upload_dir / "teams" / relative
    if file_path.is_file():
        file_path.unlink()
        logger.info("deleted team logo file path=%s", file_path)


async def save_team_logo(
    session: AsyncSession,
    *,
    contest_id: int,
    team_id: int,
    file_bytes: bytes,
    content_type: str,
    settings: Settings,
) -> str:
    """Validate, resize to team_logo_target_px², write file, update team.logo_url."""
    await require_unlocked(session, contest_id)
    team = await session.get(Team, team_id)
    if team is None or team.contest_id != contest_id:
        raise NotFoundError(f"Команда {team_id} не найдена в конкурсе {contest_id}")

    if len(file_bytes) > settings.max_logo_bytes:
        raise ValidationError(
            f"Файл слишком большой (максимум {settings.max_logo_bytes} байт)"
        )

    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime not in ALLOWED_MIME:
        raise ValidationError("Допустимые форматы: PNG, JPEG, GIF")

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.load()
    except OSError as exc:
        raise ValidationError("Не удалось прочитать изображение") from exc

    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    square = _center_crop_square(img)
    target = settings.team_logo_target_px
    resized = square.resize((target, target), Image.Resampling.LANCZOS)

    dest = _logo_disk_path(settings, contest_id, team_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    resized.save(dest, format="JPEG", quality=85, optimize=True)

    public_url = _public_logo_url(settings, contest_id, team_id)
    if team.logo_url and team.logo_url != public_url:
        delete_uploaded_logo_if_custom(team.logo_url, settings)
    team.logo_url = public_url
    return public_url
