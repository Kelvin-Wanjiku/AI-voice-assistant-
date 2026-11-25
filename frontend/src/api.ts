export type PartStatus = "ok" | "not_configured" | "error";

export interface HealthResponse {
  app: string;
  backend: { status: PartStatus };
  database: { status: PartStatus; message: string };
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/health");
  if (!res.ok) {
    throw new Error(`Backend answered with status ${res.status}`);
  }
  return res.json();
}
