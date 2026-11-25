import { useState, type FormEvent } from "react";
import { useMilo } from "../data/MiloDataContext";
import { displayTime, longDate } from "../utils/time";

export default function MyDayScreen() {
  const { plans, togglePlanDone, addPlan } = useMilo();
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [time, setTime] = useState("");

  const sorted = [...plans].sort((a, b) => a.time.localeCompare(b.time));

  const onSave = (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim() || !time) return;
    addPlan(title.trim(), time);
    setTitle("");
    setTime("");
    setAdding(false);
  };

  return (
    <>
      <h1 className="screen__title" tabIndex={-1}>My day</h1>
      <p className="screen__lead">{longDate()}</p>

      {sorted.length === 0 ? (
        <p className="panel">Nothing planned yet. Add something below.</p>
      ) : (
        <ol className="plan">
          {sorted.map((item) => (
            <li key={item.id} className={`plan__item ${item.done ? "plan__item--done" : ""}`}>
              <span className="plan__time">{displayTime(item.time)}</span>
              <div className="plan__body">
                <p className="plan__title">{item.title}</p>
                {item.note && <p className="plan__note">{item.note}</p>}
              </div>
              <label className="check">
                <input type="checkbox" checked={item.done} onChange={() => togglePlanDone(item.id)} />
                <span>Done</span>
              </label>
            </li>
          ))}
        </ol>
      )}

      {adding ? (
        <form className="panel add-form" onSubmit={onSave}>
          <h2 className="panel__title">Add to my day</h2>
          <label htmlFor="plan-title">What</label>
          <input id="plan-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="For example, visit the library" autoFocus />
          <label htmlFor="plan-time">When</label>
          <input id="plan-time" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
          <div className="add-form__buttons">
            <button type="submit" className="button" disabled={!title.trim() || !time}>Save</button>
            <button type="button" className="button button--quiet" onClick={() => setAdding(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <button className="button" onClick={() => setAdding(true)}>Add to my day</button>
      )}
    </>
  );
}
