// The Phase 1 health check, moved to the bottom of the About me screen.

import { useCallback, useEffect, useState } from "react";
import { fetchHealth, type HealthResponse, type PartStatus } from "../api";

const LABEL: Record<PartStatus, string> = {
  ok: "Working",
  not_configured: "Not set up yet",
  error: "Needs attention",
};

export default function AppStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);

  const check = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    try {
      setHealth(await fetchHealth());
    } catch {
      setHealth(null);
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  const backend = loading ? "Checking…" : failed ? "Needs attention: start the backend" : "Working";
  const ai = loading
    ? "Checking…"
    : failed || !health
      ? "Needs the backend first"
      : `${LABEL[health.ai.status]}${health.ai.message ? ` (${health.ai.message})` : ""}`;
  const search = loading
    ? "Checking…"
    : failed || !health
      ? "Needs the backend first"
      : health.web_search.status === "ok"
        ? "Working"
        : `Not set up yet: ${health.web_search.message}`;
  const database = loading
    ? "Checking…"
    : failed || !health
      ? "Needs the backend first"
      : `${LABEL[health.database.status]}${health.database.status === "ok" ? "" : `: ${health.database.message}`}`;

  return (
    <details className="status">
      <summary>Is everything working?</summary>
      <ul aria-live="polite">
        <li><strong>This app:</strong> Working</li>
        <li><strong>Milo's backend:</strong> {backend}</li>
        <li><strong>Milo's brain (AI):</strong> {ai}</li>
        <li><strong>Memory database:</strong> {database}</li>
        <li><strong>Web search:</strong> {search}</li>
      </ul>
      <button className="button button--quiet" onClick={check} disabled={loading}>
        {loading ? "Checking…" : "Check again"}
      </button>
    </details>
  );
}
