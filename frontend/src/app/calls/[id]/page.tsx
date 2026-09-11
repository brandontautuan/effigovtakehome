"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  Call,
  CallTopic,
  Case,
  callWebSocketUrl,
  fetchCall,
  fetchCase,
  fetchTranscript,
  fetchCallTopics,
  formatDate,
  TranscriptMessage,
  updateCallTopic,
} from "@/lib/cases";

const REFRESH_INTERVAL_MS = 3_000;

export default function CallDetailPage() {
  const params = useParams<{ id: string }>();
  const [call, setCall] = useState<Call | null>(null);
  const [caseItem, setCaseItem] = useState<Case | null>(null);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [topics, setTopics] = useState<CallTopic[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const transcriptEnd = useRef<HTMLDivElement>(null);

  const loadCall = useCallback(async () => {
    try {
      const [loadedCall, loadedMessages, loadedTopics] = await Promise.all([
        fetchCall(params.id),
        fetchTranscript(params.id),
        fetchCallTopics(params.id),
      ]);
      setCall(loadedCall);
      setMessages(loadedMessages);
      setTopics(loadedTopics);
      setCaseItem(loadedCall.case_id ? await fetchCase(String(loadedCall.case_id)) : null);
      setError(null);
    } catch {
      setError("Unable to load this call. It may not exist or the API may be unavailable.");
    } finally {
      setIsLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    const initialFetch = window.setTimeout(() => void loadCall(), 0);
    const interval = window.setInterval(() => void loadCall(), REFRESH_INTERVAL_MS);
    return () => {
      window.clearTimeout(initialFetch);
      window.clearInterval(interval);
    };
  }, [loadCall]);

  useEffect(() => {
    let socket: WebSocket | undefined;
    let reconnectTimer: number | undefined;
    let isDisposed = false;

    function connect() {
      // Refresh source evidence from the API; the socket only signals a change.
      socket = new WebSocket(callWebSocketUrl());
      socket.onmessage = () => void loadCall();
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
  }, [loadCall]);

  useEffect(() => {
    // Keep an active call readable as finalized messages arrive.
    transcriptEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function saveTopic(topic: CallTopic, updates: Pick<CallTopic, "category" | "topic" | "summary" | "outcome">) {
    try {
      const updatedTopic = await updateCallTopic(topic.id, updates);
      setTopics((currentTopics) => currentTopics.map((item) => item.id === updatedTopic.id ? updatedTopic : item));
      setError(null);
    } catch {
      setError("Unable to update this topic. Please try again.");
    }
  }

  if (isLoading) return <main className="page-shell"><p className="state-message">Loading call…</p></main>;
  if (error || !call) {
    return <main className="page-shell"><Link className="back-link" href="/">← Dashboard</Link><p className="state-message error-message">{error ?? "Call not found."}</p></main>;
  }

  return (
    <main className="page-shell">
      <Link className="back-link" href="/">← Dashboard</Link>
      <header className="detail-header">
        <div><p className="eyebrow">Live call</p><h1>{call.caller_name ?? "Resident call"}</h1></div>
        <span className={call.status === "active" ? "call-status active" : "call-status"}>{call.status}</span>
      </header>

      <div className="call-detail-grid">
        <section className="transcript-card">
          <div className="section-heading"><h2>Transcript</h2><span className="subtle">Finalized messages</span></div>
          {messages.length === 0 ? <p className="empty-activity">Waiting for the conversation to begin.</p> : (
            <div className="transcript-list">
              {messages.map((message) => (
                <article className={`transcript-message ${message.role}`} key={message.id}>
                  <p className="message-role">{message.role === "resident" ? "Resident" : "Agent"}</p>
                  <p>{message.content}</p>
                  <time>{formatDate(message.created_at)}</time>
                </article>
              ))}
              <div ref={transcriptEnd} />
            </div>
          )}
        </section>

        <aside className="extracted-card">
          <p className="eyebrow">Extracted information</p>
          <dl className="extracted-details">
            <Info label="Name" value={call.caller_name ?? "Pending"} />
            <Info label="Phone" value={call.phone ?? "Pending"} />
            <Info label="Issue type" value={call.issue_type?.replaceAll("_", " ") ?? "Pending"} />
            <Info label="Call status" value={call.status} />
            <div className="detail-row">
              <dt>Case</dt>
              <dd>{caseItem ? <Link className="case-link" href={`/cases/${caseItem.id}`}>{caseItem.case_number} · {caseItem.status}</Link> : "Pending"}</dd>
            </div>
            <Info label="Started" value={formatDate(call.started_at)} />
            {call.ended_at ? <Info label="Ended" value={formatDate(call.ended_at)} /> : null}
          </dl>
        </aside>
      </div>

      <section className="activity-card" aria-labelledby="topics-heading">
        <div className="activity-heading">
          <div><p className="eyebrow">Classification</p><h2 id="topics-heading">Call topics</h2></div>
          <span className="subtle">Staff can correct agent classifications</span>
        </div>
        {topics.length === 0 ? <p className="empty-activity">No classified topics yet.</p> : (
          <div className="topic-list">
            {topics.map((topic) => <TopicEditor key={topic.id} topic={topic} onSave={saveTopic} />)}
          </div>
        )}
      </section>
    </main>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="detail-row"><dt>{label}</dt><dd>{value}</dd></div>;
}

function TopicEditor({ topic, onSave }: { topic: CallTopic; onSave: (topic: CallTopic, updates: Pick<CallTopic, "category" | "topic" | "summary" | "outcome">) => Promise<void> }) {
  const [category, setCategory] = useState(topic.category);
  const [topicName, setTopicName] = useState(topic.topic);
  const [summary, setSummary] = useState(topic.summary);
  const [outcome, setOutcome] = useState(topic.outcome);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave() {
    setIsSaving(true);
    await onSave(topic, { category, topic: topicName, summary, outcome });
    setIsSaving(false);
  }

  return <article className="topic-card">
    <div className="topic-controls">
      <label>Category<input value={category} onChange={(event) => setCategory(event.target.value)} /></label>
      <label>Topic<input value={topicName} onChange={(event) => setTopicName(event.target.value)} /></label>
      <label>Outcome<input value={outcome} onChange={(event) => setOutcome(event.target.value)} /></label>
    </div>
    <label className="topic-summary">Summary<textarea value={summary} onChange={(event) => setSummary(event.target.value)} /></label>
    <div className="topic-footer">
      <span>{topic.case_id ? <Link className="case-link" href={`/cases/${topic.case_id}`}>Case #{topic.case_id}</Link> : null}{topic.service_request_id ? ` Handoff #${topic.service_request_id}` : null}{!topic.case_id && !topic.service_request_id ? "No linked record" : null}</span>
      <button type="button" disabled={isSaving} onClick={() => void handleSave()}>{isSaving ? "Saving…" : "Save correction"}</button>
    </div>
  </article>;
}
