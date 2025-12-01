export const API_BASE = process.env.API_BASE || "http://127.0.0.1:8000"; // replace with your machine LAN IP when testing on device

export type PrescriptionListEntry = {
  medication: {
    id: number;
    user_id: number;
    drug_name: string;
    dosage: string;
    frequency?: number;
    message?: string | null;
  };
  schedule: { id: number; start_date: string; end_date?: string | null; next_reminder?: string | null } | null;
  reminder_count: number;
};

export type ReminderEntry = {
  trigger_time: string;
  med_name: string;
  dosage?: string;
  message?: string | null;
  reminder_id?: number;
};

async function handleResponse(res: Response) {
  const text = await res.text();
  let body: any = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch (err) {
    body = text;
  }

  if (!res.ok) {
    const detail = body?.detail ?? body ?? `HTTP ${res.status}`;
    const message = Array.isArray(detail) ? detail.map((d: any) => d.msg ?? JSON.stringify(d)).join("; ") : String(detail);
    throw { status: res.status, body, message };
  }
  return body;
}

export async function getPrescriptions(user_id?: number): Promise<PrescriptionListEntry[]> {
  const params = user_id ? `/${encodeURIComponent(String(user_id))}` : "";
  const res = await fetch(`${API_BASE}/prescriptions${params}`, { method: "GET" });
  return handleResponse(res);
}

export async function createPrescription(payload: any) {
  const res = await fetch(`${API_BASE}/prescriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function updatePrescription(med_id: number, payload: any) {
  const res = await fetch(`${API_BASE}/prescriptions/${med_id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function deletePrescription(med_id: number) {
  const res = await fetch(`${API_BASE}/prescriptions/${med_id}`, { method: "DELETE" });
  if (!res.ok) throw { status: res.status };
  return null;
}

export async function getRemindersForUser(user_id: number): Promise<ReminderEntry[]> {
  const res = await fetch(`${API_BASE}/reminders/${encodeURIComponent(String(user_id))}`, { method: "GET" });
  return handleResponse(res) as Promise<ReminderEntry[]>;
}
