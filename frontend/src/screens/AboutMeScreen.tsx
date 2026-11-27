import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import AppStatus from "../components/AppStatus";
import { useMilo } from "../data/MiloDataContext";
import { MEMORY_CATEGORIES } from "../types";
import { REMINDERS } from "../components/PlanForm";

export default function AboutMeScreen() {
  const {
    profile,
    memories,
    memoryState,
    memoryError,
    lastForgotten,
    reloadMemory,
    saveName,
    saveTown,
    saveDefaultReminder,
    saveMorningTime,
    setMemoryEnabled,
    addMemory,
    forgetMemory,
    undoForget,
    forgetEverything,
    showDetails,
    setShowDetails,
  } = useMilo();

  // ----- Name -----
  const [name, setName] = useState(profile.name);
  const [nameMessage, setNameMessage] = useState("");
  useEffect(() => setName(profile.name), [profile.name]);

  const onSaveName = async (event: FormEvent) => {
    event.preventDefault();
    const error = await saveName(name);
    setNameMessage(error ?? "Saved.");
  };

  // ----- Town -----
  const [town, setTown] = useState(profile.town);
  const [townMessage, setTownMessage] = useState<{ text: string; bad: boolean } | null>(null);
  const [savingTown, setSavingTown] = useState(false);
  useEffect(() => setTown(profile.town), [profile.town]);

  const onSaveTown = async (event: FormEvent) => {
    event.preventDefault();
    setSavingTown(true);
    const error = await saveTown(town);
    setSavingTown(false);
    setTownMessage(error ? { text: error, bad: true } : { text: town.trim() ? "Saved. Milo will use this for the weather." : "Town removed.", bad: false });
  };

  // ----- Default reminder -----
  const [reminderMessage, setReminderMessage] = useState<{ text: string; bad: boolean } | null>(null);
  const onReminderChange = async (value: string) => {
    const minutes = value === "null" ? null : Number(value);
    const { error, plansUpdated } = await saveDefaultReminder(minutes);
    setReminderMessage(
      error
        ? { text: error, bad: true }
        : { text: `Saved.${plansUpdated ? ` ${plansUpdated} of your plans changed to match.` : ""}`, bad: false },
    );
  };

  // ----- Morning reminder for plans with no time -----
  const [morningMessage, setMorningMessage] = useState<{ text: string; bad: boolean } | null>(null);
  const onMorningChange = async (value: string) => {
    const error = await saveMorningTime(value === "off" ? null : value);
    setMorningMessage(error ? { text: error, bad: true } : { text: "Saved.", bad: false });
  };
  const morningChoices = ["07:00", "08:00", "09:00", "10:00", "11:00"];

  // ----- Remembering on/off -----
  const [switchError, setSwitchError] = useState("");
  const onToggle = async (on: boolean) => setSwitchError((await setMemoryEnabled(on)) ?? "");

  // ----- Add something -----
  const [adding, setAdding] = useState(false);
  const [category, setCategory] = useState<string>(MEMORY_CATEGORIES[0]);
  const [text, setText] = useState("");
  const [addError, setAddError] = useState("");

  const onAdd = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    const error = await addMemory(category, text.trim());
    if (error) {
      setAddError(error);
      return;
    }
    setText("");
    setAddError("");
    setAdding(false);
  };

  // ----- Forget everything -----
  const [confirmingWipe, setConfirmingWipe] = useState(false);
  const [wipeError, setWipeError] = useState("");
  const onWipe = async () => {
    const error = await forgetEverything();
    setWipeError(error ?? "");
    if (!error) setConfirmingWipe(false);
  };

  // Group memories by category, and only show groups that have something in them.
  const known = new Set<string>(MEMORY_CATEGORIES);
  const groups = [...MEMORY_CATEGORIES, ...new Set(memories.map((m) => m.category).filter((c) => !known.has(c)))]
    .map((c) => ({ category: c, items: memories.filter((m) => m.category === c) }))
    .filter((g) => g.items.length > 0);

  if (memoryState === "loading") {
    return (
      <>
        <h1 className="screen__title" tabIndex={-1}>About me</h1>
        <p className="screen__lead">Loading what Milo remembers…</p>
      </>
    );
  }

  if (memoryState === "error") {
    return (
      <>
        <h1 className="screen__title" tabIndex={-1}>About me</h1>
        <div className="chat-error" role="alert">
          <p>{memoryError}</p>
          <button className="button button--quiet" onClick={reloadMemory}>Try again</button>
        </div>
        <AppStatus />
      </>
    );
  }

  return (
    <>
      <h1 className="screen__title" tabIndex={-1}>About me</h1>
      <p className="screen__lead">
        This is everything Milo remembers about you. Milo uses it to be more helpful. You can remove anything at any time.
      </p>

      {/* ----- Name ----- */}
      <form className="panel name-form" onSubmit={onSaveName}>
        <label htmlFor="your-name" className="panel__title">Your name</label>
        <div className="composer__row">
          <input
            id="your-name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setNameMessage("");
            }}
            placeholder="What should Milo call you?"
            maxLength={60}
            autoComplete="given-name"
          />
          <button type="submit" className="button" disabled={name.trim() === profile.name}>Save</button>
        </div>
        {nameMessage && <p className="form-message" role="status">{nameMessage}</p>}
      </form>

      {/* ----- Town ----- */}
      <form className="panel name-form" onSubmit={onSaveTown}>
        <label htmlFor="your-town" className="panel__title">Your town (for the weather)</label>
        <div className="composer__row">
          <input
            id="your-town"
            value={town}
            onChange={(e) => {
              setTown(e.target.value);
              setTownMessage(null);
            }}
            placeholder="For example, Uppsala, Sweden"
            maxLength={120}
            autoComplete="address-level2"
          />
          <button type="submit" className="button" disabled={savingTown || town.trim() === profile.town}>
            {savingTown ? "Finding…" : "Save"}
          </button>
        </div>
        {townMessage && (
          <p className={`form-message ${townMessage.bad ? "form-message--bad" : ""}`} role={townMessage.bad ? "alert" : "status"}>
            {townMessage.text}
          </p>
        )}
      </form>

      {/* ----- Default reminder ----- */}
      <div className="panel name-form">
        <label htmlFor="default-reminder" className="panel__title">Reminders for my plans</label>
        <select
          id="default-reminder"
          value={String(profile.defaultReminder)}
          onChange={(e) => void onReminderChange(e.target.value)}
        >
          {REMINDERS.map((r) => (
            <option key={r.label} value={String(r.value)}>{r.label}</option>
          ))}
          {!REMINDERS.some((r) => r.value === profile.defaultReminder) && (
            <option value={String(profile.defaultReminder)}>{profile.defaultReminder} minutes before</option>
          )}
        </select>
        <p className="panel__note">For plans with a time. Plans whose reminder you set yourself keep their own. You can also just tell Milo.</p>
        {reminderMessage && (
          <p className={`form-message ${reminderMessage.bad ? "form-message--bad" : ""}`} role={reminderMessage.bad ? "alert" : "status"}>
            {reminderMessage.text}
          </p>
        )}
      </div>

      {/* ----- Morning reminder ----- */}
      <div className="panel name-form">
        <label htmlFor="morning-time" className="panel__title">Plans with no time</label>
        <select id="morning-time" value={profile.morningTime ?? "off"} onChange={(e) => void onMorningChange(e.target.value)}>
          {morningChoices.map((t) => (
            <option key={t} value={t}>Remind me at {t}</option>
          ))}
          {profile.morningTime && !morningChoices.includes(profile.morningTime) && (
            <option value={profile.morningTime}>Remind me at {profile.morningTime}</option>
          )}
          <option value="off">Don't remind me</option>
        </select>
        <p className="panel__note">That morning, Milo lists the day's plans that have no time yet, and can suggest a good time for them.</p>
        {morningMessage && (
          <p className={`form-message ${morningMessage.bad ? "form-message--bad" : ""}`} role={morningMessage.bad ? "alert" : "status"}>
            {morningMessage.text}
          </p>
        )}
      </div>

      {/* ----- Remembering on/off ----- */}
      <div className="panel">
        <label className="switch">
          <input type="checkbox" checked={profile.memoryEnabled} onChange={(e) => onToggle(e.target.checked)} />
          <span>Let Milo remember new things I tell it</span>
        </label>
        <p className="panel__note">
          {profile.memoryEnabled
            ? "When you chat, Milo saves useful things, like what you enjoy. You'll see a note each time it does."
            : "Milo won't save anything new. It still uses what's already listed below, and you can still remove things."}
        </p>
        {switchError && <p className="form-message form-message--bad" role="alert">{switchError}</p>}
      </div>

      {lastForgotten && (
        <div className="undo" role="status">
          <p>Forgotten: “{lastForgotten.text}”</p>
          <button className="button button--quiet" onClick={undoForget}>Undo</button>
        </div>
      )}
      {memoryError && <p className="form-message form-message--bad" role="alert">{memoryError}</p>}

      {/* ----- What Milo remembers ----- */}
      {groups.length === 0 ? (
        <p className="panel">
          Milo doesn't remember anything about you yet. <Link to="/chat" className="text-link">Tell Milo about yourself</Link>, or
          add something below.
        </p>
      ) : (
        groups.map(({ category: c, items }) => (
          <section key={c} className="memory-group" aria-labelledby={`cat-${c}`}>
            <h2 id={`cat-${c}`} className="memory-group__title">{c}</h2>
            <ul className="memory-list">
              {items.map((m) => (
                <li key={m.id} className="memory">
                  <p>{m.text}</p>
                  <button className="button button--quiet" onClick={() => forgetMemory(m.id)} aria-label={`Forget: ${m.text}`}>
                    Forget
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      {/* ----- Add something ----- */}
      {adding ? (
        <form className="panel add-form" onSubmit={onAdd}>
          <h2 className="panel__title">Tell Milo something to remember</h2>
          <label htmlFor="memory-text">What should Milo remember?</label>
          <input
            id="memory-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="For example, I love jazz"
            maxLength={200}
            autoFocus
          />
          <label htmlFor="memory-category">Which group?</label>
          <select id="memory-category" value={category} onChange={(e) => setCategory(e.target.value)}>
            {MEMORY_CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          {addError && <p className="form-message form-message--bad" role="alert">{addError}</p>}
          <div className="add-form__buttons">
            <button type="submit" className="button" disabled={!text.trim()}>Save</button>
            <button type="button" className="button button--quiet" onClick={() => setAdding(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <button className="button" onClick={() => setAdding(true)}>Add something</button>
      )}

      {/* ----- Forget everything ----- */}
      {memories.length > 0 && (
        <div className="danger-zone">
          {confirmingWipe ? (
            <div className="panel panel--danger" role="alertdialog" aria-labelledby="wipe-q">
              <p id="wipe-q" className="panel__big">Forget everything Milo remembers about you?</p>
              <p>This removes all {memories.length} things listed above. It can't be undone.</p>
              {wipeError && <p className="form-message form-message--bad" role="alert">{wipeError}</p>}
              <div className="add-form__buttons">
                <button className="button button--danger" onClick={onWipe}>Yes, forget everything</button>
                <button className="button button--quiet" onClick={() => setConfirmingWipe(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <button className="button button--quiet button--danger-quiet" onClick={() => setConfirmingWipe(true)}>
              Forget everything
            </button>
          )}
        </div>
      )}

      {/* ----- For helpers ----- */}
      <div className="panel helper-panel">
        <label className="switch">
          <input type="checkbox" checked={showDetails} onChange={(e) => setShowDetails(e.target.checked)} />
          <span>Show what Milo looked up and remembered</span>
        </label>
        <p className="panel__note">
          Adds small notes and links under Milo's replies in the chat. Useful for helpers and testing. This only
          changes this device.
        </p>
      </div>

      <AppStatus />
    </>
  );
}
