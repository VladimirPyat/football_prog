from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

SCORE_RANGE_CHECK = (
    "score1 IS NULL OR (score1 >= 0 AND score1 <= 20)",
    "score2 IS NULL OR (score2 >= 0 AND score2 <= 20)",
)


class UserRole(StrEnum):
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"
    USER = "USER"


class RoundStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CALCULATED = "CALCULATED"
    PUBLISHED = "PUBLISHED"


class MatchStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    POSTPONED = "POSTPONED"
    CANCELED = "CANCELED"
    VOID = "VOID"
    FINISHED = "FINISHED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    is_temp_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    contact: Mapped[Contact | None] = relationship(back_populates="user", uselist=False)


class Contact(Base):
    __tablename__ = "contacts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    vk_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tg_id: Mapped[str | None] = mapped_column(String, nullable=True)
    notify_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(back_populates="contact")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    short_name: Mapped[str] = mapped_column(String, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    matches_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("team1_id != team2_id", name="ck_matches_different_teams"),
        CheckConstraint(SCORE_RANGE_CHECK[0], name="ck_matches_score1_range"),
        CheckConstraint(SCORE_RANGE_CHECK[1], name="ck_matches_score2_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False)
    team1_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    team2_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "round_id",
            "match_id",
            name="uq_predictions_user_round_match",
        ),
        CheckConstraint(SCORE_RANGE_CHECK[0], name="ck_predictions_score1_range"),
        CheckConstraint(SCORE_RANGE_CHECK[1], name="ck_predictions_score2_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    score1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score2: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("user_id", "round_id", name="uq_scores_user_round"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False)
    points_exact: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_diff: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_outcome: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bonus1: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bonus2: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bonus3: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_without_bonus3: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_with_bonus3: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_outcomes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ContestSettings(Base):
    __tablename__ = "contest_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    total_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    matches_per_round: Mapped[int] = mapped_column(Integer, nullable=False)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    is_round_robin: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rules_json: Mapped[dict] = mapped_column(JSON, nullable=False)
