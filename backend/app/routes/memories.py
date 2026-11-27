"""The addresses the About me screen uses to show, add and remove memories, and to change the profile."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import memory_store as store
from app import planner
from app.planner import PlanProblem
from app.db import get_db
from app.schemas import MemoryIn, MemoryOut, ProfileIn, ProfileOut
from app.tools import weather
from app.tools.http import LookupFailed

router = APIRouter(tags=["memory"])


@router.get("/profile", response_model=ProfileOut)
def read_profile(db: Session = Depends(get_db)):
    return profile_out(store.get_profile(db), db)


@router.put("/profile", response_model=ProfileOut)
def change_profile(body: ProfileIn, db: Session = Depends(get_db)):
    if body.town is not None:
        town = " ".join(body.town.split())
        if not town:
            store.set_town(db, "", None, None)
        else:
            try:
                place = weather.find_place(town)
            except LookupFailed as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            store.set_town(db, place.name, place.latitude, place.longitude)
    changed = 0
    if body.default_reminder != -2:
        try:
            changed = planner.set_default_reminder(db, body.default_reminder, update_existing=True)
        except PlanProblem as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.morning_time != "unchanged":
        try:
            planner.set_morning_time(db, body.morning_time)
        except PlanProblem as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    profile = store.update_profile(db, name=body.name, memory_enabled=body.memory_enabled)
    return profile_out(profile, db, plans_updated=changed)


def profile_out(profile, db: Session, plans_updated: int = 0) -> ProfileOut:
    return ProfileOut(
        name=profile.name, memory_enabled=profile.memory_enabled, town=profile.town or "",
        default_reminder=planner.default_reminder(db), morning_time=planner.morning_time(db),
        plans_updated=plans_updated,
    )


@router.get("/memories", response_model=list[MemoryOut])
def read_memories(db: Session = Depends(get_db)):
    return store.list_memories(db)


@router.get("/memories/categories", response_model=list[str])
def read_categories():
    return store.CATEGORIES


@router.post("/memories", response_model=MemoryOut, status_code=201)
def create_memory(body: MemoryIn, db: Session = Depends(get_db)):
    memory = store.add_memory(db, body.category, body.text, source="added")
    if memory is None:
        if store.find_duplicate(db, store.clean_text(body.text)):
            raise HTTPException(status_code=409, detail="Milo already remembers that.")
        raise HTTPException(status_code=400, detail="That couldn't be saved. Milo's memory may be full.")
    return memory


@router.delete("/memories/{memory_id}", response_model=MemoryOut)
def forget_memory(memory_id: str, db: Session = Depends(get_db)):
    memory = store.delete_memory(db, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Milo doesn't remember that any more.")
    return memory


@router.delete("/memories", response_model=dict)
def forget_everything(db: Session = Depends(get_db)):
    return {"forgotten": store.delete_all_memories(db)}
