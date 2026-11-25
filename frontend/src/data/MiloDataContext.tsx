// One shared place for Milo's data, so every screen sees the same plans, memories and chat.
// Today it holds sample data in the browser. In later phases these functions will call the
// backend instead, and the screens won't need to change.

import { createContext, useContext, useRef, useState, type ReactNode } from "react";
import type { ChatMessage, Memory, PlanItem, Profile } from "../types";
import { sampleMemories, sampleMessages, samplePlans, sampleProfile } from "./sampleData";

interface MiloData {
  profile: Profile;
  plans: PlanItem[];
  memories: Memory[];
  messages: ChatMessage[];
  lastForgotten: Memory | null;
  togglePlanDone: (id: string) => void;
  addPlan: (title: string, time: string, note?: string) => void;
  forgetMemory: (id: string) => void;
  undoForget: () => void;
  sendMessage: (text: string) => void;
}

const MiloDataContext = createContext<MiloData | null>(null);

function newId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function MiloDataProvider({ children }: { children: ReactNode }) {
  const [profile] = useState<Profile>(sampleProfile);
  const [plans, setPlans] = useState<PlanItem[]>(samplePlans);
  const [memories, setMemories] = useState<Memory[]>(sampleMemories);
  const [messages, setMessages] = useState<ChatMessage[]>(sampleMessages);
  const [lastForgotten, setLastForgotten] = useState<Memory | null>(null);
  const forgottenIndex = useRef(0);

  const togglePlanDone = (id: string) =>
    setPlans((all) => all.map((p) => (p.id === id ? { ...p, done: !p.done } : p)));

  const addPlan = (title: string, time: string, note?: string) =>
    setPlans((all) => [...all, { id: newId(), title, time, note, done: false }]);

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

  const sendMessage = (text: string) => {
    setMessages((all) => [...all, { id: newId(), role: "user", content: text }]);
    // Placeholder until Phase 3 connects Milo's AI brain.
    window.setTimeout(() => {
      setMessages((all) => [
        ...all,
        {
          id: newId(),
          role: "assistant",
          content: "I can't answer properly yet. My thinking gets switched on in the next step of building me.",
        },
      ]);
    }, 600);
  };

  return (
    <MiloDataContext.Provider
      value={{
        profile,
        plans,
        memories,
        messages,
        lastForgotten,
        togglePlanDone,
        addPlan,
        forgetMemory,
        undoForget,
        sendMessage,
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
