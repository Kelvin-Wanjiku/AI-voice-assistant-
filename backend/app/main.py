from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import chat, health

settings = get_settings()

app = FastAPI(title=f"{settings.app_name} API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every route lives under /api so the frontend dev server can proxy it easily.
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
