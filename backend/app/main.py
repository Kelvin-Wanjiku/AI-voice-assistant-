import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import init_db
from app.routes import chat, health, live, memories, plans

settings = get_settings()
log = logging.getLogger("milo")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()  # make sure Milo's memory tables exist before the first request
    except SQLAlchemyError as exc:
        # Keep running, so the app can explain the problem instead of crashing.
        log.error("Milo's memory database isn't reachable: %s", exc.__class__.__name__)
    yield


app = FastAPI(title=f"{settings.app_name} API", version="0.6.0", lifespan=lifespan)

@app.exception_handler(SQLAlchemyError)
async def database_problem(_request: Request, exc: SQLAlchemyError):
    log.error("Database problem: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Milo can't reach its memory database. Check DATABASE_URL in backend/.env, or leave it empty to save memories on this computer."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every route lives under /api so the frontend dev server can proxy it easily.
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(memories.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
