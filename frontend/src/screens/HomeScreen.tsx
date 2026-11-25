import { Link } from "react-router-dom";
import { MicIcon } from "../components/Icons";
import { useMilo } from "../data/MiloDataContext";
import { sampleSuggestion, sampleWeather } from "../data/sampleData";
import { displayTime, greeting, longDate, nowHHMM } from "../utils/time";

export default function HomeScreen() {
  const { profile, plans } = useMilo();

  // The next thing on today's plan that isn't done and hasn't passed yet.
  const now = nowHHMM();
  const upcoming = [...plans]
    .filter((p) => !p.done && p.time >= now)
    .sort((a, b) => a.time.localeCompare(b.time))[0];

  return (
    <>
      <h1 className="screen__title" tabIndex={-1}>
        {greeting()}, {profile.name}.
      </h1>
      <p className="screen__lead">{longDate()}</p>

      {/* The main action. In Phase 7 this button starts listening straight away. */}
      <Link to="/chat" className="talk">
        <span className="talk__circle">
          <MicIcon size={44} />
        </span>
        <span className="talk__label">Talk to Milo</span>
      </Link>

      <section className="panel" aria-labelledby="next-heading">
        <h2 id="next-heading" className="panel__title">Coming up</h2>
        {upcoming ? (
          <p className="panel__big">
            <span className="time">{displayTime(upcoming.time)}</span> {upcoming.title}
          </p>
        ) : (
          <p className="panel__big">Nothing else planned today.</p>
        )}
        <Link to="/my-day" className="text-link">See my whole day</Link>
      </section>

      <section className="panel" aria-labelledby="weather-heading">
        <h2 id="weather-heading" className="panel__title">
          Weather <span className="sample">sample</span>
        </h2>
        <p className="panel__big">
          {sampleWeather.temperature}°, {sampleWeather.summary.toLowerCase()}
        </p>
      </section>

      <section className="panel panel--idea" aria-labelledby="idea-heading">
        <h2 id="idea-heading" className="panel__title">An idea for today</h2>
        <p>{sampleSuggestion}</p>
      </section>
    </>
  );
}
