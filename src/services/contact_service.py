"""User contact profile read/update."""

from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ValidationError
from database.models import Contact
from schemas.auth import ContactOut

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    if not _EMAIL_RE.match(value.strip()):
        raise ValidationError("Некорректный адрес электронной почты")
    return value.strip()


async def get_contacts(session: AsyncSession, user_id: int) -> ContactOut:
    """Return Contact row or empty defaults if no row."""
    contact = await session.get(Contact, user_id)
    if contact is None:
        return ContactOut(email=None, vk_id=None, tg_id=None, notify_enabled=False)
    return ContactOut.model_validate(contact)


async def upsert_contacts(
    session: AsyncSession,
    user_id: int,
    patch: dict[str, object],
) -> ContactOut:
    """Create or update contacts row; partial patch only."""
    contact = await session.get(Contact, user_id)
    if contact is None:
        contact = Contact(user_id=user_id)
        session.add(contact)

    if "email" in patch:
        raw = patch["email"]
        if raw is None or raw == "":
            contact.email = None
        else:
            contact.email = _validate_email(str(raw))

    if "vk_id" in patch:
        contact.vk_id = patch["vk_id"]  # type: ignore[assignment]

    if "tg_id" in patch:
        contact.tg_id = patch["tg_id"]  # type: ignore[assignment]

    if "notify_enabled" in patch:
        contact.notify_enabled = bool(patch["notify_enabled"])

    await session.flush()
    return ContactOut.model_validate(contact)
