"""What Milo says while it's busy looking something up, so the person isn't left in silence."""

import random

# One casual line per kind of look-up. Several options, so Milo doesn't sound like a machine.
LINES = {
    "get_weather": ["Let me just check the weather for you.", "One moment, I'll have a look at the weather."],
    "get_news": ["Let me see what's in the news.", "Give me a second, I'll see what's happening."],
    "find_recipe": ["Let me find a good recipe for that.", "One moment, I'll find you a recipe."],
    "see_plans": ["Let me look at your plans.", "One moment, I'll check your diary."],
    "add_plan": ["Let me put that in your diary.", "One moment, I'll write that down."],
    "change_plan": ["Let me change that for you.", "One moment, I'll sort that out."],
    "remove_plan": ["Let me take that off for you.", "One moment."],
    "mark_done": ["Let me tick that off.", "One moment."],
    "set_default_reminder": ["Let me change that for you.", "One moment, I'll sort that out."],
    "web_search": ["Let me find that out for you.", "Good question, let me look that up.", "Give me a second, I'll find out."],
}
SEVERAL = ["Give me a second, I'll find out.", "Let me look into that for you."]
GENERAL = ["Just a moment.", "Let me think about that."]
STILL_WORKING = ["Still looking, it won't be long.", "Nearly there, thanks for waiting."]


def holding_line(tools: list[str]) -> str:
    kinds = list(dict.fromkeys(tools))
    if len(kinds) == 1 and kinds[0] in LINES:
        return random.choice(LINES[kinds[0]])
    return random.choice(SEVERAL if kinds else GENERAL)


def still_working_line() -> str:
    return random.choice(STILL_WORKING)
