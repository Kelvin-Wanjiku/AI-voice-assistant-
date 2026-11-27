"""The tables in Milo's database."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Profile(Base):
    """Basic facts and choices about the person. There is one row, because Milo has one user for now."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(60), default="")
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Home town, for the weather (Phase 5). Empty until the person sets it on About me.
    # New columns must allow "empty" (nullable), so older databases can be upgraded automatically.
    town: Mapped[str | None] = mapped_column(String(120), nullable=True, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Default reminder for new plans, in minutes before (Phase 6). -1 = no reminder; empty = 15.
    default_reminder: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # When to remind about the day's plans that have no time: "HH:MM"; "off"; empty = 09:00.
    morning_time: Mapped[str | None] = mapped_column(String(5), nullable=True)


class Memory(Base):
    """One thing Milo remembers, like "Has a farm and likes working on it"."""

    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    category: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20), default="chat")  # "chat" or "added" (typed on About me)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Plan(Base):
    """Something on the person's day: an appointment, an activity or a routine like morning tablets."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(120))
    day: Mapped[date] = mapped_column(Date)  # the date, or the first date for repeating plans
    time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "HH:MM", or empty for "any time"
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    place: Mapped[str | None] = mapped_column(String(120), nullable=True)  # where, e.g. "Old Trafford" or "Anna's house"
    repeat: Mapped[str] = mapped_column(String(10), default="none")  # "none", "daily" or "weekly"
    remind_before: Mapped[int | None] = mapped_column(Integer, nullable=True)  # minutes; empty = no reminder
    source: Mapped[str] = mapped_column(String(20), default="added")  # "chat" or "added" (on My day)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PlanDay(Base):
    """What happened to a plan on one particular day: done, reminded, or snoozed.

    Kept separately so a repeating plan ("tablets every morning") can be done on Monday but not yet on Tuesday.
    """

    __tablename__ = "plan_days"
    __table_args__ = (UniqueConstraint("plan_id", "day", name="one_row_per_plan_per_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(32), ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded: Mapped[bool] = mapped_column(Boolean, default=False)
    snooze_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # local time
