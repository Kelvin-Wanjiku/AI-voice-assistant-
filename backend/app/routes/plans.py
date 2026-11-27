"""The addresses My day and the reminder pop-up use."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import planner
from app.db import get_db
from app.planner import PlanProblem, PlanView
from app.schemas import DoneIn, PlanChange, PlanIn, PlanOut, PlanSaved, ReminderAnswer, ReminderOut

router = APIRouter(tags=["plans"])


def out(v: PlanView) -> PlanOut:
    return PlanOut(
        id=v.id, title=v.title, date=v.day.isoformat(), time=v.time, duration_minutes=v.duration_minutes,
        note=v.note, repeat=v.repeat, remind_before=v.remind_before, done=v.done, source=v.source,
        starts_on=v.starts_on.isoformat(), place=v.place,
    )


def _day(text: str | None) -> date:
    try:
        return planner.parse_day(text, planner.now().date())
    except PlanProblem as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _time(text: str | None) -> str | None:
    try:
        return planner.parse_time(text)
    except PlanProblem as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plans", response_model=list[PlanOut])
def plans_for_day(date: str | None = None, db: Session = Depends(get_db)):
    return [out(v) for v in planner.plans_on(db, _day(date))]


@router.get("/plans/upcoming", response_model=list[PlanOut])
def upcoming(days: int = 2, db: Session = Depends(get_db)):
    """Plans from now on, today and the next days, in order. Used by Home's "Coming up"."""
    at = planner.now()
    found = []
    for day, views in planner.plans_between(db, at.date(), max(1, min(days, 14))).items():
        for v in views:
            if v.done:
                continue
            if day == at.date() and v.time and v.time < at.strftime("%H:%M"):
                continue  # already passed today
            found.append(out(v))
    return found


@router.post("/plans", response_model=PlanSaved, status_code=201)
def create_plan(body: PlanIn, db: Session = Depends(get_db)):
    try:
        plan, clashes = planner.add_plan(
            db, body.title, _day(body.date), _time(body.time), body.duration_minutes, body.note,
            body.repeat, body.remind_before, source="added", place=body.place,
        )
    except PlanProblem as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlanSaved(plan=out(plan), clashes=[out(c) for c in clashes], merged=plan.merged)


@router.put("/plans/{plan_id}", response_model=PlanSaved)
def change_plan(plan_id: str, body: PlanChange, db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_unset=True)
    if "date" in changes:
        changes["day"] = _day(changes.pop("date"))
    if "time" in changes:
        changes["time"] = _time(changes["time"])
    try:
        plan, clashes = planner.update_plan(db, plan_id, **changes)
    except PlanProblem as exc:
        raise HTTPException(status_code=404 if "isn't there" in str(exc) else 400, detail=str(exc)) from exc
    return PlanSaved(plan=out(plan), clashes=[out(c) for c in clashes])


@router.delete("/plans/{plan_id}", response_model=PlanOut)
def remove_plan(plan_id: str, db: Session = Depends(get_db)):
    try:
        return out(planner.delete_plan(db, plan_id))
    except PlanProblem as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/done", response_model=PlanOut)
def mark_done(plan_id: str, body: DoneIn, db: Session = Depends(get_db)):
    try:
        return out(planner.set_done(db, plan_id, _day(body.date), body.done))
    except PlanProblem as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reminders", response_model=list[ReminderOut])
def reminders_due(db: Session = Depends(get_db)):
    return [
        ReminderOut(
            plan_id=d.plan_id, date=d.day.isoformat(), title=d.title, time=d.time,
            minutes_until=d.minutes_until, place=d.place, kind=d.kind,
        )
        for d in planner.due_reminders(db)
    ]


@router.post("/reminders/{plan_id}/{day}")
def answer_reminder(plan_id: str, day: str, body: ReminderAnswer, db: Session = Depends(get_db)):
    try:
        planner.answer_reminder(db, plan_id, _day(day), body.action, body.minutes)
    except PlanProblem as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}
