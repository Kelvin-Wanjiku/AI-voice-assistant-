// The reminder pop-up. It checks every 30 seconds whether anything is due, on every screen.
// Two kinds:
//   - a plan with a time, shortly before it starts ("Doctor at 10:00, in 10 minutes")
//   - in the morning, the day's plans that have no time yet, with a button to ask Milo for a good time
// In Phase 7 Milo will also say reminders out loud.

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api";
import { useMilo } from "../data/MiloDataContext";
import type { Reminder } from "../types";
import { displayTime } from "../utils/time";

const CHECK_EVERY_MS = 30_000;

function whenText(r: Reminder): string {
  if (r.minutes_until > 1) return `in ${r.minutes_until} minutes`;
  if (r.minutes_until === 1) return "in 1 minute";
  if (r.minutes_until >= -1) return "now";
  return `started ${-r.minutes_until} minutes ago`;
}

function listText(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

const keyOf = (r: Reminder) => `${r.plan_id}|${r.date}|${r.time ?? "morning"}`;

/** A soft two-note chime, made in the browser (no sound file needed). */
function chime() {
  try {
    const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new AudioCtx();
    [660, 880].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      osc.type = "sine";
      const start = ctx.currentTime + i * 0.35;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.25, start + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.6);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.65);
    });
    setTimeout(() => void ctx.close(), 1500);
  } catch {
    // Some browsers block sound until the page has been clicked; the reminder still shows.
  }
}

export default function ReminderBanner() {
  const { plansVersion, plansChanged, sendMessage } = useMilo();
  const navigate = useNavigate();
  const [due, setDue] = useState<Reminder[]>([]);
  const [busy, setBusy] = useState(false);
  const chimed = useRef(new Set<string>());

  const check = useCallback(async () => {
    try {
      const found = await api.fetchReminders();
      setDue(found);
      const fresh = found.filter((r) => !chimed.current.has(keyOf(r)));
      if (fresh.length) {
        fresh.forEach((r) => chimed.current.add(keyOf(r)));
        chime();
      }
    } catch {
      // Backend not running: nothing to show. The other screens explain that.
    }
  }, []);

  useEffect(() => {
    void check();
    const timer = window.setInterval(() => void check(), CHECK_EVERY_MS);
    const onFocus = () => void check();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
    };
  }, [check, plansVersion]);

  // Timed reminders come first; the morning ones are shown together in one card.
  const timed = due.filter((r) => r.kind === "timed");
  const morning = due.filter((r) => r.kind === "morning");
  const showing: Reminder[] = timed.length ? [timed[0]] : morning;
  if (!showing.length) return null;

  const answer = async (action: "ok" | "snooze" | "done", minutes = 10) => {
    setBusy(true);
    try {
      await Promise.all(showing.map((r) => api.answerReminder(r, action, minutes)));
      if (action === "snooze") showing.forEach((r) => chimed.current.delete(keyOf(r)));
      if (action === "done") plansChanged();
      await check();
    } finally {
      setBusy(false);
    }
  };

  const askForATime = async () => {
    const titles = showing.map((r) => r.title);
    await answer("ok");
    navigate("/chat");
    sendMessage(`When would be a good time today for ${listText(titles)}?`);
  };

  if (showing[0].kind === "morning") {
    return (
      <div className="reminder" role="alertdialog" aria-labelledby="reminder-title" aria-describedby="reminder-when">
        <p className="reminder__label">Today</p>
        <p id="reminder-title" className="reminder__title">{listText(showing.map((r) => r.title))}</p>
        <p id="reminder-when" className="reminder__when">
          {showing.length === 1 ? "There's no time set for this yet." : "There's no time set for these yet."}
        </p>
        <div className="reminder__buttons">
          <button className="button" onClick={askForATime} disabled={busy}>Ask Milo for a good time</button>
          <button className="button button--quiet" onClick={() => answer("ok")} disabled={busy}>OK</button>
          <button className="button button--quiet" onClick={() => answer("snooze", 60)} disabled={busy}>Remind me in an hour</button>
        </div>
      </div>
    );
  }

  const r = showing[0];
  return (
    <div className="reminder" role="alertdialog" aria-labelledby="reminder-title" aria-describedby="reminder-when">
      <p className="reminder__label">Reminder</p>
      <p id="reminder-title" className="reminder__title">
        {r.title} at {displayTime(r.time!)}
      </p>
      <p id="reminder-when" className="reminder__when">
        {whenText(r)}
        {r.place ? `, at ${r.place}` : ""}
      </p>
      <div className="reminder__buttons">
        <button className="button" onClick={() => answer("ok")} disabled={busy}>OK</button>
        <button className="button button--quiet" onClick={() => answer("snooze")} disabled={busy}>Remind me in 10 minutes</button>
        <button className="button button--quiet" onClick={() => answer("done")} disabled={busy}>Done</button>
      </div>
      {due.length > 1 && <p className="reminder__more">{due.length - 1} more after this</p>}
    </div>
  );
}
