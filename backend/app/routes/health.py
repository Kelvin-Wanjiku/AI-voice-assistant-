from fastapi import APIRouter

from app.config import get_settings
from app.db import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Used by the frontend to show that Milo's backend and database are working."""
    db_status, db_message = check_database()
    return {
        "app": get_settings().app_name,
        "backend": {"status": "ok"},
        "database": {"status": db_status, "message": db_message},
    }
