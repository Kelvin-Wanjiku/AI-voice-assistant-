// One shared place for Milo's data, so every screen sees the same plans, memories and chat.
// The chat now talks to the real backend (Phase 3). Plans and memories are still sample data
// until Phases 4 and 6; when those arrive, only this file changes, not the screens.

import { createContext, useContext, useRef, useState, type ReactNode } from "react";
import { sendChat } from "../api";
import type { ChatMessage, Memory, PlanItem, Profile } from "../types";
import { firstGreeting, sampleMemories, samplePlans, sampleProfile } from "./sampleData";

interface MiloData {
  profile: Profile;
  plans: PlanItem[];
  memories: Memory[];
  messages: ChatMessage[];
  thinking: boolean; // true while waiting for Milo's reply
  chatError: string | null; // a message to show when a reply failed
  lastForgotten: Memory | null;
  togglePlanDone: (id: string) => void;
  addPlan: (title: string, time: string, note?: string) => void;
  forgetMemory: (id: string) => void;
  undoForget: () => void;
  sendMessage: (text: string) => void;
  retryLastMessage: () => void;
}

const MiloDataContext = createContext<MiloData | null>(null);

function newId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function MiloDataProvider({ children }: { children: ReactNode }) {
  const [profile] = useState<Profile>(sampleProfile);
  const [plans, setPlans] = useState<PlanItem[]>(samplePlans);
  const [memories, setMemories] = useState<Memory[]>(sampleMemories);
  const [lastForgotten, setLastForgotten] = useState<Memory | null>(null);
  const forgottenIndex = useRef(0);

  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "greeting", role: "assistant", content: firstGreeting },
  ]);
  const [thinking, setThinking] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  // A copy of the conversation that is always up to date, for building the request.
  const messagesRef = useRef<ChatMessage[]>(messages);

  const setConversation = (next: ChatMessage[]) => {
    messagesRef.current = next;
    setMessages(next);
  };

  // ---------- Plans ----------
  const togglePlanDone = (id: string) =>
    setPlans((all) => all.map((p) => (p.id === id ? { ...p, done: !p.done } : p)));

  const addPlan = (title: string, time: string, note?: string) =>
    setPlans((all) => [...all, { id: newId(), title, time, note, done: false }]);

  // ---------- Memories ----------
  const forgetMemory = (id: string) => {
    const index = memories.findIndex((m) => m.id === id);
    if (index === -1) return;
    forgottenIndex.current = index;
    setLastForgotten(memories[index]);
    setMemories(memories.filter((m) => m.id !== id));
  };

  const undoForget = () => {
    if (!lastForgotten) return;
    const restored = [...memories];
    restored.splice(forgottenIndex.current, 0, lastForgotten); // put it back where it was
    setMemories(restored);
    setLastForgotten(null);
  };

  // ---------- Chat ----------
  /** Ask the backend for a reply to the conversation as it stands now. */
  const requestReply = async () => {
    setThinking(true);
    setChatError(null);
    try {
      const turns = messagesRef.current.map(({ role, content }) => ({ role, content }));
      const reply = await sendChat(turns);
      setConversation([...messagesRef.current, { id: newId(), role: "assistant", content: reply }]);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setThinking(false);
    }
  };

  const sendMessage = (text: string) => {
    if (thinking) return;
    setConversation([...messagesRef.current, { id: newId(), role: "user", content: text }]);
    void requestReply();
  };

  /** After an error, the person's message is still the last one, so just ask again. */
  const retryLastMessage = () => {
    if (thinking) return;
    void requestReply();
  };

  return (
    <MiloDataContext.Provider
      value={{
        profile,
        plans,
        memories,
        messages,
        thinking,
        chatError,
        lastForgotten,
        togglePlanDone,
        addPlan,
        forgetMemory,
        undoForget,
        sendMessage,
        retryLastMessage,
      }}
    >
      {children}
    </MiloDataContext.Provider>
  );
}

/** Use this in any screen to read or change Milo's data. */
export function useMilo(): MiloData {
  const data = useContext(MiloDataContext);
  if (!data) throw new Error("useMilo must be used inside MiloDataProvider");
  return data;
}
