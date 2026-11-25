from fastapi import APIRouter

from app.config import get_settings
from app.db import check_database
from app.llm import BrainNotConfigured, current_setup

router = APIRouter(tags=["health"])


def check_brain() -> dict:
    """Checks the settings only. Whether the key really works shows up when you chat."""
    try:
        setup = current_setup()
        return {"status": "ok", "message": f"{setup.provider.name}, {setup.model}"}
    except BrainNotConfigured as exc:
        return {"status": "not_configured", "message": str(exc)}


@router.get("/health")
def health() -> dict:
    """Used by the frontend to show which parts of Milo are working."""
    db_status, db_message = check_database()
    return {
        "app": get_settings().app_name,
        "backend": {"status": "ok"},
        "ai": check_brain(),
        "database": {"status": db_status, "message": db_message},
    }
