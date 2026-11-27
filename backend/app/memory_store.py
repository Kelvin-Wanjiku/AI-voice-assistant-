"""Reading and changing what Milo remembers. Every change to memories goes through these functions."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Memory, Profile

# The groups shown on the About me screen, in this order.
CATEGORIES = ["Life and home", "Interests", "Food", "Routines", "Family and friends", "Health", "Goals"]

MAX_MEMORIES = 200  # a safety limit, so the list stays small enough to send with every message
MAX_TEXT = 200


def normalise_category(value: str | None) -> str:
    """Accept small differences like "interests" or "family", and fall back to a sensible group."""
    if not value:
        return "Life and home"
    v = value.strip().lower()
    for c in CATEGORIES:
        if v == c.lower() or v in c.lower().split():
            return c
    return "Life and home"


def clean_text(value: str) -> str:
    text = " ".join((value or "").split())  # tidy spaces and line breaks
    return text[:MAX_TEXT].rstrip(" .") if text else ""


# ---------- Profile ----------
def get_profile(db: Session) -> Profile:
    profile = db.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1, name="", memory_enabled=True)
        db.add(profile)
        db.commit()
    return profile


def update_profile(db: Session, name: str | None = None, memory_enabled: bool | None = None) -> Profile:
    profile = get_profile(db)
    if name is not None:
        profile.name = " ".join(name.split())[:60]
    if memory_enabled is not None:
        profile.memory_enabled = memory_enabled
    db.commit()
    return profile


def set_town(db: Session, town: str, latitude: float | None, longitude: float | None) -> Profile:
    """Save the person's home town for the weather. An empty town clears it."""
    profile = get_profile(db)
    profile.town = town
    profile.latitude = latitude if town else None
    profile.longitude = longitude if town else None
    db.commit()
    return profile


# ---------- Memories ----------
def list_memories(db: Session) -> list[Memory]:
    return list(db.scalars(select(Memory).order_by(Memory.created_at, Memory.id)))


def find_duplicate(db: Session, text: str) -> Memory | None:
    wanted = text.lower()
    return next((m for m in list_memories(db) if m.text.lower() == wanted), None)


def add_memory(db: Session, category: str, text: str, source: str = "chat") -> Memory | None:
    """Save a new memory. Returns None if it's empty, already known, or the list is full."""
    text = clean_text(text)
    if not text or find_duplicate(db, text):
        return None
    if len(list_memories(db)) >= MAX_MEMORIES:
        return None
    memory = Memory(category=normalise_category(category), text=text, source=source)
    db.add(memory)
    db.commit()
    return memory


def update_memory(db: Session, memory_id: str, text: str | None = None, category: str | None = None) -> Memory | None:
    memory = db.get(Memory, memory_id)
    if memory is None:
        return None
    if text is not None and clean_text(text):
        memory.text = clean_text(text)
    if category is not None:
        memory.category = normalise_category(category)
    db.commit()
    return memory


def delete_memory(db: Session, memory_id: str) -> Memory | None:
    memory = db.get(Memory, memory_id)
    if memory is None:
        return None
    db.delete(memory)
    db.commit()
    return memory


def delete_all_memories(db: Session) -> int:
    result = db.execute(delete(Memory))
    db.commit()
    return result.rowcount or 0
