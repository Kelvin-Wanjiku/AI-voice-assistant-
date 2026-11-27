// Everything the frontend asks the backend goes through this file.

import type { Headline, Lookup, Memory, MemoryChanges, Plan, PlanInput, Profile, Reminder, Weather } from "./types";

export type PartStatus = "ok" | "not_configured" | "error";

export interface PartHealth {
  status: PartStatus;
  message?: string;
}

export interface HealthResponse {
  app: string;
  backend: PartHealth;
  ai: PartHealth;
  database: PartHealth;
  web_search: PartHealth;
}

/** One line of the conversation, in the shape the backend expects. */
export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

const BACKEND_DOWN = "Milo's backend isn't answering. Is it running in the other terminal?";

/** Send a request to the backend. Throws an Error whose message is safe to show. */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    });
  } catch {
    throw new Error(BACKEND_DOWN);
  }

  if (!res.ok) {
    let detail = `Something went wrong (status ${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // The proxy answers with plain text when the backend is down.
      if (res.status === 500 || res.status === 502 || res.status === 504) detail = BACKEND_DOWN;
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---------- Health ----------
export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

// ---------- Chat ----------
export interface ChatResult {
  reply: string;
  memory: MemoryChanges;
  lookups: Lookup[];
  plans_changed: boolean;
}

export function sendChat(turns: ChatTurn[]): Promise<ChatResult> {
  return request<ChatResult>("/chat", { method: "POST", body: JSON.stringify({ messages: turns }) });
}

/**
 * Like sendChat, but Milo can say "let me check that for you" first if a look-up takes a while.
 * onHolding is called with each of those lines; the promise gives the final answer.
 * The backend sends one JSON object per line: {"type": "holding" | "reply" | "error", ...}.
 */
export async function sendChatStream(turns: ChatTurn[], onHolding: (text: string) => void): Promise<ChatResult> {
  let res: Response;
  try {
    res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: turns }),
    });
  } catch {
    throw new Error(BACKEND_DOWN);
  }
  if (!res.ok || !res.body) {
    let detail = `Something went wrong (status ${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      if (res.status === 500 || res.status === 502 || res.status === 504) detail = BACKEND_DOWN;
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    let chunk: ReadableStreamReadResult<Uint8Array>;
    try {
      chunk = await reader.read();
    } catch {
      throw new Error(BACKEND_DOWN);
    }
    buffer += decoder.decode(chunk.value ?? new Uint8Array(), { stream: !chunk.done });
    let newline: number;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (!line) continue;
      const event = JSON.parse(line);
      if (event.type === "holding") onHolding(event.text);
      else if (event.type === "reply") return event as ChatResult;
      else if (event.type === "error") throw new Error(event.detail || "Something went wrong. Please try again.");
    }
    if (chunk.done) break;
  }
  throw new Error("Milo stopped before answering. Please try again.");
}

// ---------- Profile ----------
interface ProfileWire {
  name: string;
  memory_enabled: boolean;
  town: string | null;
  default_reminder: number | null;
  morning_time: string | null;
  plans_updated?: number;
}

const toProfile = (p: ProfileWire): Profile => ({
  name: p.name,
  memoryEnabled: p.memory_enabled,
  town: p.town ?? "",
  defaultReminder: p.default_reminder,
  morningTime: p.morning_time,
});

/** Change (or switch off, with null) the morning reminder for plans with no time. */
export async function saveMorningTime(time: string | null): Promise<Profile> {
  return toProfile(await request<ProfileWire>("/profile", { method: "PUT", body: JSON.stringify({ morning_time: time }) }));
}

export async function fetchProfile(): Promise<Profile> {
  return toProfile(await request<ProfileWire>("/profile"));
}

/** Change the default reminder. Returns the profile and how many existing plans changed with it. */
export async function saveDefaultReminder(minutes: number | null): Promise<{ profile: Profile; plansUpdated: number }> {
  const wire = await request<ProfileWire>("/profile", { method: "PUT", body: JSON.stringify({ default_reminder: minutes }) });
  return { profile: toProfile(wire), plansUpdated: wire.plans_updated ?? 0 };
}

export async function saveProfile(changes: Partial<Profile>): Promise<Profile> {
  const body: Partial<ProfileWire> = {};
  if (changes.name !== undefined) body.name = changes.name;
  if (changes.memoryEnabled !== undefined) body.memory_enabled = changes.memoryEnabled;
  if (changes.town !== undefined) body.town = changes.town;
  return toProfile(await request<ProfileWire>("/profile", { method: "PUT", body: JSON.stringify(body) }));
}

// ---------- Memories ----------
export function fetchMemories(): Promise<Memory[]> {
  return request<Memory[]>("/memories");
}

export function createMemory(category: string, text: string): Promise<Memory> {
  return request<Memory>("/memories", { method: "POST", body: JSON.stringify({ category, text }) });
}

export function deleteMemory(id: string): Promise<Memory> {
  return request<Memory>(`/memories/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function deleteAllMemories(): Promise<{ forgotten: number }> {
  return request<{ forgotten: number }>("/memories", { method: "DELETE" });
}

// ---------- Live information (Home screen) ----------
export function fetchWeather(): Promise<Weather> {
  return request<Weather>("/weather");
}

export function fetchNews(limit = 4): Promise<Headline[]> {
  return request<Headline[]>(`/news?limit=${limit}`);
}

// ---------- Plans and reminders (Phase 6) ----------
export interface PlanSaved {
  plan: Plan;
  clashes: Plan[];
  merged: string; // set when a similar plan already existed and was completed instead
}

export function fetchPlans(date: string): Promise<Plan[]> {
  return request<Plan[]>(`/plans?date=${encodeURIComponent(date)}`);
}

export function fetchUpcoming(days = 2): Promise<Plan[]> {
  return request<Plan[]>(`/plans/upcoming?days=${days}`);
}

export function createPlan(plan: PlanInput): Promise<PlanSaved> {
  return request<PlanSaved>("/plans", { method: "POST", body: JSON.stringify(plan) });
}

export function updatePlan(id: string, changes: Partial<PlanInput>): Promise<PlanSaved> {
  return request<PlanSaved>(`/plans/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(changes) });
}

export function deletePlan(id: string): Promise<Plan> {
  return request<Plan>(`/plans/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function setPlanDone(id: string, date: string, done: boolean): Promise<Plan> {
  return request<Plan>(`/plans/${encodeURIComponent(id)}/done`, { method: "POST", body: JSON.stringify({ date, done }) });
}

export function fetchReminders(): Promise<Reminder[]> {
  return request<Reminder[]>("/reminders");
}

export function answerReminder(r: Reminder, action: "ok" | "snooze" | "done", minutes = 10): Promise<{ ok: boolean }> {
  return request(`/reminders/${encodeURIComponent(r.plan_id)}/${r.date}`, {
    method: "POST",
    body: JSON.stringify({ action, minutes }),
  });
}
