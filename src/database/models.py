from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
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


class RoundKind(StrEnum):
    REGULAR = "REGULAR"
    SUPPLEMENTARY = "SUPPLEMENTARY"


class MatchStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    POSTPONED = "POSTPONED"
    CANCELED = "CANCELED"
    VOID = "VOID"
    FINISHED = "FINISHED"


class ContestLifecycleStatus(StrEnum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"


class ParticipantStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"


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


class Contest(Base):
    __tablename__ = "contests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'RUNNING', 'PAUSED', 'FINISHED')",
            name="ck_contests_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=ContestLifecycleStatus.DRAFT
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    matches_per_round: Mapped[int] = mapped_column(Integer, nullable=False)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    is_round_robin: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rules_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    participants: Mapped[list[ContestParticipant]] = relationship(
        back_populates="contest", cascade="all, delete-orphan"
    )
    teams: Mapped[list[Team]] = relationship(back_populates="contest", cascade="all, delete-orphan")
    rounds: Mapped[list[Round]] = relationship(back_populates="contest", cascade="all, delete-orphan")


class ContestRestoreSnapshot(Base):
    __tablename__ = "contest_restore_snapshots"

    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contests.id"), primary_key=True
    )
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


class ContestParticipant(Base):
    __tablename__ = "contest_participants"
    __table_args__ = (
        CheckConstraint(
            "exceptional_tiebreak_points >= 0",
            name="ck_contest_participants_tiebreak_nonneg",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED')",
            name="ck_contest_participants_status",
        ),
    )

    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=ParticipantStatus.ACCEPTED)
    exceptional_tiebreak_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    contest: Mapped[Contest] = relationship(back_populates="participants")
    user: Mapped[User] = relationship()


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("contest_id", "name", name="uq_teams_contest_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contests.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    short_name: Mapped[str] = mapped_column(String, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    contest: Mapped[Contest] = relationship(back_populates="teams")


class Round(Base):
    __tablename__ = "rounds"
    __table_args__ = (UniqueConstraint("contest_id", "number", name="uq_rounds_contest_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contests.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    matches_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kind: Mapped[str] = mapped_column(
        String, nullable=False, default=RoundKind.REGULAR.value
    )
    supplementary_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    contest: Mapped[Contest] = relationship(back_populates="rounds")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("team1_id != team2_id", name="ck_matches_different_teams"),
        CheckConstraint(SCORE_RANGE_CHECK[0], name="ck_matches_score1_range"),
        CheckConstraint(SCORE_RANGE_CHECK[1], name="ck_matches_score2_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False)
    origin_round_id: Mapped[int | None] = mapped_column(
        ForeignKey("rounds.id"), nullable=True
    )
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
    count_exact_high: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    count_exact: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    count_diff: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    count_outcome: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
