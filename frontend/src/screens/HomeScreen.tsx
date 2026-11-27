import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchNews, fetchUpcoming, fetchWeather } from "../api";
import { MicIcon } from "../components/Icons";
import { useMilo } from "../data/MiloDataContext";
import type { Headline, Plan, Weather } from "../types";
import { dayLabel, displayTime, greeting, longDate } from "../utils/time";

type Load<T> = { state: "loading" } | { state: "ready"; data: T } | { state: "error"; message: string };

export default function HomeScreen() {
  const { profile, memories, plansVersion } = useMilo();
  const [coming, setComing] = useState<Load<Plan[]>>({ state: "loading" });
  const [weather, setWeather] = useState<Load<Weather>>({ state: "loading" });
  const [news, setNews] = useState<Load<Headline[]>>({ state: "loading" });

  // Fetch the weather again whenever the town changes.
  useEffect(() => {
    if (!profile.town) {
      setWeather({ state: "error", message: "" });
      return;
    }
    let cancelled = false;
    setWeather({ state: "loading" });
    fetchWeather()
      .then((data) => !cancelled && setWeather({ state: "ready", data }))
      .catch((err: Error) => !cancelled && setWeather({ state: "error", message: err.message }));
    return () => {
      cancelled = true;
    };
  }, [profile.town]);

  // Headlines follow what Milo remembers you enjoy, so fetch again when memories change.
  const memoryKey = memories.map((m) => m.text).join("|");
  useEffect(() => {
    let cancelled = false;
    fetchNews(4)
      .then((data) => !cancelled && setNews({ state: "ready", data }))
      .catch((err: Error) => !cancelled && setNews({ state: "error", message: err.message }));
    return () => {
      cancelled = true;
    };
  }, [memoryKey]);

  // What's next: today's and tomorrow's plans that haven't passed or been done.
  useEffect(() => {
    let cancelled = false;
    fetchUpcoming(2)
      .then((data) => !cancelled && setComing({ state: "ready", data }))
      .catch((err: Error) => !cancelled && setComing({ state: "error", message: err.message }));
    return () => {
      cancelled = true;
    };
  }, [plansVersion]);

  return (
    <>
      <h1 className="screen__title" tabIndex={-1}>
        {greeting()}
        {profile.name ? `, ${profile.name}` : ""}.
      </h1>
      <p className="screen__lead">{longDate()}</p>

      {/* The main action. In Phase 7 this button starts listening straight away. */}
      <Link to="/chat" className="talk">
        <span className="talk__circle">
          <MicIcon size={44} />
        </span>
        <span className="talk__label">Talk to Milo</span>
      </Link>

      <section className="panel" aria-labelledby="weather-heading" aria-live="polite">
        <h2 id="weather-heading" className="panel__title">
          {weather.state === "ready" ? `Weather in ${weather.data.place}` : "Weather"}
        </h2>
        {!profile.town ? (
          <p>
            <Link to="/about-me" className="text-link">Add your town</Link> to see the weather here.
          </p>
        ) : weather.state === "loading" ? (
          <p>Checking the weather…</p>
        ) : weather.state === "error" ? (
          <p className="form-message--bad">{weather.message}</p>
        ) : (
          <>
            <p className="panel__big">
              {weather.data.temperature}°, {weather.data.description}
            </p>
            <p>
              Today {weather.data.low}° to {weather.data.high}°
              {weather.data.rain_chance !== null ? `, ${weather.data.rain_chance}% chance of rain` : ""}.
            </p>
          </>
        )}
      </section>

      <section className="panel" aria-labelledby="next-heading">
        <h2 id="next-heading" className="panel__title">Coming up</h2>
        {coming.state === "loading" ? (
          <p>Loading your plans…</p>
        ) : coming.state === "error" ? (
          <p className="form-message--bad">{coming.message}</p>
        ) : coming.data.length === 0 ? (
          <p className="panel__big">Nothing planned for today or tomorrow.</p>
        ) : (
          <ul className="coming">
            {coming.data.slice(0, 3).map((p) => (
              <li key={`${p.id}-${p.date}`}>
                <span className="coming__when">
                  {dayLabel(p.date)}
                  {p.time ? `, ${displayTime(p.time)}` : ""}
                </span>
                <span className="coming__what">{p.title}</span>
              </li>
            ))}
          </ul>
        )}
        <Link to="/my-day" className="text-link">See my day</Link>
      </section>

      <section className="panel" aria-labelledby="news-heading">
        <h2 id="news-heading" className="panel__title">In the news</h2>
        {news.state === "loading" ? (
          <p>Loading headlines…</p>
        ) : news.state === "error" ? (
          <p className="form-message--bad">{news.message}</p>
        ) : (
          <ul className="headlines">
            {news.data.map((h) => (
              <li key={h.url}>
                <span className="headline__topic">{h.topic}</span>
                <a href={h.url} target="_blank" rel="noreferrer" className="headline__link">
                  {h.title}
                </a>
              </li>
            ))}
          </ul>
        )}
        <Link to="/chat" className="text-link">Ask Milo about the news</Link>
      </section>
    </>
  );
}
