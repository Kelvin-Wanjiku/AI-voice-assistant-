// The shapes of Milo's data. They match backend/app/schemas.py.

// The groups shown on About me, in this order. Same list as CATEGORIES in backend/app/memory_store.py.
export const MEMORY_CATEGORIES = [
  "Life and home",
  "Interests",
  "Food",
  "Routines",
  "Family and friends",
  "Health",
  "Goals",
] as const;

export type MemoryCategory = (typeof MEMORY_CATEGORIES)[number];

export interface Memory {
  id: string;
  category: string;
  text: string;
  source: "chat" | "added" | string;
}

export interface Profile {
  name: string;
  memoryEnabled: boolean;
  town: string; // e.g. "Uppsala, Sweden"; "" when not set
  defaultReminder: number | null; // minutes before new plans; null = no reminder
  morningTime: string | null; // "HH:MM" reminder for plans with no time; null = off
}

/** One plan as it appears on one day (repeating plans appear on every matching day). */
export interface Plan {
  id: string;
  title: string;
  date: string; // the day it's shown on, "YYYY-MM-DD"
  time: string | null; // "HH:MM", or null for "any time"
  duration_minutes: number | null;
  note: string | null;
  repeat: "none" | "daily" | "weekly";
  remind_before: number | null; // minutes before; null = no reminder
  done: boolean;
  source: string;
  starts_on: string; // first day, for repeating plans
  place: string | null;
}

/** What's needed to create or change a plan. */
export interface PlanInput {
  title: string;
  date: string;
  time: string | null;
  note: string | null;
  place: string | null;
  repeat: Plan["repeat"];
  remind_before: number | null;
}

export interface Reminder {
  plan_id: string;
  date: string;
  title: string;
  time: string | null; // null: a plan with no time, reminded in the morning
  minutes_until: number;
  place: string | null;
  kind: "timed" | "morning";
}

/** A small line under one of Milo's replies, saying what changed in its memory. */
export interface MemoryNote {
  kind: "added" | "updated" | "removed" | "name";
  text: string;
  memoryId?: string;
  undone?: boolean;
}

/** Something Milo looked up while answering, with links to where the information came from. */
export interface Lookup {
  label: string;
  failed: boolean;
  sources: { title: string; url: string }[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  notes?: MemoryNote[];
  lookups?: Lookup[];
  holding?: boolean; // "Let me check that for you": shown and spoken, but not sent back to the AI
}

export interface Weather {
  place: string;
  temperature: number;
  description: string;
  high: number;
  low: number;
  rain_chance: number | null;
}

export interface Headline {
  title: string;
  url: string;
  topic: string;
  source: string;
}

/** What changed in Milo's memory during one chat turn. */
export interface MemoryChanges {
  added: Memory[];
  updated: Memory[];
  removed: Memory[];
  name: string | null;
}
