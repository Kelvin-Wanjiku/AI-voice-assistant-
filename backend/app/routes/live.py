"""Live information for the Home screen: today's weather and personal headlines."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import memory_store as store
from app.db import get_db
from app.schemas import HeadlineOut, WeatherOut
from app.tools import news, weather
from app.tools.http import LookupFailed

router = APIRouter(tags=["live"])


@router.get("/weather", response_model=WeatherOut)
def todays_weather(db: Session = Depends(get_db)):
    profile = store.get_profile(db)
    if not profile.town or profile.latitude is None or profile.longitude is None:
        raise HTTPException(status_code=409, detail="Add your town on the About me screen to see the weather.")
    place = weather.Place(profile.town, profile.latitude, profile.longitude, "auto")
    try:
        return weather.summary_for_home(place)
    except LookupFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/news", response_model=list[HeadlineOut])
def headlines(limit: int = 4, db: Session = Depends(get_db)):
    memory_texts = [m.text for m in store.list_memories(db)]
    try:
        items = news.headlines_for_home(memory_texts, limit=max(1, min(limit, 8)))
    except LookupFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [HeadlineOut(title=h.title, url=h.url, topic=h.topic, source=h.source) for h in items]
