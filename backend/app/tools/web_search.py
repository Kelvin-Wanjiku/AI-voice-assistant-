"""Web search through Tavily (https://tavily.com). Needs a free key in backend/.env as TAVILY_API_KEY."""

from dataclasses import dataclass
from urllib.parse import urlparse

from app.config import get_settings
from app.tools.http import post_json

SEARCH_URL = "https://api.tavily.com/search"


@dataclass
class Result:
    title: str
    url: str
    snippet: str
    source: str  # the website, e.g. "visitsweden.com"


def is_configured() -> bool:
    return bool(get_settings().tavily_api_key.strip())


def search(query: str, topic: str = "general", max_results: int = 5) -> list[Result]:
    return search_with_answer(query, topic, max_results, with_answer=False)[1]


def search_with_answer(query: str, topic: str = "general", max_results: int = 5, with_answer: bool = True) -> tuple[str, list[Result]]:
    """Returns (a short direct answer, if asked for and found; the results)."""
    body = {
        "query": query[:300],
        "topic": topic,  # "general" or "news"
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": "basic" if with_answer else False,  # a one-paragraph answer, written by Tavily
        "include_raw_content": False,
    }
    if topic == "news":
        body["time_range"] = "week"
    headers = {"Authorization": f"Bearer {get_settings().tavily_api_key.strip()}"}
    data = post_json(SEARCH_URL, "web search", body, headers)
    results = []
    for r in (data.get("results") or [])[:max_results]:
        url = str(r.get("url") or "")
        if not url:
            continue
        results.append(
            Result(
                title=str(r.get("title") or url)[:200],
                url=url,
                snippet=" ".join(str(r.get("content") or "").split())[:500],
                source=urlparse(url).netloc.removeprefix("www."),
            )
        )
    answer = " ".join(str(data.get("answer") or "").split())[:600]
    return answer, results


def results_for_milo(query: str) -> tuple[str, list[Result]]:
    answer, results = search_with_answer(query)
    if not results and not answer:
        return f"The web search for '{query}' found nothing useful.", []
    lines = [f"Web search results for '{query}':"]
    if answer:
        lines.append(f"Short answer from the search (check it against the results): {answer}")
    lines += [f"- {r.title} ({r.source}): {r.snippet}" for r in results]
    lines.append("Times on websites may be in another country's time zone. Convert them to the person's time "
                 "when the source says which zone; if it doesn't, say you're not completely sure.")
    return "\n".join(lines), results
