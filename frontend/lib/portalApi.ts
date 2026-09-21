/**
 * Gọi hệ khách hàng — phần có đăng nhập.
 *
 * Khác `candidateApi.ts` ở chỗ định danh: file kia dùng mã phiên lưu trong
 * trình duyệt cho luồng tư vấn công khai, file này dùng **cookie phiên đăng
 * nhập** do máy chủ đặt. Vì vậy mọi lời gọi ở đây đều phải kèm
 * `credentials: "include"`; thiếu nó thì cookie không được gửi đi và mọi
 * endpoint trả 401 dù vừa đăng nhập xong.
 */

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8020";

export interface PortalAccount {
  phone: string;
  full_name: string | null;
  must_change_password: boolean;
}

export interface PortalApplication {
  application_code: string;
  job_order_code: string | null;
  job_order_title: string | null;
  status: string;
  is_active: boolean;
  destination: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface PortalProfileCell {
  value: unknown;
  source: string;
  evidence: string | null;
}

export interface PortalProfile {
  code: string;
  status: string;
  fields: Record<string, PortalProfileCell>;
  preferences: Record<string, PortalProfileCell>;
  labels: Record<string, string | null>;
}

export interface PortalOverview {
  account: { full_name: string | null; phone: string | null };
  profile: PortalProfile | null;
  applications: PortalApplication[];
}

export class PortalError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "PortalError";
    this.status = status;
  }
}

/**
 * Câu mặc định của pydantic khi dữ liệu vào sai kiểu hoặc thiếu.
 *
 * Chúng là tiếng Anh và nói bằng ngôn ngữ của lập trình viên ("String should
 * have at least 1 character"). Ứng viên đọc được đúng chừng ấy: không hiểu gì,
 * và tệ hơn là thấy một câu tiếng Anh lẫn giữa tiếng Việt thì nghĩ trang web
 * hỏng. Validator của ta thì luôn trả câu tiếng Việt, nên lọc theo dấu tiếng
 * Việt là tách được hai loại.
 */
const HAS_VIETNAMESE = /[àáâãèéêìíòóôõùúýăđĩũơưạ-ỹ]/i;

/**
 * Rút câu tiếng Việt ra khỏi `detail`, kể cả khi nó là mảng lỗi từng trường
 * của FastAPI. Ném thẳng mảng vào `Error` cho ra "[object Object]".
 */
function messageOf(payload: unknown, fallback: string): string {
  const detail = (payload as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const lines = detail
      .map((item) => String(item?.msg ?? "").replace(/^Value error, /, ""))
      .filter((line) => line && HAS_VIETNAMESE.test(line));
    if (lines.length > 0) return lines.join(" ");
  }
  return fallback;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new PortalError(
      response.status,
      messageOf(payload, "Không kết nối được hệ thống. Bạn thử lại nhé."),
    );
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export function login(phone: string, password: string): Promise<PortalAccount> {
  // Chặn ở đây thay vì để máy chủ trả 422: hai ô rỗng là lỗi gõ, và câu trả lời
  // của máy chủ cho trường hợp đó là tiếng Anh của pydantic.
  if (!phone.trim() || !password) {
    return Promise.reject(
      new PortalError(400, "Bạn nhập số điện thoại và mật khẩu nhé."),
    );
  }
  return request<PortalAccount>("/tai-khoan/dang-nhap", {
    method: "POST",
    body: JSON.stringify({ phone: phone.trim(), password }),
  });
}

export function logout(): Promise<{ message: string }> {
  return request<{ message: string }>("/tai-khoan/dang-xuat", { method: "POST" });
}

/** Trả `null` khi chưa đăng nhập, để trang gọi không phải bắt lỗi 401 riêng. */
export async function currentAccount(): Promise<PortalAccount | null> {
  try {
    return await request<PortalAccount>("/tai-khoan/toi");
  } catch (error) {
    if (error instanceof PortalError && error.status === 401) return null;
    throw error;
  }
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<PortalAccount> {
  return request<PortalAccount>("/tai-khoan/doi-mat-khau", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export function fetchOverview(): Promise<PortalOverview> {
  return request<PortalOverview>("/tai-khoan/tong-quan");
}

/** Đọc giá trị ra khỏi ô `{value, source}`. */
export function cellValue<T>(
  section: Record<string, PortalProfileCell> | undefined,
  key: string,
): T | undefined {
  const cell = section?.[key];
  return cell === undefined ? undefined : (cell.value as T);
}
