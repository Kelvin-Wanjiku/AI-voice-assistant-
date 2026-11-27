"""Milo's planner: plans, repeats, clashes and reminders. Every change to plans goes through here.

Times are the person's local time (the laptop's clock). Each plan has a date and an optional time.
Repeating plans ("every day", "every week") show up on each matching day, and are ticked off per day.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.models import Plan, PlanDay, Profile

REPEATS = ("none", "daily", "weekly")
DEFAULT_REMINDER = 15  # minutes before, for plans with a time, unless the person chose another default
USE_DEFAULT = -1  # "use the person's default reminder" (the API and tools use this when nothing was chosen)
NO_REMINDER_SETTING = -1  # how "no reminder" is stored as the person's default
CLASH_LENGTH = 60  # minutes assumed for plans with no length, when checking for clashes
REMINDER_GRACE = 30  # minutes after the start that a missed reminder still shows
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class PlanProblem(Exception):
    """Something about a plan doesn't make sense. The message is safe to show or for Milo to say."""


def now() -> datetime:
    return datetime.now()


# ---------------------------------------------------------------- understanding dates and times
def parse_day(text: str | None, today: date) -> date:
    """"2026-11-27", "today", "tomorrow", "thursday", "next friday", "27 November", "27/11"."""
    t = " ".join((text or "").lower().replace(",", " ").split())
    if not t or t == "today":
        return today
    if t == "tomorrow":
        return today + timedelta(days=1)
    if t in ("day after tomorrow", "the day after tomorrow"):
        return today + timedelta(days=2)
    words = t.replace("this ", "").replace("on ", "").split()
    if words and words[-1] in WEEKDAYS and len(words) <= 2:
        ahead = (WEEKDAYS.index(words[-1]) - today.weekday()) % 7
        if words[0] == "next" and ahead == 0:
            ahead = 7
        return today + timedelta(days=ahead)
    try:
        return date.fromisoformat(t[:10])
    except ValueError:
        pass
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%d %B", "%d %b", "%B %d", "%b %d", "%d/%m/%Y", "%d/%m", "%d.%m.%Y", "%d.%m"):
        try:
            parsed = datetime.strptime(t.replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " "), fmt)
        except ValueError:
            continue
        if "%Y" not in fmt:  # no year given: the next time that date comes round
            parsed = parsed.replace(year=today.year)
            if parsed.date() < today:
                parsed = parsed.replace(year=today.year + 1)
        return parsed.date()
    raise PlanProblem(f"I couldn't work out the date \"{text}\".")


def parse_time(text: str | None) -> str | None:
    """"10", "10am", "3:30 pm", "15:00", "noon" -> "HH:MM". Empty -> None (any time of day)."""
    t = (text or "").strip().lower().replace(".", ":").replace(" ", "")
    if not t or t in ("anytime", "none", "null", "allday"):
        return None
    if t in ("noon", "midday"):
        return "12:00"
    if t == "midnight":
        return "00:00"
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", t)
    if not m:
        raise PlanProblem(f"I couldn't work out the time \"{text}\".")
    hour, minute, half = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if half == "pm" and hour < 12:
        hour += 12
    if half == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        raise PlanProblem(f"\"{text}\" isn't a time of day.")
    return f"{hour:02d}:{minute:02d}"


def say_day(d: date, today: date) -> str:
    if d == today:
        return "today"
    if d == today + timedelta(days=1):
        return "tomorrow"
    if today < d < today + timedelta(days=7):
        return d.strftime("%A")
    return d.strftime("%A %d %B").replace(" 0", " ")


# ---------------------------------------------------------------- the person's default reminder
def default_reminder(db: Session) -> int | None:
    """Minutes before, or None for "no reminder"."""
    profile = db.get(Profile, 1)
    stored = profile.default_reminder if profile else None
    if stored is None:
        return DEFAULT_REMINDER
    return None if stored == NO_REMINDER_SETTING else stored


def set_default_reminder(db: Session, minutes: int | None, update_existing: bool = True) -> int:
    """Change the default. With update_existing, plans that still use the old default change too
    (plans whose reminder was set individually keep it). Returns how many plans changed."""
    if minutes is not None and not 0 <= minutes <= 24 * 60:
        raise PlanProblem("A reminder can be at the time, or up to a day before.")
    old = default_reminder(db)
    profile = db.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1, name="", memory_enabled=True)
        db.add(profile)
    profile.default_reminder = NO_REMINDER_SETTING if minutes is None else minutes
    changed = 0
    if update_existing and old != minutes:
        today = now().date()
        for plan in db.scalars(select(Plan).where(Plan.time.is_not(None))):
            still_ahead = plan.repeat != "none" or plan.day >= today
            if still_ahead and plan.remind_before == old:
                plan.remind_before = minutes
                changed += 1
    db.commit()
    return changed


DEFAULT_MORNING = "09:00"


def morning_time(db: Session) -> str | None:
    """When to remind about plans with no time: "HH:MM", or None when switched off."""
    profile = db.get(Profile, 1)
    stored = profile.morning_time if profile else None
    if not stored:
        return DEFAULT_MORNING
    return None if stored == "off" else stored


def set_morning_time(db: Session, value: str | None) -> str | None:
    """value: "HH:MM", or None for off."""
    profile = db.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1, name="", memory_enabled=True)
        db.add(profile)
    profile.morning_time = parse_time(value) if value else "off"
    db.commit()
    return morning_time(db)


# ---------------------------------------------------------------- reading plans
@dataclass
class PlanView:
    """One plan as it appears on one particular day."""

    id: str
    title: str
    day: date  # the day being shown
    time: str | None
    duration_minutes: int | None
    note: str | None
    repeat: str
    remind_before: int | None
    done: bool
    source: str
    starts_on: date  # first date (for repeating plans)
    place: str | None = None
    merged: str = ""  # set when adding filled in an existing plan instead of making a new one


def occurs_on(plan: Plan, day: date) -> bool:
    if day < plan.day:
        return False
    if plan.repeat == "daily":
        return True
    if plan.repeat == "weekly":
        return day.weekday() == plan.day.weekday()
    return day == plan.day


def _view(plan: Plan, day: date, state: PlanDay | None) -> PlanView:
    return PlanView(
        id=plan.id, title=plan.title, day=day, time=plan.time, duration_minutes=plan.duration_minutes,
        note=plan.note, repeat=plan.repeat, remind_before=plan.remind_before,
        done=bool(state and state.done), source=plan.source, starts_on=plan.day, place=plan.place,
    )


def _sort_key(v: PlanView):
    return (v.time is None, v.time or "", v.title.lower())


def plans_on(db: Session, day: date) -> list[PlanView]:
    candidates = db.scalars(
        select(Plan).where(or_(Plan.day == day, and_(Plan.repeat != "none", Plan.day <= day)))
    ).all()
    states = {s.plan_id: s for s in db.scalars(select(PlanDay).where(PlanDay.day == day))}
    return sorted((_view(p, day, states.get(p.id)) for p in candidates if occurs_on(p, day)), key=_sort_key)


def plans_between(db: Session, first: date, days: int) -> dict[date, list[PlanView]]:
    return {first + timedelta(days=i): plans_on(db, first + timedelta(days=i)) for i in range(days)}


def get_plan(db: Session, plan_id: str) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise PlanProblem("That plan isn't there any more.")
    return plan


# ---------------------------------------------------------------- clashes
def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def clashes(db: Session, day: date, time: str | None, duration: int | None, ignore_id: str | None = None) -> list[PlanView]:
    """Other plans with a time that overlap this one on that day."""
    if not time:
        return []
    start = _minutes(time)
    end = start + (duration or CLASH_LENGTH)
    found = []
    for other in plans_on(db, day):
        if other.id == ignore_id or not other.time or other.done:
            continue
        o_start = _minutes(other.time)
        o_end = o_start + (other.duration_minutes or CLASH_LENGTH)
        if start < o_end and o_start < end:
            found.append(other)
    return found


# ---------------------------------------------------------------- changing plans
def _check(title: str, repeat: str, duration: int | None, remind_before: int | None) -> tuple[str, str]:
    title = " ".join((title or "").split())[:120]
    if not title:
        raise PlanProblem("A plan needs a name, like \"Doctor\" or \"Walk in the park\".")
    repeat = (repeat or "none").lower()
    if repeat not in REPEATS:
        raise PlanProblem("A plan can happen once, every day or every week.")
    if duration is not None and not 0 < duration <= 24 * 60:
        raise PlanProblem("That length of time doesn't look right.")
    if remind_before is not None and not 0 <= remind_before <= 24 * 60:
        raise PlanProblem("A reminder can be at the time, or up to a day before.")
    return title, repeat


FILLER_WORDS = {"the", "a", "an", "my", "game", "match", "vs", "v", "versus", "against", "with", "and", "at", "to", "of"}


def _key_words(title: str) -> set[str]:
    words = re.sub(r"[^\w\s]", " ", title.lower()).split()
    return {w for w in words if w not in FILLER_WORDS}


def similar_titles(a: str, b: str) -> bool:
    """"Man United vs Brentford" and "Manchester United vs Brentford game" are the same plan, roughly:
    the shorter one's important words all appear in the longer one."""
    ka, kb = _key_words(a), _key_words(b)
    if not ka or not kb:
        return a.strip().lower() == b.strip().lower()
    small, big = (ka, kb) if len(ka) <= len(kb) else (kb, ka)
    if small <= big:
        return True
    # allow shortened names: "man" for "manchester", "utd" for "united"
    def same(w: str, x: str) -> bool:
        if w == x or {w, x} == {"utd", "united"}:
            return True
        short, long = (w, x) if len(w) <= len(x) else (x, w)
        return len(short) >= 3 and long.startswith(short)

    return all(any(same(w, x) for x in big) for w in small)


def _clean(text: str | None, limit: int) -> str | None:
    return " ".join((text or "").split())[:limit] or None


def add_plan(
    db: Session, title: str, day: date, time: str | None = None, duration_minutes: int | None = None,
    note: str | None = None, repeat: str = "none", remind_before: int | None = USE_DEFAULT,
    source: str = "added", today: date | None = None, place: str | None = None,
) -> tuple[PlanView, list[PlanView]]:
    """Save a new plan. Returns it with any clashes (it's saved anyway: the person decides).
    remind_before=USE_DEFAULT uses the person's default reminder.

    If a plan with a similar name is already on that day, it's completed instead of duplicated:
    a missing time, place or note is filled in. (The returned view's `merged` says so.)"""
    today = today or now().date()
    if remind_before == USE_DEFAULT:
        remind_before = default_reminder(db)
    title, repeat = _check(title, repeat, duration_minutes, remind_before)
    if day < today and repeat == "none":
        raise PlanProblem(f"{day.strftime('%A %d %B')} has already passed.")
    place, note = _clean(place, 120), _clean(note, 200)

    for existing in plans_on(db, day):
        if existing.repeat != repeat or not similar_titles(existing.title, title):
            continue
        if time and existing.time and existing.time != time:
            continue  # same name, different time: probably two different things
        plan = get_plan(db, existing.id)
        filled = []
        if time and not plan.time:
            plan.time = time
            plan.remind_before = remind_before
            filled.append(f"time {time}")
            # The morning "no time yet" reminder may have been seen; the timed one should still come.
            db.execute(delete(PlanDay).where(PlanDay.plan_id == plan.id, PlanDay.done.is_(False)))
        if place and not plan.place:
            plan.place = place
            filled.append(f"place {place}")
        if note and not plan.note:
            plan.note = note
            filled.append("note")
        if duration_minutes and not plan.duration_minutes:
            plan.duration_minutes = duration_minutes
        db.commit()
        view = _view(plan, day, None)
        view.merged = (
            f"It was already on the plans as \"{plan.title}\"; filled in: {', '.join(filled)}." if filled
            else f"It was already on the plans as \"{plan.title}\"; nothing new to add."
        )
        found = clashes(db, day, plan.time, plan.duration_minutes, ignore_id=plan.id) if filled else []
        return view, found

    found = clashes(db, day, time, duration_minutes)
    plan = Plan(
        title=title, day=day, time=time, duration_minutes=duration_minutes, note=note, place=place,
        repeat=repeat, remind_before=remind_before if time else None, source=source,
    )
    db.add(plan)
    db.commit()
    return _view(plan, day, None), found


def update_plan(db: Session, plan_id: str, **changes) -> tuple[PlanView, list[PlanView]]:
    """Change some details of a plan. Only the fields given are changed."""
    plan = get_plan(db, plan_id)
    if changes.get("remind_before") == USE_DEFAULT:
        changes["remind_before"] = default_reminder(db)
    for key in ("title", "day", "time", "duration_minutes", "note", "place", "repeat", "remind_before"):
        if key in changes:
            setattr(plan, key, changes[key])
    plan.title, plan.repeat = _check(plan.title, plan.repeat, plan.duration_minutes, plan.remind_before)
    if not plan.time:
        plan.remind_before = None
    elif "time" in changes and "remind_before" not in changes and plan.remind_before is None:
        plan.remind_before = default_reminder(db)
    # A changed date or time starts afresh: reminders for the old one no longer apply.
    if "day" in changes or "time" in changes:
        db.execute(delete(PlanDay).where(PlanDay.plan_id == plan.id, PlanDay.done.is_(False)))
    db.commit()
    found = clashes(db, plan.day, plan.time, plan.duration_minutes, ignore_id=plan.id)
    return _view(plan, plan.day, None), found


def delete_plan(db: Session, plan_id: str) -> PlanView:
    plan = get_plan(db, plan_id)
    view = _view(plan, plan.day, None)
    db.execute(delete(PlanDay).where(PlanDay.plan_id == plan_id))
    db.delete(plan)
    db.commit()
    return view


def _state(db: Session, plan_id: str, day: date) -> PlanDay:
    state = db.scalar(select(PlanDay).where(PlanDay.plan_id == plan_id, PlanDay.day == day))
    if state is None:
        state = PlanDay(plan_id=plan_id, day=day, done=False, reminded=False)
        db.add(state)
    return state


def set_done(db: Session, plan_id: str, day: date, done: bool = True) -> PlanView:
    plan = get_plan(db, plan_id)
    if not occurs_on(plan, day):
        raise PlanProblem("That plan isn't on that day.")
    state = _state(db, plan_id, day)
    state.done = done
    if done:
        state.reminded = True
    db.commit()
    return _view(plan, day, state)


# ---------------------------------------------------------------- reminders
MORNING_UNTIL = "21:00"  # untimed plans are no longer nudged after this


@dataclass
class Due:
    plan_id: str
    day: date
    title: str
    time: str | None  # None for a plan with no time (the morning reminder)
    minutes_until: int  # negative when it has already started; 0 for the morning reminder
    place: str | None = None
    kind: str = "timed"  # "timed" or "morning"


def due_reminders(db: Session, at: datetime | None = None) -> list[Due]:
    at = at or now()
    today = at.date()
    states = {s.plan_id: s for s in db.scalars(select(PlanDay).where(PlanDay.day == today))}
    morning = morning_time(db)
    clock = at.strftime("%H:%M")
    due = []
    for view in plans_on(db, today):
        state = states.get(view.id)
        if view.done or (state and state.reminded):
            continue
        if state and state.snooze_until and state.snooze_until > at:
            continue
        if not view.time:
            # No time yet: remind in the morning, so it can be fitted into the day.
            if morning and morning <= clock < MORNING_UNTIL:
                due.append(Due(view.id, today, view.title, None, 0, view.place, kind="morning"))
            continue
        if view.remind_before is None:
            continue
        starts = datetime.combine(today, datetime.strptime(view.time, "%H:%M").time())
        if starts - timedelta(minutes=view.remind_before) <= at <= starts + timedelta(minutes=REMINDER_GRACE):
            due.append(Due(view.id, today, view.title, view.time, round((starts - at).total_seconds() / 60), view.place))
    return sorted(due, key=lambda d: (d.time is not None, d.time or ""))


def answer_reminder(db: Session, plan_id: str, day: date, action: str, snooze_minutes: int = 10, at: datetime | None = None) -> None:
    """action: "ok" (seen it), "snooze" (remind again later) or "done"."""
    get_plan(db, plan_id)
    state = _state(db, plan_id, day)
    if action == "snooze":
        state.reminded = False
        state.snooze_until = (at or now()) + timedelta(minutes=max(1, min(snooze_minutes, 240)))
    elif action == "done":
        state.done = True
        state.reminded = True
    elif action == "ok":
        state.reminded = True
    else:
        raise PlanProblem("Unknown reminder answer.")
    db.commit()


# ---------------------------------------------------------------- for Milo to read
def describe(view: PlanView, today: date, with_id: bool = True) -> str:
    when = say_day(view.day, today) + (f" at {view.time}" if view.time else " (any time)")
    extras = []
    if view.repeat == "daily":
        extras.append("every day")
    elif view.repeat == "weekly":
        extras.append(f"every {view.starts_on.strftime('%A')}")
    if view.duration_minutes:
        extras.append(f"{view.duration_minutes} min")
    if view.time:
        extras.append(
            "no reminder" if view.remind_before is None
            else "reminder at the time" if view.remind_before == 0
            else f"reminder {view.remind_before} min before"
        )
    if view.place:
        extras.append(f"at {view.place}")
    if view.note:
        extras.append(view.note)
    if view.done:
        extras.append("done")
    text = f"{when}: {view.title}" + (f" ({'; '.join(extras)})" if extras else "")
    return f"[id={view.id}] {text}" if with_id else text


def summary_for_milo(db: Session, today: date | None = None, days: int = 2) -> str:
    """Today's and tomorrow's plans, for Milo's instructions."""
    today = today or now().date()
    lines = []
    for day, views in plans_between(db, today, days).items():
        label = say_day(day, today).capitalize()
        if views:
            lines.append(f"{label}:")
            lines += [f"- {describe(v, today)}" for v in views]
        else:
            lines.append(f"{label}: nothing planned.")
    return "\n".join(lines)
