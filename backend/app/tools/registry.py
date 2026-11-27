"""The list of tools Milo may use, and the code that runs them.

The AI sees each tool's name, a description and what to fill in. It decides whether a message needs one
(for example "Should I go for a walk?" -> get_weather). This file then runs the tool and returns plain text
for Milo to read, plus links to show the person where the information came from.
"""

import json
import logging
from dataclasses import dataclass, field

from app.planner import PlanProblem
from app.tools import diary, news, recipes, weather, web_search
from app.tools.http import LookupFailed

log = logging.getLogger("milo.tools")

@dataclass
class Context:
    """What the tools may need to know about the person."""

    town: str = ""
    latitude: float | None = None
    longitude: float | None = None
    memory_texts: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    label: str  # shown in the chat, e.g. "Checked the weather for Uppsala, Sweden"
    text: str  # what Milo reads
    sources: list[tuple[str, str]] = field(default_factory=list)  # (title, url)
    failed: bool = False
    changes_plans: bool = False  # the person's plans were changed, so My day should refresh


def _fn(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []},
        },
    }


def tool_specs(leave_out: set[str] | None = None) -> list[dict]:
    """The tools Milo may use. leave_out: tool names not to offer this time."""
    return [t for t in _all_specs() if t["function"]["name"] not in (leave_out or set())]


def _all_specs() -> list[dict]:
    specs = [
        _fn(
            "get_weather",
            "Current weather and forecast for the next three days. Use it whenever the weather matters: "
            "the person asks about it, or plans to go out, walk, work outside, garden or travel.",
            {"place": {"type": "string", "description": "A town, only if they ask about somewhere other than home. Leave empty for their home town."}},
        ),
        _fn(
            "get_news",
            "Today's news headlines. Use when the person asks about the news, or what's happening in a subject they follow.",
            {"topic": {"type": "string", "description": "A subject such as 'football', 'technology' or 'farming'. Leave empty for world news plus the person's interests."}},
        ),
        _fn(
            "find_recipe",
            "Find a recipe with ingredients and method. Use when the person wants to cook something, or asks what to make with an ingredient.",
            {"query": {"type": "string", "description": "A dish ('pancakes') or a main ingredient ('potatoes')."}},
            ["query"],
        ),
    ]
    specs += diary_specs()
    if web_search.is_configured():
        specs.append(
            _fn(
                "web_search",
                "Search the web for current or local facts you don't know: opening times, events, prices, recent facts. "
                "Don't use it for weather, news headlines or recipes.",
                {"query": {"type": "string", "description": "A short search, e.g. 'Uppsala farmers market opening times'."}},
                ["query"],
            )
        )
    return specs


DATE_HELP = "The day: 'YYYY-MM-DD' (preferred), or 'today', 'tomorrow', or a weekday like 'thursday'."
DIARY_TOOLS = {"see_plans", "add_plan", "change_plan", "remove_plan", "mark_done", "set_default_reminder"}
DIARY_CHANGES = DIARY_TOOLS - {"see_plans"}


def diary_specs() -> list[dict]:
    return [
        _fn(
            "see_plans",
            "See the person's plans for a day or several days. Today's and tomorrow's are already in your instructions; "
            "use this for other days.",
            {"day": {"type": "string", "description": DATE_HELP}, "days": {"type": "integer", "description": "How many days from that day, 1 to 14."}},
        ),
        _fn(
            "add_plan",
            "Put something on the person's plans: an appointment, a visit, an activity, an event or a routine. "
            "For a public event (a match, concert, show, market), look up its date, time and place first. "
            "For a personal plan, ask for a missing day, time or place when it matters; if they don't know, add it without. "
            "If a similar plan is already on that day, its missing details are filled in instead of adding a second one.",
            {
                "title": {"type": "string", "description": "Short name, e.g. 'Doctor' or 'Anna visits'."},
                "date": {"type": "string", "description": DATE_HELP + " For repeating plans, the first day."},
                "time": {"type": "string", "description": "24-hour 'HH:MM' in the person's LOCAL time. If the time came from a "
                         "website or the news, convert it to their time zone first. Leave empty if there's no time."},
                "duration_minutes": {"type": "integer", "description": "Only if they said how long."},
                "place": {"type": "string", "description": "Where, if known: a venue, address or simply 'Anna's house'."},
                "note": {"type": "string", "description": "A useful detail, e.g. 'bring the blood test results'."},
                "repeat": {"type": "string", "enum": ["none", "daily", "weekly"], "description": "'daily' or 'weekly' only if they said it repeats."},
                "remind_before": {"type": "integer", "description": "Only if they asked for a particular reminder: minutes before, 0 = at the time. "
                                  "Leave out to use their default reminder."},
            },
            ["title", "date"],
        ),
        _fn(
            "change_plan",
            "Change a plan: move it, rename it, change the reminder. Only include what changes.",
            {
                "plan_id": {"type": "string", "description": "The id from the plans list."},
                "title": {"type": "string"},
                "date": {"type": "string", "description": DATE_HELP},
                "time": {"type": "string", "description": "24-hour 'HH:MM' in the person's LOCAL time, or empty to make it 'any time'."},
                "duration_minutes": {"type": "integer"},
                "place": {"type": "string"},
                "note": {"type": "string"},
                "repeat": {"type": "string", "enum": ["none", "daily", "weekly"]},
                "remind_before": {"type": "integer", "description": "This plan's reminder: minutes before, 0 = at the time."},
            },
            ["plan_id"],
        ),
        _fn(
            "set_default_reminder",
            "Change how long before their plans the person is reminded, in general (e.g. 'reminders should be 10 minutes before'). "
            "Also updates their existing plans that use the old default, unless they say only new plans.",
            {
                "minutes_before": {"type": "integer", "description": "Minutes before. 0 = at the time. -1 = no reminders."},
                "update_existing": {"type": "boolean", "description": "Also change existing plans (default true)."},
            },
            ["minutes_before"],
        ),
        _fn(
            "remove_plan",
            "Remove a plan. Only when the person clearly wants it removed or cancelled.",
            {"plan_id": {"type": "string", "description": "The id from the plans list."}},
            ["plan_id"],
        ),
        _fn(
            "mark_done",
            "Tick off a plan when the person says they've done it (for repeating plans, just for that day).",
            {"plan_id": {"type": "string"}, "date": {"type": "string", "description": DATE_HELP + " Default today."}},
            ["plan_id"],
        ),
    ]


def run_diary(name: str, args: dict) -> ToolResult:
    action = {
        "see_plans": diary.see_plans, "add_plan": diary.add, "change_plan": diary.change,
        "remove_plan": diary.remove, "mark_done": diary.mark_done, "set_default_reminder": diary.set_default_reminder,
    }[name]
    label, text = action(args)
    return ToolResult(label, text, changes_plans=name != "see_plans")


def parse_arguments(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def run_tool(name: str, args: dict, ctx: Context) -> ToolResult:
    """Run one tool. Never raises: problems become a short note Milo can pass on honestly."""
    try:
        if name in DIARY_TOOLS:
            return run_diary(name, args)

        if name == "get_weather":
            requested = str(args.get("place") or "").strip()
            if requested:
                place = weather.find_place(requested)
            elif ctx.town and ctx.latitude is not None and ctx.longitude is not None:
                place = weather.Place(ctx.town, ctx.latitude, ctx.longitude, "auto")
            else:
                return ToolResult(
                    "Couldn't check the weather",
                    "The person hasn't told Milo their town yet. Ask which town they're in, "
                    "and mention they can save it on the About me screen.",
                    failed=True,
                )
            return ToolResult(f"Checked the weather for {place.name}", weather.summary_for_milo(place),
                              [("Open-Meteo forecast", "https://open-meteo.com")])

        if name == "get_news":
            topic = str(args.get("topic") or "").strip()
            text, items = news.news_for_milo(topic, ctx.memory_texts)
            label = f"Checked the news about {topic}" if topic else "Checked today's news"
            return ToolResult(label, text, [(f"{h.source}: {h.title}", h.url) for h in items[:5]])

        if name == "find_recipe":
            query = str(args.get("query") or "").strip()
            text, found = recipes.recipes_for_milo(query)
            return ToolResult(f"Looked up a recipe for {query}", text, [(f"Recipe: {r.name}", r.url) for r in found])

        if name == "web_search":
            if not web_search.is_configured():
                return ToolResult("Couldn't search the web", "Web search isn't set up.", failed=True)
            query = str(args.get("query") or "").strip()
            text, results = web_search.results_for_milo(query)
            return ToolResult(f"Searched the web for \"{query}\"", text, [(f"{r.source}: {r.title}", r.url) for r in results[:4]])

        return ToolResult("Unknown tool", f"There is no tool called {name}.", failed=True)

    except PlanProblem as exc:
        return ToolResult(_failed_label(name), f"That didn't work: {exc} Tell the person, or ask them to clarify.", failed=True)
    except LookupFailed as exc:
        return ToolResult(_failed_label(name), f"The lookup didn't work: {exc} Tell the person briefly.", failed=True)
    except Exception:  # noqa: BLE001 - a broken tool must never break the chat
        log.exception("Tool %s failed", name)
        return ToolResult(_failed_label(name), "The lookup didn't work because of an unexpected problem. Tell the person briefly.", failed=True)


def _failed_label(name: str) -> str:
    return {
        "get_weather": "Couldn't check the weather",
        "get_news": "Couldn't load the news",
        "find_recipe": "Couldn't look up recipes",
        "web_search": "Couldn't search the web",
        "see_plans": "Couldn't look at the plans",
        "add_plan": "Couldn't add the plan",
        "change_plan": "Couldn't change the plan",
        "remove_plan": "Couldn't remove the plan",
        "mark_done": "Couldn't tick off the plan",
        "set_default_reminder": "Couldn't change the reminder setting",
    }.get(name, "A look-up didn't work")
