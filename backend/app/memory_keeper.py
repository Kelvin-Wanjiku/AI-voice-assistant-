"""The memory keeper: after each message, decide what Milo should remember, update or forget.

It runs at the same time as Milo's reply (see routes/chat.py), using a second, separate AI request
with its own instructions. It only proposes changes; this file checks them before anything is saved.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app import memory_store as store
from app.llm import complete
from app.schemas import MemoryChanges, MemoryOut

log = logging.getLogger("milo.memory")

MAX_ADD, MAX_UPDATE, MAX_REMOVE = 3, 3, 5
CONTEXT_MESSAGES = 6  # the latest message plus a little of what came before, for context

KEEPER_INSTRUCTIONS = f"""You manage the long-term memory of Milo, a companion app for an older adult.
Read the person's LATEST message (earlier messages are only there for context) and decide whether \
Milo's memory should change. Most messages need no change at all.

Remember lasting things the person says about themselves that will help Milo be a better companion later:
- Life and home: where they live in general terms, their home, farm, pets, work or past work.
- Interests, likes and dislikes. Food they like, dislike or can't eat.
- Routines, such as when they usually walk or eat.
- Family and friends: names and relationships, such as "Daughter Anna visits on Sundays".
- Health details they share about themselves that matter later, such as a condition, an allergy, \
a diet, or a bad back. Never guess or diagnose.
- Goals that last, such as "Wants to be more active".
- Anything they explicitly ask Milo to remember.

Do NOT remember:
- Passing moods or today's state ("I'm bored", "I'm tired today", "my head hurts today"), \
unless they ask Milo to remember it.
- Questions, small talk, or things Milo said.
- Passwords, bank or card numbers, ID numbers, exact addresses or phone numbers.
- Appointments, visits, plans with a date, and reminders: Milo's planner keeps those. \
(Lasting routines without a date, like "usually walks after lunch", are fine to remember.)
- Anything already in the memory list. Update the existing item instead of adding a near-duplicate.

Forget or correct:
- If they ask Milo to forget something, or say something is no longer true \
("I don't like jazz any more", "Anna moved away"), remove or update the matching memory.

Write each memory as one short phrase of at most 15 words, about the person, without their name, \
for example "Has a farm and enjoys working on it".
Use exactly one of these categories: {", ".join(store.CATEGORIES)}.
If the person tells you their name, put it in "name".

Answer with JSON only, no other text, in exactly this shape:
{{"add": [{{"category": "...", "text": "..."}}], "update": [{{"id": "...", "text": "...", "category": "..."}}], \
"remove": ["id"], "name": null}}
When nothing should change, answer: {{"add": [], "update": [], "remove": [], "name": null}}
"""


@dataclass
class Plan:
    """The changes the AI proposed, before they're checked and saved."""

    add: list[dict] = field(default_factory=list)
    update: list[dict] = field(default_factory=list)
    remove: list[str] = field(default_factory=list)
    name: str | None = None


def parse_plan(raw: str) -> Plan:
    """Read the AI's answer. Tolerates ```json fences or extra words around the JSON."""
    text = re.sub(r"```(?:json)?", "", raw or "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return Plan()
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return Plan()
    if not isinstance(data, dict):
        return Plan()

    def dicts(value):
        return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []

    remove = data.get("remove")
    name = data.get("name")
    return Plan(
        add=dicts(data.get("add")),
        update=dicts(data.get("update")),
        remove=[str(x) for x in remove if isinstance(x, (str, int))] if isinstance(remove, list) else [],
        name=name.strip() if isinstance(name, str) and name.strip() else None,
    )


def propose_changes(conversation: list[dict], memories: list[tuple[str, str, str]]) -> Plan:
    """Ask the AI what should change. memories is a list of (id, category, text). Never raises."""
    known = "\n".join(f"- id={mid} [{cat}] {text}" for mid, cat, text in memories) or "(nothing yet)"
    recent = conversation[-CONTEXT_MESSAGES:]
    transcript = "\n".join(f"{'Person' if m['role'] == 'user' else 'Milo'}: {m['content']}" for m in recent)
    prompt = f"Current memory list:\n{known}\n\nConversation (the last 'Person' line is the latest message):\n{transcript}"
    try:
        raw = complete(KEEPER_INSTRUCTIONS, [{"role": "user", "content": prompt}], max_tokens=1024)
    except Exception as exc:  # noqa: BLE001 - a memory failure must never break the chat
        log.warning("Memory keeper couldn't run: %s", exc)
        return Plan()
    return parse_plan(raw)


def apply_plan(db: Session, plan: Plan, memory_enabled: bool) -> MemoryChanges:
    """Check the proposed changes and save the sensible ones. Forgetting always works, even with memory off."""
    changes = MemoryChanges()

    for memory_id in plan.remove[:MAX_REMOVE]:
        removed = store.delete_memory(db, memory_id)
        if removed:
            changes.removed.append(MemoryOut.model_validate(removed))

    if not memory_enabled:
        return changes

    for item in plan.update[:MAX_UPDATE]:
        memory_id = str(item.get("id", ""))
        new_text = store.clean_text(str(item.get("text", "")))
        if not memory_id or not new_text:
            continue
        before = next((m for m in store.list_memories(db) if m.id == memory_id), None)
        if before is None or (before.text == new_text and not item.get("category")):
            continue
        updated = store.update_memory(db, memory_id, text=new_text, category=item.get("category"))
        if updated:
            changes.updated.append(MemoryOut.model_validate(updated))

    for item in plan.add[:MAX_ADD]:
        added = store.add_memory(db, str(item.get("category", "")), str(item.get("text", "")), source="chat")
        if added:
            changes.added.append(MemoryOut.model_validate(added))

    if plan.name:
        name = " ".join(plan.name.split())[:60]
        if name and name != store.get_profile(db).name:
            store.update_profile(db, name=name)
            changes.name = name

    return changes
