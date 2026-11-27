"""Weather from Open-Meteo (https://open-meteo.com): free, no key needed."""

from dataclasses import dataclass
from datetime import datetime

from app.tools.http import LookupFailed, get_json

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# What the weather codes mean (WMO codes, as used by Open-Meteo).
CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "heavy showers", 85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}


def describe(code) -> str:
    try:
        return CODES.get(int(code), "mixed weather")
    except (TypeError, ValueError):
        return "mixed weather"


@dataclass
class Place:
    name: str  # e.g. "Uppsala, Sweden"
    latitude: float
    longitude: float
    timezone: str


def find_place(query: str) -> Place:
    """Turn "Uppsala" or "Uppsala, Sweden" into a place with coordinates. Raises LookupFailed if not found."""
    query = " ".join((query or "").split())
    if not query:
        raise LookupFailed("No town given.")
    town, _, hint = query.partition(",")
    town, hint = town.strip(), hint.strip().lower()

    data = get_json(GEOCODE_URL, "weather", {"name": town, "count": 10, "language": "en", "format": "json"}, max_age=86400)
    results = data.get("results") or []
    if hint:  # "Uppsala, Sweden": prefer results in that country or region
        results = [
            r for r in results
            if hint in str(r.get("country", "")).lower()
            or hint in str(r.get("admin1", "")).lower()
            or hint == str(r.get("country_code", "")).lower()
        ] or results
    if not results:
        raise LookupFailed(f"Couldn't find a place called \"{query}\". Try adding the country, like \"{town}, Sweden\".")

    r = results[0]
    name = ", ".join(part for part in (r.get("name"), r.get("country")) if part)
    return Place(name=name, latitude=float(r["latitude"]), longitude=float(r["longitude"]), timezone=r.get("timezone") or "auto")


def get_forecast(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": round(latitude, 3),
        "longitude": round(longitude, 3),
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "timezone": "auto",
        "forecast_days": 3,
    }
    data = get_json(FORECAST_URL, "weather", params, max_age=600)  # weather is kept for 10 minutes
    if "current" not in data or "daily" not in data:
        raise LookupFailed("The weather service sent something unexpected.")
    return data


def _hour(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M")
    except ValueError:
        return iso


def _day(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%A")
    except ValueError:
        return iso


def summary_for_home(place: Place) -> dict:
    """A small summary for the Home screen."""
    data = get_forecast(place.latitude, place.longitude)
    cur, daily = data["current"], data["daily"]
    return {
        "place": place.name,
        "temperature": round(cur.get("temperature_2m", 0)),
        "description": describe(cur.get("weather_code")),
        "high": round(daily["temperature_2m_max"][0]),
        "low": round(daily["temperature_2m_min"][0]),
        "rain_chance": daily.get("precipitation_probability_max", [None])[0],
    }


def summary_for_milo(place: Place) -> str:
    """A plain-text forecast for Milo to read: now, the next 12 hours, and the next three days."""
    data = get_forecast(place.latitude, place.longitude)
    cur, hourly, daily = data["current"], data.get("hourly", {}), data["daily"]
    lines = [
        f"Weather for {place.name} (local time now {_hour(cur.get('time', ''))}):",
        f"Now: {round(cur.get('temperature_2m', 0))}°C (feels like {round(cur.get('apparent_temperature', cur.get('temperature_2m', 0)))}°C), "
        f"{describe(cur.get('weather_code'))}, wind {round(cur.get('wind_speed_10m', 0))} km/h.",
    ]

    times = hourly.get("time", [])
    now_time = cur.get("time", "")
    start = next((i for i, t in enumerate(times) if t >= now_time[:13]), 0)
    steps = []
    for i in range(start, min(start + 13, len(times)), 3):
        rain = (hourly.get("precipitation_probability") or [None] * len(times))[i]
        steps.append(
            f"{_hour(times[i])} {round(hourly['temperature_2m'][i])}°C {describe(hourly['weather_code'][i])}"
            + (f", {rain}% chance of rain" if rain is not None else "")
        )
    if steps:
        lines.append("Next hours: " + "; ".join(steps) + ".")

    for i, day in enumerate(daily.get("time", [])[:3]):
        label = "Today" if i == 0 else "Tomorrow" if i == 1 else _day(day)
        rain = daily.get("precipitation_probability_max", [None] * 3)[i]
        lines.append(
            f"{label}: {describe(daily['weather_code'][i])}, {round(daily['temperature_2m_min'][i])} to "
            f"{round(daily['temperature_2m_max'][i])}°C"
            + (f", up to {rain}% chance of rain" if rain is not None else "")
            + (f", sunset {_hour(daily['sunset'][i])}" if i == 0 and daily.get("sunset") else "")
            + "."
        )
    return "\n".join(lines)
