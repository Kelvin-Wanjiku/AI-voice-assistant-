from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import get_settings


@lru_cache
def get_engine() -> Engine | None:
    """Create the database engine once. Returns None if no DATABASE_URL is set yet."""
    url = get_settings().database_url.strip()
    if not url:
        return None
    # pool_pre_ping drops dead connections instead of failing on them later
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


def check_database() -> tuple[str, str]:
    """Return (status, message). status is one of: ok, not_configured, error."""
    engine = get_engine()
    if engine is None:
        return "not_configured", "No database connected yet. Add DATABASE_URL to backend/.env."
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok", "Connected."
    except Exception as exc:  # noqa: BLE001 - we want to report any failure plainly
        return "error", f"Could not connect: {type(exc).__name__}. Check DATABASE_URL in backend/.env."
