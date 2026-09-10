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

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function statusClass(status: string): string {
  return `status-${status.replaceAll("_", "-")}`;
}
