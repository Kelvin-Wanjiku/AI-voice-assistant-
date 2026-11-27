// One shared place for Milo's data, so every screen sees the same profile, memories, plans and chat.
// Chat, memories, live information and plans all come from the backend now.
// Screens that show plans fetch them themselves; `plansVersion` tells them when to fetch again.

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import * as api from "../api";
import type { ChatMessage, Memory, MemoryChanges, MemoryNote, Profile } from "../types";
import { firstGreeting } from "./sampleData";

type LoadState = "loading" | "ready" | "error";

interface MiloData {
  // Profile and memories
  profile: Profile;
  memories: Memory[];
  memoryState: LoadState;
  memoryError: string | null;
  lastForgotten: Memory | null;
  reloadMemory: () => void;
  saveName: (name: string) => Promise<string | null>;
  saveTown: (town: string) => Promise<string | null>;
  saveDefaultReminder: (minutes: number | null) => Promise<{ error: string | null; plansUpdated: number }>;
  saveMorningTime: (time: string | null) => Promise<string | null>;
  setMemoryEnabled: (on: boolean) => Promise<string | null>;
  addMemory: (category: string, text: string) => Promise<string | null>;
  forgetMemory: (id: string) => Promise<void>;
  undoForget: () => Promise<void>;
  forgetEverything: () => Promise<string | null>;

  // Plans: a counter that goes up whenever plans change (in the chat, on My day, or from a reminder)
  plansVersion: number;
  plansChanged: () => void;

  // Display
  showDetails: boolean; // show look-ups, links and memory notes under Milo's replies
  setShowDetails: (on: boolean) => void;

  // Chat
  messages: ChatMessage[];
  thinking: boolean;
  chatError: string | null;
  sendMessage: (text: string) => void;
  retryLastMessage: () => void;
  undoChatMemory: (messageId: string, memoryId: string) => Promise<void>;
}

const MiloDataContext = createContext<MiloData | null>(null);

function newId(): string {
  return Math.random().toString(36).slice(2, 10);
}

const errorText = (err: unknown) => (err instanceof Error ? err.message : "Something went wrong. Please try again.");

/** Turn the memory changes from one chat turn into short notes to show under Milo's reply. */
function notesFrom(changes: MemoryChanges): MemoryNote[] {
  return [
    ...changes.added.map((m) => ({ kind: "added" as const, text: m.text, memoryId: m.id })),
    ...changes.updated.map((m) => ({ kind: "updated" as const, text: m.text, memoryId: m.id })),
    ...changes.removed.map((m) => ({ kind: "removed" as const, text: m.text })),
    ...(changes.name ? [{ kind: "name" as const, text: changes.name }] : []),
  ];
}

export function MiloDataProvider({ children }: { children: ReactNode }) {
  // ---------- Profile and memories ----------
  const [profile, setProfile] = useState<Profile>({
    name: "",
    memoryEnabled: true,
    town: "",
    defaultReminder: 15,
    morningTime: "09:00",
  });
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryState, setMemoryState] = useState<LoadState>("loading");
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [lastForgotten, setLastForgotten] = useState<Memory | null>(null);

  // ---------- Plans ----------
  const [plansVersion, setPlansVersion] = useState(0);
  const plansChanged = useCallback(() => setPlansVersion((v) => v + 1), []);

  const reloadMemory = useCallback(async () => {
    setMemoryState("loading");
    setMemoryError(null);
    try {
      const [p, m] = await Promise.all([api.fetchProfile(), api.fetchMemories()]);
      setProfile(p);
      setMemories(m);
      setMemoryState("ready");
    } catch (err) {
      setMemoryError(errorText(err));
      setMemoryState("error");
    }
  }, []);

  // Load what Milo remembers when the app opens.
  useEffect(() => {
    void reloadMemory();
  }, [reloadMemory]);

  /** Each of these returns an error message to show, or null when it worked. */
  const saveName = async (name: string) => {
    try {
      setProfile(await api.saveProfile({ name }));
      return null;
    } catch (err) {
      return errorText(err);
    }
  };

  const saveTown = async (town: string) => {
    try {
      setProfile(await api.saveProfile({ town }));
      return null;
    } catch (err) {
      return errorText(err);
    }
  };

  const saveDefaultReminder = async (minutes: number | null) => {
    try {
      const { profile: saved, plansUpdated } = await api.saveDefaultReminder(minutes);
      setProfile(saved);
      if (plansUpdated) setPlansVersion((v) => v + 1);
      return { error: null, plansUpdated };
    } catch (err) {
      return { error: errorText(err), plansUpdated: 0 };
    }
  };

  const saveMorningTime = async (time: string | null) => {
    try {
      setProfile(await api.saveMorningTime(time));
      return null;
    } catch (err) {
      return errorText(err);
    }
  };

  const setMemoryEnabled = async (on: boolean) => {
    setProfile((p) => ({ ...p, memoryEnabled: on })); // flip the switch straight away…
    try {
      setProfile(await api.saveProfile({ memoryEnabled: on }));
      return null;
    } catch (err) {
      setProfile((p) => ({ ...p, memoryEnabled: !on })); // …and put it back if saving failed
      return errorText(err);
    }
  };

  const addMemory = async (category: string, text: string) => {
    try {
      const saved = await api.createMemory(category, text);
      setMemories((all) => [...all, saved]);
      return null;
    } catch (err) {
      return errorText(err);
    }
  };

  const forgetMemory = async (id: string) => {
    const memory = memories.find((m) => m.id === id);
    if (!memory) return;
    setMemoryError(null);
    try {
      await api.deleteMemory(id);
      setMemories((all) => all.filter((m) => m.id !== id));
      setLastForgotten(memory);
    } catch (err) {
      setMemoryError(errorText(err));
    }
  };

  const undoForget = async () => {
    if (!lastForgotten) return;
    const error = await addMemory(lastForgotten.category, lastForgotten.text);
    if (error) setMemoryError(error);
    setLastForgotten(null);
  };

  const forgetEverything = async () => {
    try {
      await api.deleteAllMemories();
      setMemories([]);
      setLastForgotten(null);
      return null;
    } catch (err) {
      return errorText(err);
    }
  };

  // ---------- Display ----------
  // A per-device preference, kept in the browser. Off by default: Milo is a voice companion,
  // so the conversation should look like a conversation. Helpers can switch it on.
  const [showDetails, setShowDetailsState] = useState<boolean>(() => {
    try {
      return localStorage.getItem("milo.showDetails") === "yes";
    } catch {
      return false;
    }
  });
  const setShowDetails = (on: boolean) => {
    setShowDetailsState(on);
    try {
      localStorage.setItem("milo.showDetails", on ? "yes" : "no");
    } catch {
      // storage can be unavailable (private windows); the switch still works until the page closes
    }
  };

  // ---------- Chat ----------
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

  /** Keep About me in step with what the memory keeper changed during the chat. */
  const applyMemoryChanges = (changes: MemoryChanges) => {
    setMemories((all) => {
      const removedIds = new Set(changes.removed.map((m) => m.id));
      const updated = new Map(changes.updated.map((m) => [m.id, m]));
      return [...all.filter((m) => !removedIds.has(m.id)).map((m) => updated.get(m.id) ?? m), ...changes.added];
    });
    if (changes.name) setProfile((p) => ({ ...p, name: changes.name ?? p.name }));
  };

  /** Ask the backend for a reply to the conversation as it stands now. */
  const requestReply = async () => {
    setThinking(true);
    setChatError(null);
    try {
      // "Let me check" lines are for the person, not the AI, so they're left out of the history.
      const turns = messagesRef.current.filter((m) => !m.holding).map(({ role, content }) => ({ role, content }));
      const { reply, memory, lookups, plans_changed } = await api.sendChatStream(turns, (text) => {
        setConversation([...messagesRef.current, { id: newId(), role: "assistant", content: text, holding: true }]);
      });
      applyMemoryChanges(memory);
      if (plans_changed) {
        plansChanged();
        api.fetchProfile().then(setProfile).catch(() => {}); // the default reminder may have changed
      }
      const notes = notesFrom(memory);
      setConversation([
        ...messagesRef.current,
        {
          id: newId(),
          role: "assistant",
          content: reply,
          notes: notes.length ? notes : undefined,
          lookups: lookups?.length ? lookups : undefined,
        },
      ]);
    } catch (err) {
      setChatError(errorText(err));
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

  /** The "Undo" next to "Remembered: …" in the chat. */
  const undoChatMemory = async (messageId: string, memoryId: string) => {
    try {
      await api.deleteMemory(memoryId);
    } catch {
      // If it was already forgotten on About me, that's fine: the result is the same.
    }
    setMemories((all) => all.filter((m) => m.id !== memoryId));
    setConversation(
      messagesRef.current.map((m) =>
        m.id !== messageId
          ? m
          : { ...m, notes: m.notes?.map((n) => (n.memoryId === memoryId ? { ...n, undone: true } : n)) },
      ),
    );
  };

  return (
    <MiloDataContext.Provider
      value={{
        profile,
        memories,
        memoryState,
        memoryError,
        lastForgotten,
        reloadMemory: () => void reloadMemory(),
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
        plansVersion,
        plansChanged,
        messages,
        thinking,
        chatError,
        sendMessage,
        retryLastMessage,
        undoChatMemory,
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
