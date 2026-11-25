// Everything the frontend asks the backend goes through this file.

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
}

/** One line of the conversation, in the shape the backend expects. */
export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`Backend answered with status ${res.status}`);
  return res.json();
}

/** Send the conversation so far and get Milo's reply. Throws an Error whose message is safe to show. */
export async function sendChat(turns: ChatTurn[]): Promise<string> {
  let res: Response;
  try {
    res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: turns }),
    });
  } catch {
    throw new Error("Milo's backend isn't answering. Is it running in the other terminal?");
  }

  if (!res.ok) {
    let detail = `Something went wrong (status ${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // The proxy answers with plain text when the backend is down.
      if (res.status === 500 || res.status === 502 || res.status === 504) {
        detail = "Milo's backend isn't answering. Is it running in the other terminal?";
      }
    }
    throw new Error(detail);
  }

  const data = await res.json();
  return data.reply as string;
}
