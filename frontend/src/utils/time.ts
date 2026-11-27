export function greeting(date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

/** "Wednesday 25 November" */
export function longDate(date = new Date()): string {
  return date.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}

/** "14:30" -> "14:30" or "2:30 PM", depending on the computer's settings */
export function displayTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** The current time as "HH:MM", for comparing with plan times */
export function nowHHMM(date = new Date()): string {
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

/** A date as "YYYY-MM-DD" in local time (not UTC, which can be a different day late in the evening). */
export function isoDate(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/** "YYYY-MM-DD" -> a Date at local midnight. */
export function fromIso(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function addDays(iso: string, days: number): string {
  const d = fromIso(iso);
  d.setDate(d.getDate() + days);
  return isoDate(d);
}

/** "Today", "Tomorrow", "Yesterday", or "Friday 27 November". */
export function dayLabel(iso: string, today = isoDate()): string {
  if (iso === today) return "Today";
  if (iso === addDays(today, 1)) return "Tomorrow";
  if (iso === addDays(today, -1)) return "Yesterday";
  return longDate(fromIso(iso));
}

/** "every day" / "every Friday" for repeating plans. */
export function repeatLabel(repeat: string, startsOn: string): string {
  if (repeat === "daily") return "Every day";
  if (repeat === "weekly") return `Every ${fromIso(startsOn).toLocaleDateString("en-GB", { weekday: "long" })}`;
  return "";
}

export function reminderLabel(minutes: number | null): string {
  if (minutes === null) return "No reminder";
  if (minutes === 0) return "Reminder at the time";
  if (minutes % 60 === 0) return `Reminder ${minutes / 60} hour${minutes === 60 ? "" : "s"} before`;
  return `Reminder ${minutes} minutes before`;
}
