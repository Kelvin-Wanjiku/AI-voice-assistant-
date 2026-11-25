// The shapes of Milo's data. The backend will use the same shapes in later phases.

export type MemoryCategory =
  | "Interests"
  | "Food"
  | "Routines"
  | "Family and friends"
  | "Health"
  | "Goals";

export interface Memory {
  id: string;
  category: MemoryCategory;
  text: string;
}

export interface PlanItem {
  id: string;
  time: string; // 24-hour "HH:MM", e.g. "14:30"
  title: string;
  note?: string;
  done: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export interface Profile {
  name: string;
}
