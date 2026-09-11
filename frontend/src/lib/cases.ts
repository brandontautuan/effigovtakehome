// This is the dashboard's sole boundary to FastAPI; UI components never read
// SQLite or depend on the LiveKit SDK directly.

export type Case = {
  id: number;
  case_number: string;
  name: string;
  phone: string;
  issue_type: string;
  description: string;
  status: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type CaseEvent = {
  id: number;
  case_id: number;
  event_type: string;
  description: string;
  source: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
};

export type Call = {
  id: number;
  case_id: number | null;
  case_number: string | null;
  status: string;
  caller_name: string | null;
  phone: string | null;
  issue_type: string | null;
  started_at: string;
  ended_at: string | null;
};

export type TranscriptMessage = {
  id: number;
  call_id: number;
  role: "resident" | "agent";
  content: string;
  created_at: string;
};

export type CallTopic = {
  id: number;
  call_id: number;
  category: string;
  topic: string;
  summary: string;
  outcome: string;
  case_id: number | null;
  service_request_id: number | null;
  classification_source: string;
  staff_override: boolean;
  created_at: string;
  updated_at: string;
};

export type ServiceRequest = {
  id: number;
  call_id: number | null;
  description: string;
  destination: string;
  status: string;
  created_at: string;
};

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) throw new Error(`Case API returned ${response.status}`);
  return response.json() as Promise<T>;
}

export function fetchCases(): Promise<Case[]> {
  return request<Case[]>("/cases", { cache: "no-store" });
}

export function fetchCase(id: string): Promise<Case> {
  return request<Case>(`/cases/${id}`, { cache: "no-store" });
}

export function updateCaseStatus(id: number, status: string): Promise<Case> {
  return request<Case>(`/cases/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status, source: "staff_dashboard" }),
  });
}

export function fetchCaseEvents(id: string): Promise<CaseEvent[]> {
  return request<CaseEvent[]>(`/cases/${id}/events`, { cache: "no-store" });
}

export function fetchCalls(): Promise<Call[]> {
  return request<Call[]>("/calls", { cache: "no-store" });
}

export function fetchServiceRequests(): Promise<ServiceRequest[]> {
  return request<ServiceRequest[]>("/service-requests", { cache: "no-store" });
}

export function fetchCall(id: string): Promise<Call> {
  return request<Call>(`/calls/${id}`, { cache: "no-store" });
}

export function fetchTranscript(id: string): Promise<TranscriptMessage[]> {
  return request<TranscriptMessage[]>(`/calls/${id}/transcript`, { cache: "no-store" });
}

export function fetchCallTopics(id: string): Promise<CallTopic[]> {
  return request<CallTopic[]>(`/calls/${id}/topics`, { cache: "no-store" });
}

export function updateCallTopic(
  id: number,
  updates: Pick<CallTopic, "category" | "topic" | "summary" | "outcome">
): Promise<CallTopic> {
  return request<CallTopic>(`/call-topics/${id}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export function callWebSocketUrl(): string {
  // Notifications are refresh hints only. The REST API remains the data source.
  return `${API_URL.replace(/^http/, "ws")}/ws/calls`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function statusClass(status: string): string {
  return `status-${status.replaceAll("_", "-")}`;
}
