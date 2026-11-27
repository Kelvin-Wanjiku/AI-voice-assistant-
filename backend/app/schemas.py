"""The shapes of data the backend sends and accepts. The frontend's types.ts mirrors these."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    text: str
    source: str


class MemoryIn(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=200)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    memory_enabled: bool
    town: str | None = ""
    default_reminder: int | None = 15  # minutes before; null = no reminder
    morning_time: str | None = "09:00"  # morning reminder for plans with no time; null = off
    plans_updated: int = 0  # after changing the default: how many existing plans changed with it


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    memory_enabled: bool | None = None
    town: str | None = Field(default=None, max_length=120)  # e.g. "Uppsala" or "Uppsala, Sweden"; "" clears it
    default_reminder: int | None = -2  # minutes before; null = no reminder; -2 = leave unchanged
    morning_time: str | None = "unchanged"  # "HH:MM"; null = off


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class MemoryChanges(BaseModel):
    """What the memory keeper changed during one chat turn, so the Chat screen can show it."""

    added: list[MemoryOut] = []
    updated: list[MemoryOut] = []
    removed: list[MemoryOut] = []
    name: str | None = None  # set when the person told Milo their name


class Source(BaseModel):
    title: str
    url: str


class Lookup(BaseModel):
    """Something Milo looked up while answering, e.g. "Checked the weather for Uppsala, Sweden"."""

    label: str
    sources: list[Source] = []
    failed: bool = False


class ChatResponse(BaseModel):
    reply: str
    memory: MemoryChanges = MemoryChanges()
    lookups: list[Lookup] = []
    plans_changed: bool = False  # Milo added, moved or removed something on My day


class WeatherOut(BaseModel):
    place: str
    temperature: int
    description: str
    high: int
    low: int
    rain_chance: int | None = None


class HeadlineOut(BaseModel):
    title: str
    url: str
    topic: str
    source: str


# ---------------------------------------------------------------- planner (Phase 6)
class PlanOut(BaseModel):
    id: str
    title: str
    date: str  # the day shown, "YYYY-MM-DD"
    time: str | None
    duration_minutes: int | None
    note: str | None
    repeat: str
    remind_before: int | None
    done: bool
    source: str
    starts_on: str  # first date, for repeating plans ("YYYY-MM-DD")
    place: str | None = None


class PlanIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    date: str  # "YYYY-MM-DD" (words like "tomorrow" also work)
    time: str | None = None  # "HH:MM"; empty for "any time"
    duration_minutes: int | None = None
    note: str | None = Field(default=None, max_length=200)
    place: str | None = Field(default=None, max_length=120)
    repeat: str = "none"
    remind_before: int | None = -1  # minutes before; null = no reminder; -1 = the person's default


class PlanChange(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    date: str | None = None
    time: str | None = None
    duration_minutes: int | None = None
    note: str | None = Field(default=None, max_length=200)
    place: str | None = Field(default=None, max_length=120)
    repeat: str | None = None
    remind_before: int | None = None


class PlanSaved(BaseModel):
    plan: PlanOut
    clashes: list[PlanOut] = []
    merged: str = ""  # set when an existing similar plan was completed instead of adding a new one


class DoneIn(BaseModel):
    date: str
    done: bool = True


class ReminderOut(BaseModel):
    plan_id: str
    date: str
    title: str
    time: str | None  # None for the morning reminder about a plan with no time
    minutes_until: int
    place: str | None = None
    kind: str = "timed"  # "timed" or "morning"


class ReminderAnswer(BaseModel):
    action: str  # "ok", "snooze" or "done"
    minutes: int = 10
