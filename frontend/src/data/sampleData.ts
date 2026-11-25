// Pretend data so we can see and test the screens.
// The chat is real since Phase 3. Phase 4 replaces the memories, Phase 5 the weather, Phase 6 the plans.

import type { Memory, PlanItem, Profile } from "../types";

export const sampleProfile: Profile = { name: "Margaret" };

export const samplePlans: PlanItem[] = [
  { id: "p1", time: "09:00", title: "Morning tablets", done: true },
  { id: "p2", time: "11:30", title: "Call Anna", note: "Ask about Sunday lunch", done: false },
  { id: "p3", time: "15:00", title: "Walk in the park", note: "If the weather is dry", done: false },
  { id: "p4", time: "18:00", title: "Cook dinner", note: "Fish and potatoes", done: false },
];

export const sampleMemories: Memory[] = [
  { id: "m1", category: "Interests", text: "Loves gardening, especially in summer" },
  { id: "m2", category: "Interests", text: "Enjoys listening to jazz" },
  { id: "m3", category: "Food", text: "Likes fish" },
  { id: "m4", category: "Food", text: "Doesn't like mushrooms" },
  { id: "m5", category: "Routines", text: "Usually walks after lunch" },
  { id: "m6", category: "Family and friends", text: "Daughter Anna visits on Sundays" },
  { id: "m7", category: "Goals", text: "Wants to be a little more active" },
];

// Milo's opening line on the Chat screen. It is shown, but not sent to the AI.
export const firstGreeting = "Hello! I'm Milo. What would you like to talk about today?";

export const sampleWeather = { summary: "Light rain, clearing later", temperature: 9 };

export const sampleSuggestion =
  "The rain should stop this afternoon. It could be a nice time to spend half an hour in the garden.";
