"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Call,
  Case,
  callWebSocketUrl,
  fetchCalls,
  fetchCases,
  formatDate,
  statusClass,
} from "@/lib/cases";

const REFRESH_INTERVAL_MS = 3_000;

export default function DashboardPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    try {
      const [loadedCases, loadedCalls] = await Promise.all([fetchCases(), fetchCalls()]);
      setCases(loadedCases);
      setCalls(loadedCalls);
      setError(null);
    } catch {
      setError("Unable to load cases. Check that the FastAPI server is running.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Polling preserves a usable dashboard if the optional WebSocket is down.
    const initialFetch = window.setTimeout(() => void loadDashboard(), 0);
    const interval = window.setInterval(() => void loadDashboard(), REFRESH_INTERVAL_MS);
    return () => {
      window.clearTimeout(initialFetch);
      window.clearInterval(interval);
    };
  }, [loadDashboard]);

  useEffect(() => {
    let socket: WebSocket | undefined;
    let reconnectTimer: number | undefined;
    let isDisposed = false;

    function connect() {
      // A notification contains no case data; reload from FastAPI for consistency.
      socket = new WebSocket(callWebSocketUrl());
      socket.onmessage = () => void loadDashboard();
      socket.onclose = () => {
        if (!isDisposed) reconnectTimer = window.setTimeout(connect, REFRESH_INTERVAL_MS);
      };
    }

    connect();
    return () => {
      isDisposed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [loadDashboard]);

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">EffiGov</p>
          <h1>Case Management</h1>
          <p className="subtle">New cases refresh automatically every three seconds.</p>
        </div>
        <span className="refresh-label">Live API view</span>
      </header>

      {isLoading ? <p className="state-message">Loading cases…</p> : null}
      {error ? <p className="state-message error-message">{error}</p> : null}
      {!isLoading && !error ? (
        <>
          <section className="live-calls" aria-labelledby="live-calls-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Voice operations</p>
                <h2 id="live-calls-heading">Live Calls</h2>
              </div>
              <span className="subtle">WebSocket updates + polling fallback</span>
            </div>
            {calls.length === 0 ? <p className="empty-activity">No calls yet.</p> : (
              <div className="call-grid">
                {calls.slice(0, 6).map((call) => (
                  <Link className="call-card" href={`/calls/${call.id}`} key={call.id}>
                    <span className={call.status === "active" ? "active-dot" : "completed-dot"} />
                    <div>
                      <strong>{call.caller_name ?? "Resident"}</strong>
                      <p>{call.issue_type?.replaceAll("_", " ") ?? "Issue being collected"}</p>
                      <small>{call.status} · {call.case_number ?? "Case pending"}</small>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>
        {cases.length === 0 ? <p className="state-message">No cases have been reported yet.</p> : (
        <section className="table-card" aria-label="Cases">
          <table>
            <thead>
              <tr><th>Case</th><th>Resident</th><th>Issue</th><th>Status</th><th>Created</th></tr>
            </thead>
            <tbody>
              {cases.map((caseItem) => (
                <tr key={caseItem.id}>
                  <td><Link className="case-link" href={`/cases/${caseItem.id}`}>{caseItem.case_number}</Link></td>
                  <td>{caseItem.name}</td>
                  <td>{caseItem.issue_type.replaceAll("_", " ")}</td>
                  <td><span className={`status-badge ${statusClass(caseItem.status)}`}>{caseItem.status.replaceAll("_", " ")}</span></td>
                  <td>{formatDate(caseItem.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        )}
        </>
      ) : null}
    </main>
  );
}
