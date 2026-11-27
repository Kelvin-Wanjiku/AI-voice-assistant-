"""Where the Chat screen sends messages.

/api/chat/stream (used by the app) sends Milo's answer in small steps, one JSON object per line:
  {"type": "holding", "text": "Let me just check the weather for you."}   <- only if a look-up takes a while
  {"type": "reply", "reply": "...", "memory": {...}, "lookups": [...]}   <- the answer, always last
  {"type": "error", "detail": "..."}                                       <- instead of a reply, if it failed
That way Milo can say "let me check" straight away, and follow up by itself when the answer is ready.

/api/chat does the same in one go, without the holding line (handy for testing in /docs).
"""

import json
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIConnectionError, APIStatusError
from sqlalchemy.orm import Session

from app import memory_store as store
from app import planner
from app.config import get_settings
from app.db import get_db, get_session_factory
from app.holding import holding_line, still_working_line
from app.llm import BrainNotConfigured, current_setup
from app.memory_keeper import Plan, apply_plan, propose_changes
from app.personality import build_system_prompt
from app.schemas import ChatRequest, ChatResponse, Lookup, MemoryChanges, Source
from app.thinking import Progress, answer
from app.tools.registry import Context

router = APIRouter(tags=["chat"])
log = logging.getLogger("milo.chat")

MAX_HISTORY = 20  # only the most recent messages are sent, to keep replies fast and within free limits
STILL_WORKING_AFTER = 15.0  # seconds after the holding line, add "still looking"
SLOW_THINKING_AFTER = 8.0  # with no look-up, say "just a moment" if the AI is this slow

# Workers: one writes Milo's reply (looking things up if needed) while another decides what to remember.
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="milo-ai")


def explain_api_error(exc: APIStatusError) -> tuple[int, str]:
    """Turn an error from the AI provider into a message a person can act on."""
    text = str(exc).lower()
    code = exc.status_code
    try:
        setup = current_setup()
        provider, key_page = setup.provider.name, setup.provider.key_page
    except BrainNotConfigured:
        provider, key_page = "the AI provider", "your provider's website"

    if code in (401, 403) or (code == 400 and "api key" in text):
        return 503, f"{provider} rejected the API key. Copy it again from {key_page} into LLM_API_KEY, then restart the backend."
    if code == 402 or "credit" in text:
        return 503, f"Your {provider} account has no credit for this model. Choose a free model in LLM_MODEL."
    if code == 404 or (code == 400 and "model" in text):
        return 503, f"{provider} didn't recognise the model name. Check LLM_MODEL in backend/.env."
    if code == 429:
        return 503, (
            f"Milo has reached {provider}'s free limit for now. Wait a minute and try again. "
            "If it keeps happening, the daily limit may be used up, or this model may not be free."
        )
    if code >= 500:
        return 502, f"{provider} is busy right now. Please try again in a moment."
    return 502, f"{provider} returned an error ({code}). Try again in a moment."


def explain_failure(exc: Exception) -> tuple[int, str]:
    """Any failure while Milo was thinking -> (status code, a calm message for the person)."""
    if isinstance(exc, BrainNotConfigured):
        return 503, str(exc)
    if isinstance(exc, APIConnectionError):
        log.warning("Could not reach the AI provider: %s", exc)
        return 502, "Could not reach the AI service. Check the internet connection."
    if isinstance(exc, APIStatusError):
        log.warning("AI provider error %s: %s", exc.status_code, exc)  # full details in the backend terminal
        return explain_api_error(exc)
    log.error("Unexpected problem while Milo was thinking", exc_info=exc)
    return 502, "Something went wrong while Milo was thinking. Please try again."


@dataclass
class Turn:
    """One chat turn in progress: Milo's reply and the memory keeper, running side by side."""

    reply_job: Future
    keeper_job: Future
    progress: Progress
    memory_enabled: bool


def start_turn(body: ChatRequest, db: Session) -> Turn:
    history = [m.model_dump() for m in body.messages][-MAX_HISTORY:]

    # The AI expects the conversation to start with the person, and to end with them too.
    while history and history[0]["role"] != "user":
        history.pop(0)
    if not history or history[-1]["role"] != "user":
        raise HTTPException(status_code=422, detail="The conversation must end with a message from the user.")

    # What Milo knows right now.
    profile = store.get_profile(db)
    memories = store.list_memories(db)
    system = build_system_prompt(
        name=profile.name,
        memories=[(m.category, m.text) for m in memories],
        memory_enabled=profile.memory_enabled,
        plans=planner.summary_for_milo(db),
        default_reminder=planner.default_reminder(db),
    )
    ctx = Context(
        town=profile.town or "",
        latitude=profile.latitude,
        longitude=profile.longitude,
        memory_texts=[m.text for m in memories],
    )
    progress = Progress()
    return Turn(
        reply_job=_pool.submit(answer, system, history, ctx, progress),
        keeper_job=_pool.submit(propose_changes, history, [(m.id, m.category, m.text) for m in memories]),
        progress=progress,
        memory_enabled=profile.memory_enabled,
    )


def finish_turn(turn: Turn, db: Session) -> ChatResponse:
    """Once the reply is ready: save memory changes and put the response together. Raises if the reply failed."""
    reply, looked_up = turn.reply_job.result()
    if not reply:
        raise HTTPException(status_code=502, detail="The AI service sent an empty reply. Try again.")

    # Save the memory changes only now, once we know the reply worked.
    plan: Plan = turn.keeper_job.result()
    try:
        changes = apply_plan(db, plan, memory_enabled=turn.memory_enabled)
    except Exception as exc:  # noqa: BLE001 - a memory problem must never lose Milo's reply
        log.warning("Couldn't save memory changes: %s", exc)
        db.rollback()
        changes = MemoryChanges()

    lookups = [
        Lookup(label=r.label, failed=r.failed, sources=[Source(title=t, url=u) for t, u in r.sources])
        for r in looked_up
    ]
    return ChatResponse(
        reply=reply, memory=changes, lookups=lookups, plans_changed=any(r.changes_plans for r in looked_up)
    )


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    turn = start_turn(body, db)
    try:
        turn.reply_job.result()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        status, message = explain_failure(exc)
        raise HTTPException(status_code=status, detail=message) from exc
    return finish_turn(turn, db)


@router.post("/chat/stream")
def chat_stream(body: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    turn = start_turn(body, db)  # problems with the request itself are reported before streaming starts
    holding_after = max(0.5, get_settings().holding_after_seconds)

    def line(event: dict) -> str:
        return json.dumps(event) + "\n"

    def events():
        started = time.monotonic()
        held_at: float | None = None
        still_sent = False
        while not turn.reply_job.done():
            time.sleep(0.1)
            waited = time.monotonic() - started
            if held_at is None:
                looking = turn.progress.looking_up.is_set()
                if (looking and waited >= holding_after) or (not looking and waited >= max(SLOW_THINKING_AFTER, holding_after)):
                    held_at = waited
                    yield line({"type": "holding", "text": holding_line(turn.progress.tools)})
            elif not still_sent and waited - held_at >= STILL_WORKING_AFTER:
                still_sent = True
                yield line({"type": "holding", "text": still_working_line()})

        # The request's own database session may be closed by now, so use a fresh one.
        session = get_session_factory()()
        try:
            response = finish_turn(turn, session)
            yield line({"type": "reply", **response.model_dump()})
        except HTTPException as exc:
            yield line({"type": "error", "detail": exc.detail})
        except Exception as exc:  # noqa: BLE001
            yield line({"type": "error", "detail": explain_failure(exc)[1]})
        finally:
            session.close()

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
