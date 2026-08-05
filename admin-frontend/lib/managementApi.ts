const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface Overview {
  appointments_total: number;
  appointments_pending: number;
  appointments_confirmed: number;
  appointments_completed: number;
  leads_total: number;
  leads_new: number;
  conversations_total: number;
  messages_total: number;
  notifications_unread: number;
  staff_active: number;
}

export interface Appointment {
  appointment_code: string;
  customer_name: string;
  phone: string;
  appointment_date: string;
  appointment_time: string;
  status: string;
  confirmed_by?: string | null;
  result_note?: string | null;
  created_at: string;
}

export interface Notification {
  appointment_code: string;
  customer_name: string;
  phone: string;
  appointment_date: string;
  appointment_time: string;
  is_read: boolean;
  created_at: string;
}

export interface ManagedLead {
  lead_code: string;
  customer_name: string;
  phone: string;
  source: string;
  status: string;
  assigned_to?: string | null;
  note?: string | null;
  created_at: string;
}

export interface StaffUser {
  full_name: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export interface Conversation {
  session_id: string;
  message_count: number;
  last_intent?: string;
  created_at: string;
  last_active: string;
  booking_step?: string | null;
  latest_message?: { role: string; content: string };
}

export interface ConversationMessage {
  role: string;
  content: string;
  intent?: string;
  created_at: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401) {
      if (typeof window !== "undefined") window.location.href = "/login";
    }
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || "Không thể kết nối hệ thống.");
  }
  return response.json();
}

export const managementApi = {
  overview: () => request<Overview>("/management/overview"),
  appointments: (status?: string) =>
    request<Appointment[]>(
      `/appointments${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  updateAppointment: (
    code: string,
    status: string,
    resultNote?: string,
  ) =>
    request<Appointment>(`/appointments/${code}/status`, {
      method: "PATCH",
      body: JSON.stringify({
        status,
        result_note: resultNote || null,
      }),
    }),
  notifications: (unreadOnly = false) =>
    request<Notification[]>(
      `/notifications${unreadOnly ? "?unread_only=true" : ""}`,
    ),
  markNotificationRead: (code: string) =>
    request(`/notifications/${code}/read`, { method: "PATCH" }),
  leads: () => request<ManagedLead[]>("/management/leads"),
  createLead: (data: {
    customer_name: string;
    phone: string;
    source: string;
    assigned_to?: string;
  }) =>
    request<ManagedLead>("/management/leads", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateLead: (code: string, data: Partial<ManagedLead>) =>
    request<ManagedLead>(`/management/leads/${code}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  conversations: () =>
    request<Conversation[]>("/management/conversations"),
  conversation: (sessionId: string) =>
    request<{ session_id: string; messages: ConversationMessage[] }>(
      `/management/conversations/${encodeURIComponent(sessionId)}`,
    ),
  users: () => request<StaffUser[]>("/management/users"),
  createUser: (data: {
    full_name: string;
    email: string;
    role: string;
    password: string;
  }) =>
    request<StaffUser>("/management/users", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateUser: (email: string, data: Partial<StaffUser>) =>
    request<StaffUser>(`/management/users/${encodeURIComponent(email)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};
