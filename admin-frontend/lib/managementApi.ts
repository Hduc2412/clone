const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8020";

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

/** Nhãn tiếng Việt do backend trả kèm, để giao diện không giữ bản sao bảng danh mục. */
export interface JobOrderLabels {
  status: string | null;
  employer_type: string | null;
  program: string | null;
  region_group: string | null;
  japanese_required: string | null;
  education_required: string | null;
  gender_pref: string | null;
}

/** Điều kiện bắt buộc — dùng để loại ứng viên khi đối chiếu. */
export interface JobOrderRequirements {
  japanese_required: string;
  education_required: string | null;
  experience_min: number;
  age_min: number | null;
  age_max: number | null;
  gender_pref: string;
}

/** Thông tin tham khảo — chỉ để hiển thị và xếp hạng, không loại ai. */
export interface JobOrderReference {
  salary_min: number | null;
  salary_max: number | null;
  allowances: string[];
  cost_total_vnd: number | null;
  interview_date: string | null;
  departure_expected: string | null;
  highlights: string[];
}

export interface JobOrder {
  code: string;
  title: string;
  employer_name: string;
  employer_type: string;
  program: string;
  prefecture: string;
  region_group: string | null;
  city: string | null;
  quota: number;
  hired_count: number;
  deadline: string;
  requirements: JobOrderRequirements;
  reference: JobOrderReference;
  description: string | null;
  internal_note: string | null;
  status: string;
  published: boolean;
  labels: JobOrderLabels;
  visible_publicly?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CatalogOption {
  code: string;
  label: string;
}

export interface PrefectureOption extends CatalogOption {
  region_group: string;
}

export interface JobOrderMeta {
  employer_types: CatalogOption[];
  programs: CatalogOption[];
  japanese_levels: CatalogOption[];
  education_levels: CatalogOption[];
  gender_prefs: CatalogOption[];
  statuses: CatalogOption[];
  transitions: Record<string, string[]>;
  regions: CatalogOption[];
  prefectures: PrefectureOption[];
}

export interface JobOrderEvent {
  job_order_code: string;
  action: string;
  actor_email: string | null;
  actor_name: string | null;
  old_status: string | null;
  new_status: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface JobOrderImportRow {
  row_number: number;
  action: "create" | "update" | "error";
  code: string | null;
  title: string | null;
  errors: string[];
  data: Record<string, unknown>;
}

export interface JobOrderImportResult {
  summary: { total: number; create: number; update: number; error: number };
  missing_columns: string[];
  rows: JobOrderImportRow[];
  dry_run: boolean;
  applied?: {
    created: number;
    updated: number;
    failed: { row_number: number; reason: string }[];
  };
}

// --- Hồ sơ ứng viên ---

/**
 * Một ô dữ liệu trong hồ sơ. Mỗi giá trị đi kèm nguồn của nó, nên màn hình luôn
 * nói được "con số này ở đâu ra" thay vì hiện một con số trần.
 */
export interface ProfileCell<T = unknown> {
  value: T;
  source: "staff" | "user_confirmed" | "cv" | "chat";
  confidence: number;
  evidence: string | null;
}

export interface CandidateProfile {
  consultation_profile?: {
    recent_messages?: { content: string; intent: string; recorded_at: string }[];
    conflicts?: { field: string; previous: unknown; suggested: unknown; evidence: string }[];
  };
  code: string;
  session_id: string;
  status: string;
  version: number;
  fields: Record<string, ProfileCell>;
  preferences: Record<string, ProfileCell>;
  assigned_to: string | null;
  lead_code: string | null;
  confirmed_at: string | null;
  labels: Record<string, string | null>;
  missing_required: string[];
  created_at: string;
  updated_at: string;
}

/** Danh mục cho biểu mẫu sửa hồ sơ. Cùng nguồn với biểu mẫu của ứng viên. */
export interface CandidateProfileMeta {
  japanese_levels: CatalogOption[];
  education_levels: CatalogOption[];
  employer_types: CatalogOption[];
  regions: CatalogOption[];
  prefectures: PrefectureOption[];
  genders: CatalogOption[];
  required_fields: string[];
}

export interface CandidateProfilePatch {
  fields?: Record<string, unknown>;
  preferences?: Record<string, unknown>;
  expected_version: number;
}

export interface CandidateDocument {
  code: string;
  session_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  page_count: number;
  status: "received" | "extracted" | "unreadable" | "failed";
  profile_code: string | null;
  extracted_fields: string[];
  /** Trường máy đọc ra nhưng hệ thống không dám nhận, kèm lý do. */
  rejected: Record<string, string>;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface QueuedRegistration {
  application_code: string;
  lead_code: string;
  customer_name: string;
  phone: string;
  status: string;
  assigned_to: string | null;
  job_order_code: string;
  job_order_title: string | null;
  match_score: number | null;
  profile_code: string;
  report_code: string | null;
  japanese_level: string | null;
  destination: string | null;
  created_at: string;
}

export interface ConsultationReport {
  code: string;
  application_code: string;
  profile_code: string;
  job_order_code: string;
  /** Phiếu dạng chữ thuần — nhân viên đọc thẳng hoặc dán vào tin nhắn nội bộ. */
  text: string;
  gaps: string[];
  missing_info: string[];
  created_at: string;
}

export interface ScoreRule {
  action: string;
  points: number;
  label: string;
}

export interface ScoreTotal {
  staff_email: string;
  points: number;
  events: number;
  last_at: string;
}

export interface ScoreEvent {
  code: string;
  staff_email: string;
  action: string;
  label: string;
  points: number;
  reference_type: string;
  reference_code: string | null;
  source: "auto" | "manual";
  note: string | null;
  created_by: string | null;
  occurred_at: string;
}

export interface ScoreBreakdown {
  action: string;
  label: string;
  points: number;
  events: number;
}

export interface StaffLedger {
  staff_email: string;
  points: number;
  events: ScoreEvent[];
  breakdown: ScoreBreakdown[];
}

// --- Nhật ký giới thiệu ---

export interface CriterionRow {
  key: string;
  label: string;
  requirement_text: string;
  candidate_text: string;
  result: "DAT" | "KHONG_DAT" | "CHUA_RO";
  missing_field: string | null;
  kind: "cung";
}

export interface SoftRow {
  key: string;
  label: string;
  requirement_text: string;
  candidate_text: string;
  outcome: string;
  points: number;
  max_points: number;
  missing_field: string | null;
  kind: "mem";
}

export interface MatchItem {
  code: string;
  title: string;
  employer_name: string;
  prefecture: string;
  region_group: string | null;
  employer_type: string;
  program: string;
  deadline: string;
  eligible: boolean;
  score: number;
  rank: number | null;
  hard_rows: CriterionRow[];
  soft_rows: SoftRow[];
  gaps: string[];
  missing_info: string[];
  labels: Record<string, string | null>;
}

/** Bản tóm tắt dùng cho danh sách. Không kéo theo `items`. */
export interface RecommendationLogSummary {
  code: string;
  profile_code: string;
  profile_version: number;
  session_id: string | null;
  assigned_to: string | null;
  as_of: string;
  total_considered: number;
  eligible_count: number;
  top_codes: string[];
  trigger: string;
  actor_email: string | null;
  engine_version: string;
  weights_version: string;
  orders_fingerprint: string;
  weights_fingerprint: string;
  created_at: string;
}

export interface RecommendationLog extends RecommendationLogSummary {
  pool_query: Record<string, unknown>;
  missing_info: string[];
  items: MatchItem[];
  application_code: string | null;
}

/**
 * Rút một câu tiếng Việt đọc được ra khỏi phần `detail` của máy chủ.
 *
 * FastAPI trả `detail` ở ba hình dạng: chuỗi (lỗi ta tự ném), **mảng** lỗi từng
 * trường khi dữ liệu vào không hợp lệ (422), và đôi khi là đối tượng có khóa
 * `message`. Ném thẳng hai dạng sau vào `new Error` cho ra "[object Object]" —
 * người nhập liệu thấy đúng chừng ấy và không biết ô nào sai.
 */
function detailMessage(payload: unknown, fallback: string): string {
  const detail = (payload as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const lines = detail
      .map((item) => {
        const where = Array.isArray(item?.loc)
          ? item.loc.filter((part: unknown) => part !== "body").join(" › ")
          : "";
        const what = String(item?.msg ?? "").replace(/^Value error, /, "");
        if (!what) return "";
        return where ? `${where}: ${what}` : what;
      })
      .filter(Boolean);
    if (lines.length > 0) return lines.join("; ");
  }

  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return fallback;
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
    throw new Error(detailMessage(payload, "Không thể kết nối hệ thống."));
  }
  return response.json();
}

/**
 * Gửi biểu mẫu có file. Khác `request` ở chỗ **không** đặt `Content-Type`:
 * trình duyệt phải tự sinh header multipart kèm chuỗi phân tách, đặt tay vào là
 * phía máy chủ không tách được file ra khỏi phần dữ liệu.
 */
async function requestForm<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    body,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      window.location.href = "/login";
    }
    const payload = await response.json().catch(() => null);
    throw new Error(detailMessage(payload, "Không thể tải file lên hệ thống."));
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

  // --- Đơn tuyển dụng ---
  jobOrders: (filters?: {
    status?: string;
    published?: boolean;
    program?: string;
    employerType?: string;
    prefecture?: string;
    regionGroup?: string;
    japaneseRequired?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.published !== undefined) {
      params.set("published", String(filters.published));
    }
    if (filters?.program) params.set("program", filters.program);
    if (filters?.employerType) params.set("employer_type", filters.employerType);
    if (filters?.prefecture) params.set("prefecture", filters.prefecture);
    if (filters?.regionGroup) params.set("region_group", filters.regionGroup);
    if (filters?.japaneseRequired) {
      params.set("japanese_required", filters.japaneseRequired);
    }
    const query = params.toString();
    return request<JobOrder[]>(`/job-orders${query ? `?${query}` : ""}`);
  },
  jobOrder: (code: string) =>
    request<JobOrder>(`/job-orders/${encodeURIComponent(code)}`),
  jobOrderMeta: () => request<JobOrderMeta>("/job-orders/meta"),
  jobOrderEvents: (code: string) =>
    request<JobOrderEvent[]>(`/job-orders/${encodeURIComponent(code)}/events`),
  createJobOrder: (data: Record<string, unknown>) =>
    request<JobOrder>("/job-orders", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateJobOrder: (code: string, data: Record<string, unknown>) =>
    request<JobOrder>(`/job-orders/${encodeURIComponent(code)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  setJobOrderStatus: (code: string, status: string, note?: string) =>
    request<JobOrder>(`/job-orders/${encodeURIComponent(code)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, note: note || null }),
    }),
  setJobOrderPublished: (code: string, published: boolean) =>
    request<JobOrder>(`/job-orders/${encodeURIComponent(code)}/publish`, {
      method: "PATCH",
      body: JSON.stringify({ published }),
    }),
  deleteJobOrder: (code: string) =>
    request<void>(`/job-orders/${encodeURIComponent(code)}`, {
      method: "DELETE",
    }),
  importJobOrders: (file: File, dryRun: boolean) => {
    const body = new FormData();
    body.append("file", file);
    return requestForm<JobOrderImportResult>(
      `/job-orders/import?dry_run=${dryRun}`,
      body,
    );
  },
  jobOrderTemplateUrl: () => `${BACKEND_URL}/job-orders/import/template`,

  // --- Hồ sơ ứng viên ---
  candidateProfiles: (filters?: {
    status?: string;
    assignedTo?: string;
    leadCode?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.assignedTo) params.set("assigned_to", filters.assignedTo);
    if (filters?.leadCode) params.set("lead_code", filters.leadCode);
    const query = params.toString();
    return request<CandidateProfile[]>(`/profiles${query ? `?${query}` : ""}`);
  },
  candidateProfile: (code: string) =>
    request<CandidateProfile>(`/profiles/${encodeURIComponent(code)}`),
  candidateProfileMeta: () => request<CandidateProfileMeta>("/profiles/meta"),
  /**
   * Sửa hồ sơ. `expected_version` là bắt buộc chứ không tùy chọn: hai nhân viên
   * mở cùng một hồ sơ là chuyện thường, và không có nó thì người lưu sau lặng
   * lẽ xóa mất phần người lưu trước vừa sửa. Sai phiên bản thì máy chủ trả 409.
   */
  updateCandidateProfile: (code: string, patch: CandidateProfilePatch) =>
    request<CandidateProfile>(`/profiles/${encodeURIComponent(code)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  assignCandidateProfile: (code: string, assignedTo: string | null) =>
    request<CandidateProfile>(`/profiles/${encodeURIComponent(code)}/assignment`, {
      method: "PATCH",
      body: JSON.stringify({ assigned_to: assignedTo }),
    }),

  /**
   * Tài liệu chưa gắn được vào hồ sơ nào (ảnh chụp, bản scan, đọc hỏng) chỉ tra
   * được qua đường này — chúng không thuộc hồ sơ nào nên không hiện ở đâu khác.
   */
  documents: (status?: string) => {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<{ items: CandidateDocument[] }>(`/documents${query}`).then(
      (payload) => payload.items,
    );
  },
  documentStats: () =>
    request<{
      by_status: Record<string, number>;
      images: number;
      total: number;
    }>("/documents/stats"),
  profileDocuments: (profileCode: string) =>
    request<{ items: CandidateDocument[] }>(
      `/documents/profile/${encodeURIComponent(profileCode)}`,
    ).then((payload) => payload.items),
  documentText: (code: string) =>
    request<{ code: string; text: string }>(
      `/documents/${encodeURIComponent(code)}/text`,
    ),
  /**
   * Đường tải bản gốc. Trả về chuỗi thay vì gọi `fetch`: trình duyệt phải tự mở
   * đường này thì mới nhận được file kèm tên gốc, và cookie phiên đi theo sẵn.
   */
  documentOriginalUrl: (code: string) =>
    `${BACKEND_URL}/documents/${encodeURIComponent(code)}/original`,

  // --- Hàng đợi đăng ký sơ bộ ---
  registrationQueue: () =>
    request<{ items: QueuedRegistration[]; count: number }>("/registrations/queue"),
  acceptRegistration: (code: string) =>
    request<QueuedRegistration>(
      `/registrations/${encodeURIComponent(code)}/accept`,
      { method: "POST" },
    ),
  registrationReport: (code: string) =>
    request<ConsultationReport>(
      `/registrations/${encodeURIComponent(code)}/report`,
    ),
  myRegistrations: () =>
    request<{ items: QueuedRegistration[] }>("/registrations/mine").then(
      (payload) => payload.items,
    ),
  handoverRegistration: (code: string, assignedTo: string, note: string) =>
    request<QueuedRegistration>(
      `/registrations/${encodeURIComponent(code)}/handover`,
      { method: "POST", body: JSON.stringify({ assigned_to: assignedTo, note }) },
    ),
  releaseRegistration: (code: string, note: string) =>
    request<QueuedRegistration>(
      `/registrations/${encodeURIComponent(code)}/release`,
      { method: "POST", body: JSON.stringify({ note }) },
    ),

  // --- Điểm hiệu suất nhân viên ---
  scoreboard: (range?: { dateFrom?: string; dateTo?: string }) => {
    const params = new URLSearchParams();
    if (range?.dateFrom) params.set("date_from", range.dateFrom);
    if (range?.dateTo) params.set("date_to", range.dateTo);
    const query = params.toString();
    return request<{ items: ScoreTotal[]; rules: ScoreRule[] }>(
      `/staff-scores${query ? `?${query}` : ""}`,
    );
  },
  staffLedger: (email: string, range?: { dateFrom?: string; dateTo?: string }) => {
    const params = new URLSearchParams();
    if (range?.dateFrom) params.set("date_from", range.dateFrom);
    if (range?.dateTo) params.set("date_to", range.dateTo);
    const query = params.toString();
    return request<StaffLedger>(
      `/staff-scores/${encodeURIComponent(email)}${query ? `?${query}` : ""}`,
    );
  },
  adjustScore: (email: string, points: number, note: string) =>
    request<ScoreEvent>(`/staff-scores/${encodeURIComponent(email)}/adjust`, {
      method: "POST",
      body: JSON.stringify({ points, note }),
    }),

  // --- Nhật ký giới thiệu ---
  recommendationLogs: (filters?: {
    profileCode?: string;
    sessionId?: string;
    trigger?: string;
    dateFrom?: string;
    dateTo?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.profileCode) params.set("profile_code", filters.profileCode);
    if (filters?.sessionId) params.set("session_id", filters.sessionId);
    if (filters?.trigger) params.set("trigger", filters.trigger);
    if (filters?.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters?.dateTo) params.set("date_to", filters.dateTo);
    const query = params.toString();
    return request<RecommendationLogSummary[]>(
      `/recommendation-logs${query ? `?${query}` : ""}`,
    );
  },
  recommendationLog: (code: string) =>
    request<RecommendationLog>(`/recommendation-logs/${encodeURIComponent(code)}`),
  latestRecommendationLog: (profileCode: string) =>
    request<RecommendationLog>(
      `/recommendation-logs/profile/${encodeURIComponent(profileCode)}/latest`,
    ),
  rerunMatching: (profileCode: string) =>
    request<RecommendationLog>("/recommendation-logs/rerun", {
      method: "POST",
      body: JSON.stringify({ profile_code: profileCode }),
    }),
};
