/**
 * Luồng tư vấn của ứng viên, gọi từ trình duyệt.
 *
 * Khác `publicApi.ts` ở chỗ file đó chạy trên máy chủ để dựng sẵn trang đơn hàng,
 * còn file này chạy trong trình duyệt và có trạng thái theo từng người dùng.
 *
 * CV và chat dùng cùng mã hành trình trong journeySession.
 */
import { BACKEND_PUBLIC_URL } from "./publicApi";

export { getSessionId, resetSession } from "./journeySession";

/** Một ô dữ liệu trong hồ sơ. Giá trị nào cũng mang theo nguồn của nó. */
export interface ProfileCell<T = unknown> {
  value: T;
  source: "staff" | "user_confirmed" | "cv" | "chat";
  confidence: number;
  evidence: string | null;
}

export interface CandidateProfile {
  code: string;
  session_id: string;
  status: string;
  version: number;
  fields: Record<string, ProfileCell>;
  preferences: Record<string, ProfileCell>;
  labels: Record<string, string | null>;
  missing_required: string[];
  confirmed_at: string | null;
}

export interface CatalogOption {
  code: string;
  label: string;
}

export interface PrefectureOption extends CatalogOption {
  region_group: string;
}

export interface ProfileMeta {
  japanese_levels: CatalogOption[];
  education_levels: CatalogOption[];
  employer_types: CatalogOption[];
  regions: CatalogOption[];
  prefectures: PrefectureOption[];
  genders: CatalogOption[];
  required_fields: string[];
}

export interface CriterionRow {
  key: string;
  label: string;
  requirement_text: string;
  candidate_text: string;
  result: "DAT" | "KHONG_DAT" | "CHUA_RO";
  missing_field: string | null;
}

export interface SoftRow {
  key: string;
  label: string;
  requirement_text: string;
  candidate_text: string;
  points: number;
  max_points: number;
}

export interface MatchItem {
  code: string;
  title: string;
  employer_name: string;
  prefecture: string;
  employer_type: string;
  program: string;
  deadline: string;
  eligible: boolean;
  score: number;
  rank: number | null;
  hard_rows: CriterionRow[];
  soft_rows: SoftRow[];
  gaps: string[];
  labels: Record<string, string | null>;
  explanation_text: string;
  explanation_block: string;
}

export interface MatchResult {
  log_code: string;
  as_of: string;
  total_considered: number;
  eligible_count: number;
  missing_info: string[];
  matches: MatchItem[];
  disclaimer: string;
  from_cache: boolean;
}

/** Giá trị người dùng gõ vào biểu mẫu, trước khi gửi đi. */
export interface ProfileFormValues {
  full_name?: string;
  birth_year?: number;
  gender?: string;
  education_level?: string;
  major?: string;
  japanese_level?: string;
  experience_years?: number;
  care_experience?: boolean;
  phone?: string;
}

export interface PreferenceFormValues {
  desired_prefecture?: string;
  desired_employer_type?: string;
  salary_expectation_jpy?: number;
  budget_vnd?: number;
  reason?: string;
}

/**
 * Lỗi có thông điệp đọc được. Backend trả `detail` là chuỗi, hoặc là đối tượng
 * khi cần kèm danh sách trường còn thiếu, nên gom cả hai về một chỗ.
 */
export interface CandidateDocument {
  code: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: "received" | "extracted" | "unreadable" | "failed";
  profile_code: string | null;
  extracted_fields: string[];
  /** Trường máy đọc ra nhưng không dám nhận, kèm lý do. */
  rejected: Record<string, string>;
  created_at: string;
}

export interface UploadResult {
  message: string;
  document: CandidateDocument;
  profile: CandidateProfile | null;
  accepted_fields: string[];
  rejected: Record<string, string>;
}

export interface DocumentListing {
  items: CandidateDocument[];
  max_per_session: number;
  accepted_types: string;
  max_upload_mb: number;
}

export interface RegistrationResult {
  message: string;
  application_code: string;
  job_order_code: string;
  job_order_title: string | null;
  status: string;
}

export interface MyRegistration {
  application_code: string;
  job_order_code: string;
  job_order_title: string | null;
  status: string;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  missing: string[];

  constructor(status: number, message: string, missing: string[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.missing = missing;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_PUBLIC_URL}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });
  } catch {
    throw new ApiError(
      0,
      "Không kết nối được máy chủ. Bạn kiểm tra lại mạng rồi thử lần nữa nhé.",
    );
  }

  if (response.ok) {
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  }

  const payload = await response.json().catch(() => null);
  const detail = payload?.detail;
  if (detail && typeof detail === "object") {
    throw new ApiError(
      response.status,
      detail.message ?? "Hồ sơ còn thiếu thông tin.",
      detail.missing ?? [],
    );
  }
  throw new ApiError(
    response.status,
    typeof detail === "string" ? detail : "Có lỗi xảy ra, bạn thử lại giúp em.",
  );
}

/** Bỏ ô trống trước khi gửi: trường vắng mặt nghĩa là chưa rõ, không phải rỗng. */
function clean<T extends object>(values: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(values).filter(
      ([, value]) => value !== undefined && value !== "" && value !== null,
    ),
  ) as Partial<T>;
}

export function fetchProfileMeta(): Promise<ProfileMeta> {
  return request<ProfileMeta>("/public/profiles/meta");
}

export async function fetchProfile(
  sessionId: string,
): Promise<CandidateProfile | null> {
  try {
    return await request<CandidateProfile>(
      `/public/profiles/${encodeURIComponent(sessionId)}`,
    );
  } catch (error) {
    // Chưa có hồ sơ là trạng thái bình thường của người vào lần đầu, không phải lỗi.
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export function createProfile(
  sessionId: string,
  fields: ProfileFormValues,
  preferences: PreferenceFormValues,
): Promise<CandidateProfile> {
  return request<CandidateProfile>("/public/profiles", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      mode: "manual",
      fields: clean(fields),
      preferences: clean(preferences),
    }),
  });
}

export function updateProfile(
  sessionId: string,
  fields: ProfileFormValues,
  preferences: PreferenceFormValues,
  expectedVersion?: number,
): Promise<CandidateProfile> {
  return request<CandidateProfile>(
    `/public/profiles/${encodeURIComponent(sessionId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        fields: clean(fields),
        preferences: clean(preferences),
        ...(expectedVersion ? { expected_version: expectedVersion } : {}),
      }),
    },
  );
}

export function confirmProfile(sessionId: string): Promise<CandidateProfile> {
  return request<CandidateProfile>(
    `/public/profiles/${encodeURIComponent(sessionId)}/confirm`,
    { method: "POST" },
  );
}

export function fetchMatches(
  sessionId: string,
  options: { limit?: number; refresh?: boolean } = {},
): Promise<MatchResult> {
  const params = new URLSearchParams();
  if (options.limit) params.set("limit", String(options.limit));
  if (options.refresh) params.set("refresh", "true");
  const query = params.toString();
  return request<MatchResult>(
    `/public/matches/${encodeURIComponent(sessionId)}${query ? `?${query}` : ""}`,
  );
}


/**
 * Gửi một file hồ sơ.
 *
 * Không đặt `Content-Type`: trình duyệt phải tự sinh header multipart kèm chuỗi
 * phân tách, đặt tay vào là phía máy chủ không tách được file ra khỏi dữ liệu.
 * Vì vậy không dùng lại `request` ở trên — hàm đó luôn gắn `application/json`.
 */
export async function uploadDocument(
  sessionId: string,
  file: File,
): Promise<UploadResult> {
  const body = new FormData();
  body.append("file", file);

  let response: Response;
  try {
    response = await fetch(
      `${BACKEND_PUBLIC_URL}/public/documents/${encodeURIComponent(sessionId)}`,
      { method: "POST", body },
    );
  } catch {
    throw new ApiError(
      0,
      "Không gửi được file. Bạn kiểm tra lại mạng rồi thử lần nữa nhé.",
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      typeof payload?.detail === "string"
        ? payload.detail
        : "Không nhận được file này.",
    );
  }
  return payload as UploadResult;
}

export function fetchDocuments(sessionId: string): Promise<DocumentListing> {
  return request<DocumentListing>(
    `/public/documents/${encodeURIComponent(sessionId)}`,
  );
}

/**
 * Đăng ký một đơn.
 *
 * `confirmed` luôn là `true` ở đây, nhưng vẫn phải gửi lên: phía máy chủ từ chối
 * khi thiếu nó. Giao diện bắt ứng viên bấm xác nhận một lần nữa trước khi gọi
 * hàm này — chọn đơn là quyết định của người, không phải suy đoán của máy.
 */
export function registerForOrder(
  sessionId: string,
  jobOrderCode: string,
): Promise<RegistrationResult> {
  return request<RegistrationResult>(
    `/public/registrations/${encodeURIComponent(sessionId)}`,
    {
      method: "POST",
      body: JSON.stringify({ job_order_code: jobOrderCode, confirmed: true }),
    },
  );
}

export function fetchMyRegistrations(
  sessionId: string,
): Promise<{ items: MyRegistration[] }> {
  return request<{ items: MyRegistration[] }>(
    `/public/registrations/${encodeURIComponent(sessionId)}`,
  );
}

/** Đọc giá trị ra khỏi ô `{value, source}` để đổ ngược vào biểu mẫu. */
export function valueOf<T>(
  section: Record<string, ProfileCell> | undefined,
  key: string,
): T | undefined {
  const cell = section?.[key];
  return cell === undefined ? undefined : (cell.value as T);
}
