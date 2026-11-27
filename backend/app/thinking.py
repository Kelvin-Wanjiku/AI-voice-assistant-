"""How Milo answers one message, step by step.

1. Ask the AI: answer now, or look something up first? (It sees the list of tools.)
2. If it wants tools: run them at the same time, then ask again, with what was found added to its
   instructions as plain notes. It may do ONE more round of look-ups if the first didn't settle it.
3. The final reply must be an answer. If it still says "let me check" or describes its searches,
   it's sent back once with a firm instruction to answer now.

Results are given as notes rather than "tool messages". That works the same on every AI provider,
including Gemini, which otherwise needs hidden extra data sent back.

While this runs, `progress` tells the chat route what's happening, so it can say
"Let me just check the weather for you" if the answer takes a few seconds.
"""

import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from openai import BadRequestError

from app.llm import complete, complete_or_choose_tools
from app.tools.registry import DIARY_CHANGES, Context, ToolResult, parse_arguments, run_tool, tool_specs

log = logging.getLogger("milo.thinking")

_tool_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="milo-tool")

MAX_ROUNDS = 2  # look-up rounds per message
MAX_LOOKUPS = 5  # look-ups per message, across both rounds
MAX_PER_ROUND = 3

LOOKUP_NOTES = """Live information you have ALREADY looked up for the person's latest message is below. \
The look-ups are finished: answer their question now, using it, in your own words and briefly. \
Mention where it's from when that helps (for example "the BBC says"), but never read out web addresses. \
Don't say you'll check, look up, or get back to them, and don't describe your searches. \
If the information doesn't fully answer the question, say what you found and what you couldn't find out."""

FINAL_ROUND = """You can't look anything else up for this reply."""

ANSWER_NOW = """Your last draft didn't answer the person. Answer their latest message now, in one to three sentences, \
using what you know and the information above. Never say "let me check", "one moment" or similar, \
and never describe searches or write anything in square brackets."""

# Replies that only promise to answer later, instead of answering.
STALLING = re.compile(
    r"\b(let me (just |quickly )?(double[- ]?)?(check|look|find|see|search)|i'?ll (just )?(check|look|find|search|get back)"
    r"|one (moment|sec|second)|give me a (moment|sec|second)|bear with me|hold on|i'?ll let you know)\b",
    re.IGNORECASE,
)
# Replies that say a plan was changed ("I've added it", "I'll remind you 10 minutes before").
CLAIMS_A_CHANGE = re.compile(
    r"\b(i'?ve|i have|i'?ll|i will)\s+(just\s+|now\s+|also\s+)?"
    r"(added|put|moved|changed|set|updated|removed|cancell?ed|deleted|booked|scheduled|ticked|make sure to remind|remind you)\b",
    re.IGNORECASE,
)
CHECK_YOUR_CLAIM = """Your draft says you've changed the person's plans or reminders, but your diary tools haven't \
changed anything in this reply. If they asked for a change, make it now with the diary tools. \
If not, answer without saying you've changed anything."""
BE_HONEST = """Nothing was changed in the person's plans during this reply. Answer now without saying you've added, \
moved, set or changed anything, and without promising to do it later. If a change is needed, say what you'd change \
and ask them to confirm."""

# Lines like "[Searched the web for ...]" that some models write instead of answering.
BRACKET_LINES = re.compile(r"^\s*\[[^\]]*\]\s*$", re.MULTILINE)


@dataclass
class Progress:
    """Shared between the thinking thread and the chat route, to know when to say "let me check"."""

    tools: list[str] = field(default_factory=list)  # tools being used right now
    looking_up: threading.Event = field(default_factory=threading.Event)


def clean_reply(text: str) -> str:
    text = BRACKET_LINES.sub("", text or "")
    text = re.sub(r"\[(searched|checked|looking|search|tool)[^\]]*\]", "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()


def is_stalling(text: str) -> bool:
    """True when the reply is only a promise to check, not an answer."""
    return not text or (len(text) < 220 and bool(STALLING.search(text)))


def _run_lookups(calls: list[tuple[str, str]], ctx: Context, done: set[str], limit: int) -> list[ToolResult]:
    jobs = []
    for name, raw_args in calls:
        args = parse_arguments(raw_args)
        key = f"{name} {json.dumps(args, sort_keys=True)}"
        if key in done:
            continue  # don't repeat an identical look-up
        done.add(key)
        jobs.append(_tool_pool.submit(run_tool, name, args, ctx))
        if len(jobs) >= limit:
            break
    return [job.result() for job in jobs]


def _with_notes(system: str, results: list[ToolResult], final: bool) -> str:
    notes = "\n\n".join(f"[{r.label}]\n{r.text}" for r in results)
    return f"{system}\n\n{LOOKUP_NOTES}" + (f" {FINAL_ROUND}" if final else "") + f"\n\n{notes}"


def answer(system: str, history: list[dict], ctx: Context, progress: Progress | None = None) -> tuple[str, list[ToolResult]]:
    """Returns Milo's reply and what was looked up along the way."""
    progress = progress or Progress()
    results: list[ToolResult] = []
    done: set[str] = set()
    current_system = system

    for round_number in range(1, MAX_ROUNDS + 1):
        try:
            # Once plans have been changed, the second round may only read them, so nothing is added twice.
            leave_out = DIARY_CHANGES if any(r.changes_plans for r in results) else set()
            specs = tool_specs(leave_out)
            text, calls = complete_or_choose_tools(current_system, history, specs)
            offered = {t["function"]["name"] for t in specs}
            calls = [c for c in calls if c[0] in offered]  # never run a tool that wasn't offered
        except BadRequestError as exc:
            # A provider or model that doesn't support tools: answer without them.
            log.warning("Tools not accepted by this AI model (%s); answering without them.", exc.status_code)
            text, calls = complete(current_system, history), []

        room = min(MAX_PER_ROUND, MAX_LOOKUPS - len(results))
        if not calls or room <= 0:
            reply = clean_reply(text)
            break

        progress.tools = [name for name, _ in calls]
        progress.looking_up.set()
        new = _run_lookups(calls, ctx, done, room)
        if not new:  # only repeats of earlier look-ups: answer with what we have
            reply = ""
            break
        results += new
        current_system = _with_notes(system, results, final=round_number == MAX_ROUNDS)
    else:
        # Used every look-up round: now write the reply, without tools.
        reply = clean_reply(complete(current_system, history))

    if not reply or is_stalling(reply):
        if results:
            current_system = _with_notes(system, results, final=True)
        log.info("Milo's draft didn't answer (%r); asking it to answer now.", reply[:80])
        reply = clean_reply(complete(f"{current_system}\n\n{ANSWER_NOW}", history))

    if claims_change(reply) and not any(r.changes_plans for r in results):
        reply = _make_claim_true(system, history, ctx, results, done, reply, progress)

    return reply, results


def claims_change(text: str) -> bool:
    return bool(CLAIMS_A_CHANGE.search(text or ""))


def _make_claim_true(system, history, ctx, results, done, draft, progress) -> str:
    """Milo said it changed a plan, but didn't. Give it one chance to actually do it; otherwise make it honest."""
    log.info("Milo claimed a change without making one (%r); checking.", draft[:80])
    base = _with_notes(system, results, final=False) if results else system
    specs = tool_specs()
    try:
        text, calls = complete_or_choose_tools(f"{base}\n\n{CHECK_YOUR_CLAIM}", history, specs)
    except BadRequestError:
        text, calls = "", []
    offered = {t["function"]["name"] for t in specs}
    calls = [c for c in calls if c[0] in offered]
    if calls:
        progress.tools = [name for name, _ in calls]
        progress.looking_up.set()
        results += _run_lookups(calls, ctx, done, MAX_PER_ROUND)
        reply = clean_reply(complete(_with_notes(system, results, final=True), history))
        if reply and not is_stalling(reply):
            return reply
    elif text and not claims_change(text) and not is_stalling(text):
        return clean_reply(text)
    final_system = _with_notes(system, results, final=True) if results else system
    return clean_reply(complete(f"{final_system}\n\n{BE_HONEST}", history))
