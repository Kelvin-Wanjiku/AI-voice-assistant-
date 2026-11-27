"""News headlines from BBC News feeds (free, no key), chosen to match the person's interests.

Topics with a BBC feed are free. Other topics ("farming news") use web search, if it's set up.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from app.tools import web_search
from app.tools.http import LookupFailed, get_text

BBC = "https://feeds.bbci.co.uk"

# topic -> (label shown to the person, feed address, words that point to this topic)
FEEDS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "world": ("World", f"{BBC}/news/world/rss.xml", ("world", "international", "global")),
    "europe": ("Europe", f"{BBC}/news/world/europe/rss.xml", ("europe", "european", "sweden", "eu")),
    "football": ("Football", f"{BBC}/sport/football/rss.xml", ("football", "soccer", "premier league", "champions league")),
    "sport": ("Sport", f"{BBC}/sport/rss.xml", ("sport", "sports")),
    "tennis": ("Tennis", f"{BBC}/sport/tennis/rss.xml", ("tennis", "wimbledon")),
    "cricket": ("Cricket", f"{BBC}/sport/cricket/rss.xml", ("cricket",)),
    "formula 1": ("Formula 1", f"{BBC}/sport/formula1/rss.xml", ("formula 1", "formula one", "f1", "motor racing")),
    "golf": ("Golf", f"{BBC}/sport/golf/rss.xml", ("golf",)),
    "rugby": ("Rugby", f"{BBC}/sport/rugby-union/rss.xml", ("rugby",)),
    "technology": ("Technology", f"{BBC}/news/technology/rss.xml", ("technology", "tech", "computers", "gadgets")),
    "science": ("Science", f"{BBC}/news/science_and_environment/rss.xml", ("science", "nature", "environment", "space", "climate")),
    "health": ("Health", f"{BBC}/news/health/rss.xml", ("health news", "medicine")),
    "business": ("Business", f"{BBC}/news/business/rss.xml", ("business", "economy", "money", "stocks")),
    "arts": ("Arts", f"{BBC}/news/entertainment_and_arts/rss.xml", ("arts", "music", "films", "movies", "theatre", "books", "entertainment", "jazz")),
}


@dataclass
class Headline:
    title: str
    url: str
    summary: str
    topic: str  # the label, e.g. "Football"
    source: str = "BBC News"


def topic_for(text: str) -> str | None:
    """Which feed topic a word or phrase points to, if any. "football" -> "football", "jazz" -> "arts"."""
    t = f" {(text or '').lower()} "
    for key, (_label, _url, words) in FEEDS.items():
        if key in t or any(f" {w} " in t or f" {w}s " in t for w in words):
            return key
    return None


def is_broad(topic: str, key: str) -> bool:
    """True for a general topic like "football" or "football news", false for something specific
    like "Champions League" or "Manchester United", which a web news search handles better."""
    words = {w for w in topic.lower().replace(",", " ").split() if w not in ("news", "latest", "today", "the", "headlines")}
    label_words = set(FEEDS[key][0].lower().split()) | set(key.split()) | {w for kw in FEEDS[key][2] for w in kw.split()}
    return bool(words) and words <= label_words


def interest_topics(memory_texts: list[str], limit: int = 2) -> list[str]:
    """Feed topics that match what Milo remembers the person enjoys, most relevant first."""
    found: list[str] = []
    for text in memory_texts:
        topic = topic_for(text)
        if topic and topic not in found and topic not in ("world",):
            found.append(topic)
    return found[:limit]


def read_feed(topic: str, limit: int = 5) -> list[Headline]:
    label, url, _ = FEEDS[topic]
    xml = get_text(url, "news", max_age=900)  # news is kept for 15 minutes
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise LookupFailed("The news service sent something unexpected.") from exc
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            items.append(Headline(title=title, url=link, summary=(item.findtext("description") or "").strip(), topic=label))
        if len(items) >= limit:
            break
    return items


def headlines_for_home(memory_texts: list[str], limit: int = 4) -> list[Headline]:
    """World news plus the person's interests: e.g. 2 world headlines and 2 football headlines."""
    topics = interest_topics(memory_texts)
    per_topic = max(1, limit // (len(topics) + 1))
    chosen: list[Headline] = []
    seen: set[str] = set()
    for topic in topics + ["world"]:
        try:
            for h in read_feed(topic, limit=per_topic + 2):
                if h.url not in seen and sum(1 for c in chosen if c.topic == h.topic) < per_topic:
                    chosen.append(h)
                    seen.add(h.url)
        except LookupFailed:
            continue
    # fill up with world news if an interest feed had too few
    if len(chosen) < limit:
        try:
            for h in read_feed("world", limit=limit + 4):
                if h.url not in seen and len(chosen) < limit:
                    chosen.append(h)
                    seen.add(h.url)
        except LookupFailed:
            pass
    if not chosen:
        raise LookupFailed("Couldn't load the news right now.")
    return chosen[:limit]


def news_for_milo(topic: str | None, memory_texts: list[str]) -> tuple[str, list[Headline]]:
    """Headlines for Milo to talk about. With no topic: world news plus the person's interests."""
    topic = (topic or "").strip()
    if not topic or topic.lower() in ("news", "headlines", "top", "today", "latest", "general"):
        items = headlines_for_home(memory_texts, limit=6)
        heading = "Today's headlines (world news plus the person's interests):"
    elif (key := topic_for(topic)) is not None and (is_broad(topic, key) or not web_search.is_configured()):
        items = read_feed(key, limit=5)
        heading = f"Latest {FEEDS[key][0]} headlines:"
    elif web_search.is_configured():
        results = web_search.search(f"{topic} news", topic="news", max_results=5)
        items = [Headline(title=r.title, url=r.url, summary=r.snippet, topic=topic.title(), source=r.source) for r in results]
        heading = f"Recent news about {topic}:"
    else:
        items = read_feed("world", limit=5)
        heading = (
            f"There is no news feed for '{topic}' and web search isn't set up, so here are world headlines instead. "
            "Tell the person this briefly:"
        )
    if not items:
        return f"No news found about {topic}.", []
    lines = [heading] + [f"- [{h.topic}] {h.title}" + (f": {h.summary}" if h.summary else "") for h in items]
    return "\n".join(lines), items
