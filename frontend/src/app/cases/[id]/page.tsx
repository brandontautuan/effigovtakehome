"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  Case,
  CaseEvent,
  fetchCase,
  fetchCaseEvents,
  formatDate,
  statusClass,
  updateCaseStatus,
} from "@/lib/cases";

const REFRESH_INTERVAL_MS = 3_000;
const STATUS_OPTIONS = ["open", "in_progress", "resolved"];

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const [caseItem, setCaseItem] = useState<Case | null>(null);
  const [events, setEvents] = useState<CaseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const loadCase = useCallback(async () => {
    try {
      const [loadedCase, loadedEvents] = await Promise.all([
        fetchCase(params.id),
        fetchCaseEvents(params.id),
      ]);
      setCaseItem(loadedCase);
      setEvents(loadedEvents);
      setError(null);
    } catch {
      setError("Unable to load this case. It may not exist or the API may be unavailable.");
    } finally {
      setIsLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    const initialFetch = window.setTimeout(() => void loadCase(), 0);
    const interval = window.setInterval(() => void loadCase(), REFRESH_INTERVAL_MS);
    return () => {
      window.clearTimeout(initialFetch);
      window.clearInterval(interval);
    };
  }, [loadCase]);

  async function handleStatusChange(status: string) {
    if (!caseItem) return;
    setIsSaving(true);
    try {
      const updatedCase = await updateCaseStatus(caseItem.id, status);
      const updatedEvents = await fetchCaseEvents(String(caseItem.id));
      setCaseItem(updatedCase);
      setEvents(updatedEvents);
      setError(null);
    } catch {
      setError("Unable to update the case status. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) return <main className="page-shell"><p className="state-message">Loading case…</p></main>;
  if (error || !caseItem) {
    return <main className="page-shell"><Link className="back-link" href="/">← All cases</Link><p className="state-message error-message">{error ?? "Case not found."}</p></main>;
  }

  return (
    <main className="page-shell">
      <Link className="back-link" href="/">← All cases</Link>
      <header className="detail-header">
        <div><p className="eyebrow">Case</p><h1>{caseItem.case_number}</h1></div>
        <span className={`status-badge ${statusClass(caseItem.status)}`}>{caseItem.status.replaceAll("_", " ")}</span>
      </header>
      <section className="detail-card">
        <div className="status-control">
          <label htmlFor="case-status">Staff status</label>
          <select id="case-status" value={caseItem.status} disabled={isSaving} onChange={(event) => void handleStatusChange(event.target.value)}>
            {STATUS_OPTIONS.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}
          </select>
        </div>
        <dl className="case-details">
          <Detail label="Resident" value={caseItem.name} />
          <Detail label="Phone" value={caseItem.phone} />
          <Detail label="Issue type" value={caseItem.issue_type.replaceAll("_", " ")} />
          <Detail label="Description" value={caseItem.description} wide />
          <Detail label="Notes" value={caseItem.notes || "No notes yet."} wide />
          <Detail label="Created" value={formatDate(caseItem.created_at)} />
          <Detail label="Last updated" value={formatDate(caseItem.updated_at)} />
        </dl>
      </section>

      <section className="activity-card" aria-labelledby="activity-heading">
        <div className="activity-heading">
          <div>
            <p className="eyebrow">History</p>
            <h2 id="activity-heading">Activity</h2>
          </div>
          <span className="subtle">Refreshes automatically</span>
        </div>
        {events.length === 0 ? (
          <p className="empty-activity">No activity has been recorded for this case yet.</p>
        ) : (
          <ol className="activity-list">
            {events.map((event) => (
              <li key={event.id}>
                <p className="activity-time">{formatDate(event.created_at)}</p>
                <p className="activity-description">{event.description}</p>
                <p className="activity-source">{formatSource(event.source)}</p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}

function Detail({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return <div className={wide ? "detail-row wide" : "detail-row"}><dt>{label}</dt><dd>{value}</dd></div>;
}

function formatSource(source: string): string {
  return source.replaceAll("_", " ");
}
