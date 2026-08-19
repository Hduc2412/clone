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
  assigned_to?: string | null;
  assigned_name?: string | null;
  assigned_by?: string | null;
  assigned_at?: string | null;
  result_note?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppointmentEvent {
  appointment_code: string;
  action: "created" | "assigned" | "status_changed" | "rescheduled";
  actor_name: string;
  actor_email?: string | null;
  old_status?: string | null;
  new_status?: string | null;
  note?: string | null;
  details: {
    previous_assigned_to?: string | null;
    assigned_to?: string;
    assigned_name?: string;
    previous_date?: string;
    previous_time?: string;
    appointment_date?: string;
    appointment_time?: string;
  };
  created_at: string;
}

export interface AppointmentStats {
  total: number;
  pending: number;
  confirmed: number;
  completed: number;
  unreachable: number;
  cancelled: number;
  confirmation_rate: number;
  completion_rate: number;
  unreachable_rate: number;
  cancellation_rate: number;
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

export interface RecruitmentApplication {
  application_code: string;
  lead_code: string;
  customer_name: string;
  phone: string;
  status: string;
  is_active: boolean;
  assigned_to?: string | null;
  destination?: string | null;
  japanese_level?: string | null;
  qualification?: string | null;
  note?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  action: string;
  outcome: "success" | "failure";
  actor_email?: string | null;
  actor_name?: string | null;
  actor_role?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  ip_address?: string | null;
  details: Record<string, unknown>;
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

export interface CustomerJourneyConversation extends Conversation {
  messages: ConversationMessage[];
}

export interface CustomerJourney {
  lead: ManagedLead;
  applications: RecruitmentApplication[];
  appointments: Appointment[];
  conversations: CustomerJourneyConversation[];
  events: {
    applications: Array<Record<string, unknown>>;
    appointments: AppointmentEvent[];
  };
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
  appointments: (filters?: {
    status?: string;
    dateFrom?: string;
    dateTo?: string;
    assignedTo?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters?.dateTo) params.set("date_to", filters.dateTo);
    if (filters?.assignedTo) params.set("assigned_to", filters.assignedTo);
    const query = params.toString();
    return request<Appointment[]>(`/appointments${query ? `?${query}` : ""}`);
  },
  appointmentStats: (filters?: {
    dateFrom?: string;
    dateTo?: string;
    assignedTo?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters?.dateTo) params.set("date_to", filters.dateTo);
    if (filters?.assignedTo) params.set("assigned_to", filters.assignedTo);
    const query = params.toString();
    return request<AppointmentStats>(`/appointments/stats${query ? `?${query}` : ""}`);
  },
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
  appointmentAssignees: () =>
    request<StaffUser[]>("/appointments/assignees"),
  assignAppointment: (code: string, assignedTo: string) =>
    request<Appointment>(`/appointments/${code}/assignment`, {
      method: "PATCH",
      body: JSON.stringify({ assigned_to: assignedTo }),
    }),
  appointmentEvents: (code: string) =>
    request<AppointmentEvent[]>(`/appointments/${code}/events`),
  rescheduleAppointment: (
    code: string,
    appointmentDate: string,
    appointmentTime: string,
    note?: string,
  ) =>
    request<Appointment>(`/appointments/${code}/reschedule`, {
      method: "PATCH",
      body: JSON.stringify({
        appointment_date: appointmentDate,
        appointment_time: appointmentTime,
        note: note || null,
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
  customerJourney: (code: string) =>
    request<CustomerJourney>(
      `/management/leads/${encodeURIComponent(code)}/journey`,
    ),
  applications: (filters?: { status?: string; activeOnly?: boolean }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.activeOnly) params.set("active_only", "true");
    const query = params.toString();
    return request<RecruitmentApplication[]>(`/applications${query ? `?${query}` : ""}`);
  },
  createApplication: (data: {
    lead_code: string;
    assigned_to?: string;
    destination?: string;
    japanese_level?: string;
    qualification?: string;
    note?: string;
  }) =>
    request<RecruitmentApplication>("/applications", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateApplication: (code: string, data: Partial<RecruitmentApplication>) =>
    request<RecruitmentApplication>(`/applications/${code}`, {
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
  auditLogs: (filters?: {
    actorEmail?: string;
    action?: string;
    outcome?: string;
    dateFrom?: string;
    dateTo?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.actorEmail) params.set("actor_email", filters.actorEmail);
    if (filters?.action) params.set("action", filters.action);
    if (filters?.outcome) params.set("outcome", filters.outcome);
    if (filters?.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters?.dateTo) params.set("date_to", filters.dateTo);
    const query = params.toString();
    return request<AuditLog[]>(`/audit-logs${query ? `?${query}` : ""}`);
  },
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
