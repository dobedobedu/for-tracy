const API_BASE = import.meta.env.VITE_API_URL || "/api";

export interface Upload {
  id: number;
  filename: string;
  report_date: string;
  row_count_raw: number;
  row_count_after_scope: number;
  uploaded_at: string;
}

export interface Transition {
  record_number: string;
  address: string;
  from_status: string;
  to_status: string;
}

export interface CompareResult {
  from_report: { date: string; filename: string };
  to_report: { date: string; filename: string };
  transitions: Transition[];
  summary: { from: string; to: string; count: number }[];
}

export interface Community {
  name: string;
  count: number;
  permits: {
    record_number: string;
    address: string;
    current_status: string;
    current_milestone: string;
  }[];
}

export interface KanbanColumn {
  milestone: string;
  permits: Permit[];
}

export interface Permit {
  record_number: string;
  address: string;
  current_status: string;
  current_milestone: string;
  changed: boolean;
  change_info?: {
    from_status: string;
    to_status: string;
    is_backward: boolean;
    is_tracked_milestone: boolean;
  };
}

export async function uploadCSV(file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getUploads(): Promise<Upload[]> {
  const res = await fetch(`${API_BASE}/uploads`);
  const data = await res.json();
  return data.uploads;
}

export async function getCalendar(): Promise<{ date: string; uploads: number; permits_observed: number }[]> {
  const res = await fetch(`${API_BASE}/calendar`);
  const data = await res.json();
  return data.activity;
}

export async function getCompare(fromDate: string, toDate: string): Promise<CompareResult> {
  const res = await fetch(`${API_BASE}/compare?from_date=${encodeURIComponent(fromDate)}&to_date=${encodeURIComponent(toDate)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getKanban(communities?: string[], reportDate?: string): Promise<{ columns: KanbanColumn[]; latest_upload?: { filename: string; report_date: string } }> {
  const params = new URLSearchParams();
  if (communities && communities.length > 0) params.append("community", communities.join(","));
  if (reportDate) params.append("report_date", reportDate);
  const res = await fetch(`${API_BASE}/kanban?${params.toString()}`);
  return res.json();
}

export async function getCommunities(onlyChanged?: boolean, fromDate?: string, toDate?: string): Promise<Community[]> {
  const params = new URLSearchParams();
  if (onlyChanged) params.append("only_changed", "true");
  if (fromDate) params.append("from_date", fromDate);
  if (toDate) params.append("to_date", toDate);
  const res = await fetch(`${API_BASE}/communities?${params.toString()}`);
  const data = await res.json();
  return data.communities;
}

export async function getTimeline(recordNumber: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/permits/${recordNumber}/timeline`);
  const data = await res.json();
  return data.timeline;
}
