import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMilo } from "../data/MiloDataContext";

export default function ChatScreen() {
  const { messages, thinking, chatError, sendMessage, retryLastMessage } = useMilo();
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
          <div key={m.id} className={`bubble bubble--${m.role}`}>
            <span className="bubble__who">{m.role === "user" ? "You" : "Milo"}</span>
            <p>{m.content}</p>
          </div>
        ))}

        {thinking && (
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
