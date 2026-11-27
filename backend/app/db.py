"""Where Milo keeps things it should remember.

By default this is a small file on your computer (backend/milo.db), so nothing needs setting up.
Put a DATABASE_URL in backend/.env to use Supabase (or any PostgreSQL database) instead.
"""

from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

LOCAL_DB_FILE = Path(__file__).resolve().parent.parent / "milo.db"


class Base(DeclarativeBase):
    """Every table class in models.py builds on this."""


def database_url() -> str:
    url = get_settings().database_url.strip()
    return url or f"sqlite:///{LOCAL_DB_FILE.as_posix()}"


def using_local_file() -> bool:
    return database_url().startswith("sqlite")


@lru_cache
def get_engine() -> Engine:
    url = database_url()
    if url.startswith("sqlite"):
        # The web server answers requests from several threads; SQLite needs to be told that's fine.
        return create_engine(url, connect_args={"check_same_thread": False})
    # pool_pre_ping drops dead connections instead of failing on them later
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


_tables_ready = False


def get_db():
    """Gives each request its own database session, and always closes it afterwards."""
    if not _tables_ready:
        init_db()  # in case the database wasn't reachable when the backend started
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create Milo's tables if they don't exist yet. Safe to run every time the backend starts."""
    global _tables_ready
    from app import models  # noqa: F401 - importing registers the tables

    engine = get_engine()
    Base.metadata.create_all(engine)
    add_missing_columns(engine)
    _tables_ready = True


def add_missing_columns(engine: Engine) -> None:
    """Upgrade a database made by an earlier phase: add any new columns the tables don't have yet.

    create_all() only creates missing tables, not missing columns. This small helper adds columns,
    so your saved memories survive upgrades. (It never removes or changes existing columns.)
    """
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    column_type = column.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {column_type}'))


def check_database() -> tuple[str, str]:
    """Return (status, message). status is one of: ok, error."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - we want to report any failure plainly
        return "error", f"Could not connect: {type(exc).__name__}. Check DATABASE_URL in backend/.env."
    if using_local_file():
        return "ok", "Saved on this computer (backend/milo.db)"
    return "ok", "Connected to your online database"
