"""Milo's diary tools: see, add, change, remove and tick off plans, by talking."""

from datetime import date

from app import planner
from app.db import get_session_factory
from app.planner import PlanProblem


def _today() -> date:
    return planner.now().date()


def _clash_text(clashes, today: date) -> str:
    if not clashes:
        return ""
    names = "; ".join(planner.describe(c, today, with_id=False) for c in clashes)
    return f" It clashes with: {names}. Tell the person and ask what they'd like to do."


def _int_or_none(value):
    if value in (None, "", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise PlanProblem(f"\"{value}\" isn't a number of minutes.") from None


def see_plans(args: dict) -> tuple[str, str]:
    today = _today()
    first = planner.parse_day(args.get("day") or "today", today)
    days = max(1, min(_int_or_none(args.get("days")) or 1, 14))
    with get_session_factory()() as db:
        found = planner.plans_between(db, first, days)
    lines = []
    for day, views in found.items():
        label = planner.say_day(day, today).capitalize()
        lines.append(f"{label}:" if views else f"{label}: nothing planned.")
        lines += [f"- {planner.describe(v, today)}" for v in views]
    span = planner.say_day(first, today) + (f" and the {days - 1} days after" if days > 1 else "")
    return f"Looked at your plans for {span}", "\n".join(lines)


def add(args: dict) -> tuple[str, str]:
    today = _today()
    day = planner.parse_day(args.get("date"), today)
    time = planner.parse_time(args.get("time"))
    remind = args.get("remind_before", planner.USE_DEFAULT)
    if remind in (None, ""):
        remind = planner.USE_DEFAULT
    with get_session_factory()() as db:
        view, clashes = planner.add_plan(
            db, str(args.get("title") or ""), day, time, _int_or_none(args.get("duration_minutes")),
            args.get("note"), str(args.get("repeat") or "none"), _int_or_none(remind), source="chat", today=today,
            place=args.get("place"),
        )
    if view.merged:
        text = f"{view.merged} Now (local time): {planner.describe(view, today)}.{_clash_text(clashes, today)}"
        return f"Updated your plans: {planner.describe(view, today, with_id=False)}", text
    text = f"Added (local time): {planner.describe(view, today)}.{_clash_text(clashes, today)}"
    if not view.time:
        text += " It has no time yet: Milo will remind them in the morning and can suggest a good time."
    return f"Added to your plans: {planner.describe(view, today, with_id=False)}", text


def change(args: dict) -> tuple[str, str]:
    today = _today()
    changes = {}
    if args.get("title"):
        changes["title"] = str(args["title"])
    if args.get("date"):
        changes["day"] = planner.parse_day(args["date"], today)
    if "time" in args:
        changes["time"] = planner.parse_time(args.get("time"))
    for key in ("duration_minutes", "remind_before"):
        if key in args:
            changes[key] = _int_or_none(args.get(key))
    if "note" in args:
        changes["note"] = args.get("note") or None
    if "place" in args:
        changes["place"] = (args.get("place") or "").strip()[:120] or None
    if args.get("repeat"):
        changes["repeat"] = str(args["repeat"])
    with get_session_factory()() as db:
        view, clashes = planner.update_plan(db, str(args.get("plan_id") or ""), **changes)
    text = f"Changed. Now (local time): {planner.describe(view, today)}.{_clash_text(clashes, today)}"
    return f"Changed a plan: {planner.describe(view, today, with_id=False)}", text


def remove(args: dict) -> tuple[str, str]:
    today = _today()
    with get_session_factory()() as db:
        view = planner.delete_plan(db, str(args.get("plan_id") or ""))
    what = planner.describe(view, today, with_id=False)
    return f"Removed from your plans: {what}", f"Removed: {what}."


def mark_done(args: dict) -> tuple[str, str]:
    today = _today()
    day = planner.parse_day(args.get("date") or "today", today)
    with get_session_factory()() as db:
        view = planner.set_done(db, str(args.get("plan_id") or ""), day, True)
    return f"Ticked off: {view.title}", f"Marked as done: {planner.describe(view, today, with_id=False)}."


def set_default_reminder(args: dict) -> tuple[str, str]:
    raw = args.get("minutes_before")
    minutes = None if raw in (None, "", "none", -1) else _int_or_none(raw)
    update_existing = args.get("update_existing", True) not in (False, "false", "no")
    with get_session_factory()() as db:
        changed = planner.set_default_reminder(db, minutes, update_existing)
    setting = "no reminder" if minutes is None else "at the time" if minutes == 0 else f"{minutes} minutes before"
    text = f"Default reminder is now: {setting}. "
    text += f"{changed} existing plan(s) changed to match." if update_existing else "Existing plans were left as they were."
    return f"Default reminder: {setting}", text
