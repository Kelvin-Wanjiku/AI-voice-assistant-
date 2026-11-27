import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api";
import PlanForm from "../components/PlanForm";
import { useMilo } from "../data/MiloDataContext";
import type { Plan, PlanInput } from "../types";
import { addDays, dayLabel, displayTime, isoDate, longDate, fromIso, reminderLabel, repeatLabel } from "../utils/time";

type Editing = { kind: "new" } | { kind: "change"; plan: Plan } | null;

function clashText(clashes: Plan[]): string {
  return clashes.map((c) => `${c.title}${c.time ? ` at ${displayTime(c.time)}` : ""}`).join(" and ");
}

export default function MyDayScreen() {
  const { plansVersion, plansChanged, profile } = useMilo();
  const [day, setDay] = useState(isoDate());
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Editing>(null);
  const [message, setMessage] = useState("");
  const [removed, setRemoved] = useState<Plan | null>(null);

  const load = useCallback(async () => {
    try {
      setPlans(await api.fetchPlans(day));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load your plans.");
    }
  }, [day]);

  // Load the day's plans, and again whenever plans change anywhere (for example, Milo added one in the chat).
  useEffect(() => {
    void load();
  }, [load, plansVersion]);

  const goTo = (iso: string) => {
    setDay(iso);
    setPlans(null);
    setEditing(null);
    setMessage("");
    setRemoved(null);
  };

  const afterSave = (saved: api.PlanSaved, verb: string) => {
    const when = saved.plan.repeat === "none" ? ` for ${dayLabel(saved.plan.date).toLowerCase()}` : "";
    const main = saved.merged
      ? `“${saved.plan.title}” was already on your plans, so it's been updated instead of added twice.`
      : `${verb} “${saved.plan.title}”${when}.`;
    setMessage(main + (saved.clashes.length ? ` Note: it overlaps with ${clashText(saved.clashes)}.` : ""));
    setEditing(null);
    plansChanged();
  };

  const onAdd = async (input: PlanInput) => {
    try {
      afterSave(await api.createPlan(input), "Added");
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : "Couldn't save that.";
    }
  };

  const onChange = (plan: Plan) => async (input: PlanInput) => {
    try {
      afterSave(await api.updatePlan(plan.id, input), "Changed");
      return null;
    } catch (err) {
      return err instanceof Error ? err.message : "Couldn't save that.";
    }
  };

  const onToggle = async (plan: Plan) => {
    const flip = (done: boolean) => setPlans((all) => all?.map((p) => (p.id === plan.id ? { ...p, done } : p)) ?? all);
    flip(!plan.done); // tick straight away…
    try {
      await api.setPlanDone(plan.id, plan.date, !plan.done);
      plansChanged();
    } catch (err) {
      flip(plan.done); // …and untick if it couldn't be saved
      setError(err instanceof Error ? err.message : "Couldn't save that.");
    }
  };

  const onRemove = async (plan: Plan) => {
    try {
      await api.deletePlan(plan.id);
      setPlans((all) => all?.filter((p) => p.id !== plan.id) ?? all); // gone straight away
      setRemoved(plan);
      setMessage("");
      plansChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't remove that.");
    }
  };

  const onUndo = async () => {
    if (!removed) return;
    try {
      await api.createPlan({
        title: removed.title,
        date: removed.repeat === "none" ? removed.date : removed.starts_on,
        time: removed.time,
        note: removed.note,
        place: removed.place,
        repeat: removed.repeat,
        remind_before: removed.remind_before,
      });
      setRemoved(null);
      plansChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't put that back.");
    }
  };

  const today = isoDate();
  const isPast = day < today;

  return (
    <>
      <h1 className="screen__title" tabIndex={-1}>My day</h1>

      <nav className="day-nav" aria-label="Choose a day">
        <button className="button button--quiet" onClick={() => goTo(addDays(day, -1))}>‹ Day before</button>
        {day !== today && <button className="button button--quiet" onClick={() => goTo(today)}>Today</button>}
        <button className="button button--quiet" onClick={() => goTo(addDays(day, 1))}>Day after ›</button>
      </nav>
      <p className="day-heading" aria-live="polite">
        <strong>{dayLabel(day)}</strong>
        {dayLabel(day) !== longDate(fromIso(day)) && <span> · {longDate(fromIso(day))}</span>}
      </p>

      {message && <p className="undo" role="status">{message}</p>}
      {removed && (
        <div className="undo" role="status">
          <p>Removed “{removed.title}”.</p>
          <button className="button button--quiet" onClick={onUndo}>Undo</button>
        </div>
      )}
      {error && (
        <div className="chat-error" role="alert">
          <p>{error}</p>
          <button className="button button--quiet" onClick={() => void load()}>Try again</button>
        </div>
      )}

      {plans === null && !error ? (
        <p className="panel">Loading…</p>
      ) : plans && plans.length === 0 ? (
        <p className="panel">
          Nothing planned{day === today ? " today" : ""}. Add something below, or just <Link to="/chat" className="text-link">tell Milo</Link>.
        </p>
      ) : (
        plans && (
          <ol className="plan">
            {plans.map((p) =>
              editing?.kind === "change" && editing.plan.id === p.id ? (
                <li key={p.id} className="plan__editing">
                  <PlanForm heading="Change this plan" saveLabel="Save changes" start={p} defaultDate={day} defaultReminder={profile.defaultReminder} onSave={onChange(p)} onCancel={() => setEditing(null)} />
                </li>
              ) : (
                <li key={p.id} className={`plan__item ${p.done ? "plan__item--done" : ""}`}>
                  <span className="plan__time">{p.time ? displayTime(p.time) : "Any time"}</span>
                  <div className="plan__body">
                    <p className="plan__title">{p.title}</p>
                    {p.place && <p className="plan__place">At {p.place}</p>}
                    {p.note && <p className="plan__note">{p.note}</p>}
                    <p className="plan__meta">
                      {[
                        repeatLabel(p.repeat, p.starts_on),
                        p.time ? reminderLabel(p.remind_before) : "No time yet: reminder in the morning",
                      ].filter(Boolean).join(" · ")}
                    </p>
                    <div className="plan__actions">
                      <button className="link-button" onClick={() => setEditing({ kind: "change", plan: p })} aria-label={`Change ${p.title}`}>Change</button>
                      <button className="link-button" onClick={() => onRemove(p)} aria-label={`Remove ${p.title}`}>Remove</button>
                    </div>
                  </div>
                  <label className="check">
                    <input type="checkbox" checked={p.done} onChange={() => onToggle(p)} />
                    <span>Done</span>
                  </label>
                </li>
              ),
            )}
          </ol>
        )
      )}

      {editing?.kind === "new" ? (
        <PlanForm heading="Add to my day" saveLabel="Save" start={null} defaultDate={isPast ? today : day} defaultReminder={profile.defaultReminder} onSave={onAdd} onCancel={() => setEditing(null)} />
      ) : (
        <button className="button" onClick={() => { setEditing({ kind: "new" }); setMessage(""); }}>Add to my day</button>
      )}
    </>
  );
}
