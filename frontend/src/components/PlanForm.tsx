// The form for adding or changing a plan on My day.

import { useState, type FormEvent } from "react";
import type { Plan, PlanInput } from "../types";

export const REMINDERS: { label: string; value: number | null }[] = [
  { label: "5 minutes before", value: 5 },
  { label: "10 minutes before", value: 10 },
  { label: "15 minutes before", value: 15 },
  { label: "30 minutes before", value: 30 },
  { label: "1 hour before", value: 60 },
  { label: "At the time", value: 0 },
  { label: "No reminder", value: null },
];

interface Props {
  heading: string;
  saveLabel: string;
  start: Plan | null; // the plan being changed, or null for a new one
  defaultDate: string;
  defaultReminder: number | null; // the person's default, for new plans
  onSave: (plan: PlanInput) => Promise<string | null>; // returns an error message, or null
  onCancel: () => void;
}

export default function PlanForm({ heading, saveLabel, start, defaultDate, defaultReminder, onSave, onCancel }: Props) {
  const [title, setTitle] = useState(start?.title ?? "");
  // For repeating plans, the date field is the first day it happens.
  const [date, setDate] = useState(start ? (start.repeat === "none" ? start.date : start.starts_on) : defaultDate);
  const [time, setTime] = useState(start?.time ?? "");
  const [repeat, setRepeat] = useState<Plan["repeat"]>(start?.repeat ?? "none");
  const [reminder, setReminder] = useState<string>(String(start ? start.remind_before : defaultReminder));
  const [note, setNote] = useState(start?.note ?? "");
  const [place, setPlace] = useState(start?.place ?? "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim() || !date) return;
    setSaving(true);
    const problem = await onSave({
      title: title.trim(),
      date,
      time: time || null,
      note: note.trim() || null,
      place: place.trim() || null,
      repeat,
      remind_before: time ? (reminder === "null" ? null : Number(reminder)) : null,
    });
    setSaving(false);
    if (problem) setError(problem);
  };

  return (
    <form className="panel add-form" onSubmit={onSubmit}>
      <h2 className="panel__title">{heading}</h2>

      <label htmlFor="plan-title">What</label>
      <input id="plan-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="For example, doctor's appointment" maxLength={120} autoFocus />

      <div className="form-pair">
        <div>
          <label htmlFor="plan-date">{repeat === "none" ? "Day" : "Starting on"}</label>
          <input id="plan-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div>
          <label htmlFor="plan-time">Time (optional)</label>
          <input id="plan-time" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
      </div>

      <div className="form-pair">
        <div>
          <label htmlFor="plan-repeat">How often</label>
          <select id="plan-repeat" value={repeat} onChange={(e) => setRepeat(e.target.value as Plan["repeat"])}>
            <option value="none">Just once</option>
            <option value="daily">Every day</option>
            <option value="weekly">Every week</option>
          </select>
        </div>
        <div>
          <label htmlFor="plan-reminder">Reminder</label>
          <select id="plan-reminder" value={time ? reminder : "null"} onChange={(e) => setReminder(e.target.value)} disabled={!time}>
            {REMINDERS.map((r) => (
              <option key={r.label} value={String(r.value)}>{r.label}</option>
            ))}
            {!REMINDERS.some((r) => String(r.value) === reminder) && reminder !== "null" && (
              <option value={reminder}>{reminder} minutes before</option>
            )}
          </select>
          {!time && <p className="form-hint">No time? Milo will remind you in the morning.</p>}
        </div>
      </div>

      <label htmlFor="plan-place">Where (optional)</label>
      <input id="plan-place" value={place} onChange={(e) => setPlace(e.target.value)} placeholder="For example, the health centre" maxLength={120} />

      <label htmlFor="plan-note">Note (optional)</label>
      <input id="plan-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example, bring the letter" maxLength={200} />

      {error && <p className="form-message form-message--bad" role="alert">{error}</p>}
      <div className="add-form__buttons">
        <button type="submit" className="button" disabled={saving || !title.trim() || !date}>{saving ? "Saving…" : saveLabel}</button>
        <button type="button" className="button button--quiet" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
