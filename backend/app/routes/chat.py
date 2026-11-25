import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from openai import APIConnectionError, APIStatusError
from pydantic import BaseModel, Field

from app.llm import BrainNotConfigured, ask_milo, current_setup

router = APIRouter(tags=["chat"])
log = logging.getLogger("milo.chat")

MAX_HISTORY = 20  # only the most recent messages are sent, to keep replies fast and within free limits


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str


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


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    history = [m.model_dump() for m in body.messages][-MAX_HISTORY:]

    # The AI expects the conversation to start with the person, and to end with them too.
    while history and history[0]["role"] != "user":
        history.pop(0)
    if not history or history[-1]["role"] != "user":
        raise HTTPException(status_code=422, detail="The conversation must end with a message from the user.")

    try:
        reply = ask_milo(history)
    except BrainNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except APIConnectionError as exc:
        log.warning("Could not reach the AI provider: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach the AI service. Check the internet connection.") from exc
    except APIStatusError as exc:
        log.warning("AI provider error %s: %s", exc.status_code, exc)  # full details in the backend terminal
        status, message = explain_api_error(exc)
        raise HTTPException(status_code=status, detail=message) from exc

    if not reply:
        raise HTTPException(status_code=502, detail="The AI service sent an empty reply. Try again.")
    return ChatResponse(reply=reply)
