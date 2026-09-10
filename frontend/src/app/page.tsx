"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Case, fetchCases, formatDate, statusClass } from "@/lib/cases";

const REFRESH_INTERVAL_MS = 3_000;

export default function DashboardPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadCases = useCallback(async () => {
    try {
      setCases(await fetchCases());
      setError(null);
    } catch {
      setError("Unable to load cases. Check that the FastAPI server is running.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialFetch = window.setTimeout(() => void loadCases(), 0);
    const interval = window.setInterval(() => void loadCases(), REFRESH_INTERVAL_MS);
    return () => {
      window.clearTimeout(initialFetch);
      window.clearInterval(interval);
    };
  }, [loadCases]);

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
      {!isLoading && !error && cases.length === 0 ? (
        <p className="state-message">No cases have been reported yet.</p>
      ) : null}

      {!isLoading && !error && cases.length > 0 ? (
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
      ) : null}
    </main>
  );
}
