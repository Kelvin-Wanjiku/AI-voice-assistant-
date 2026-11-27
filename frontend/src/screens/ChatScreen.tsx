import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMilo } from "../data/MiloDataContext";
import type { MemoryNote } from "../types";

const NOTE_LABEL: Record<MemoryNote["kind"], string> = {
  added: "Remembered",
  updated: "Updated",
  removed: "Forgot",
  name: "Now calling you",
};

export default function ChatScreen() {
  const { messages, thinking, chatError, sendMessage, retryLastMessage, undoChatMemory, showDetails } = useMilo();
  // While Milo is busy: show "Thinking…", unless it has just said "let me check" (that says it already).
  const waitingQuietly = thinking && !messages[messages.length - 1]?.holding;
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keep the newest message (or the "thinking" line, or the error) in view.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, thinking, chatError]);

  // When Milo has answered, put the cursor back in the box so the person can reply straight away.
  const wasThinking = useRef(false);
  useEffect(() => {
    if (wasThinking.current && !thinking) inputRef.current?.focus({ preventScroll: true });
    wasThinking.current = thinking;
  }, [thinking]);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || thinking) return;
    sendMessage(trimmed);
    setText("");
  };

  return (
    <>
      <h1 className="screen__title" tabIndex={-1}>Chat with Milo</h1>

      <section className="chat" aria-label="Conversation" aria-live="polite">
        {messages.map((m) => (
          <div key={m.id} className={`turn turn--${m.role}${m.holding ? " turn--holding" : ""}`}>
            <div className={`bubble bubble--${m.role}`}>
              <span className="bubble__who">{m.role === "user" ? "You" : "Milo"}</span>
              <p>{m.content}</p>
            </div>

            {/* What Milo looked up for this answer, with links to where it came from. */}
            {showDetails && m.lookups && (
              <ul className="notes notes--lookup" aria-label="What Milo looked up">
                {m.lookups.map((l, i) => (
                  <li key={i} className="note note--lookup">
                    <strong className={l.failed ? "note__failed" : undefined}>{l.label}</strong>
                    {l.sources.length > 0 && (
                      <ul className="sources">
                        {l.sources.map((s) => (
                          <li key={s.url}>
                            <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {/* What Milo's memory did during this turn, so nothing is remembered behind the person's back. */}
            {showDetails && m.notes && (
              <ul className="notes" aria-label="Memory changes">
                {m.notes.map((note, i) => (
                  <li key={i} className={`note ${note.undone ? "note--undone" : ""}`}>
                    <span>
                      <strong>{note.undone ? "Not remembered" : NOTE_LABEL[note.kind]}:</strong> {note.text}
                    </span>
                    {note.kind === "added" && !note.undone && note.memoryId && (
                      <button
                        className="link-button"
                        onClick={() => undoChatMemory(m.id, note.memoryId!)}
                        aria-label={`Don't remember: ${note.text}`}
                      >
                        Undo
                      </button>
                    )}
                  </li>
                ))}
                <li className="note note--hint">
                  <Link to="/about-me">See everything Milo remembers</Link>
                </li>
              </ul>
            )}
          </div>
        ))}

        {waitingQuietly && (
          <div className="bubble bubble--assistant bubble--thinking">
            <span className="bubble__who">Milo</span>
            <p>Thinking…</p>
          </div>
        )}

        {chatError && !thinking && (
          <div className="chat-error" role="alert">
            <p>{chatError}</p>
            <button className="button button--quiet" onClick={retryLastMessage}>Try again</button>
          </div>
        )}
        <div ref={endRef} />
      </section>

      <form className="composer" onSubmit={onSubmit}>
        <label htmlFor="message" className="composer__label">Your message</label>
        <div className="composer__row">
          <input
            id="message"
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type to Milo…"
            autoComplete="off"
            maxLength={2000}
          />
          <button type="submit" className="button" disabled={!text.trim() || thinking}>
            Send
          </button>
        </div>
      </form>
    </>
  );
}
