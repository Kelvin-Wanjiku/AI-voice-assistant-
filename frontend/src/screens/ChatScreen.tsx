import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMilo } from "../data/MiloDataContext";

export default function ChatScreen() {
  const { messages, sendMessage } = useMilo();
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  // Keep the newest message in view.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
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
        <div ref={endRef} />
      </section>

      <form className="composer" onSubmit={onSubmit}>
        <label htmlFor="message" className="composer__label">Your message</label>
        <div className="composer__row">
          <input
            id="message"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type to Milo…"
            autoComplete="off"
          />
          <button type="submit" className="button" disabled={!text.trim()}>
            Send
          </button>
        </div>
      </form>
    </>
  );
}
