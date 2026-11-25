import { useCallback, useEffect, useState } from "react";
import { fetchHealth, type HealthResponse, type PartStatus } from "./api";

function greeting(date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

const STATUS_LABEL: Record<PartStatus, string> = {
  ok: "Working",
  not_configured: "Not set up yet",
  error: "Needs attention",
};

const STATUS_SYMBOL: Record<PartStatus, string> = {
  ok: "✓",
  not_configured: "–",
  error: "!",
};

interface RowProps {
  name: string;
  status: PartStatus | "checking";
  detail?: string;
}

function StatusRow({ name, status, detail }: RowProps) {
  const label = status === "checking" ? "Checking…" : STATUS_LABEL[status];
  const symbol = status === "checking" ? "…" : STATUS_SYMBOL[status];
  return (
    <li className={`row row--${status}`}>
      <span className="row__symbol" aria-hidden="true">
        {symbol}
      </span>
      <div>
        <p className="row__name">{name}</p>
        <p className="row__label">{label}</p>
        {detail && <p className="row__detail">{detail}</p>}
      </div>
    </li>
  );
}

export default function App() {
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

  const backendStatus: RowProps["status"] = loading ? "checking" : failed ? "error" : "ok";
  const dbStatus: RowProps["status"] = loading || !health ? (failed ? "error" : "checking") : health.database.status;

  return (
    <main className="page">
      <h1 className="hello">{greeting()}.</h1>
      <p className="intro">Milo is getting ready. Here is what is working so far.</p>

      <ul className="rows" aria-live="polite">
        <StatusRow name="This app" status="ok" />
        <StatusRow
          name="Milo's backend"
          status={backendStatus}
          detail={
            failed
              ? "The backend is not answering. Start it with: uvicorn app.main:app --reload (inside the backend folder)."
              : undefined
          }
        />
        <StatusRow
          name="Memory database"
          status={dbStatus}
          detail={failed ? "Needs the backend first." : health?.database.message}
        />
      </ul>

      <button className="button" onClick={check} disabled={loading}>
        {loading ? "Checking…" : "Check again"}
      </button>
    </main>
  );
}
