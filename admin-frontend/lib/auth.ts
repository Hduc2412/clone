const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8020";

export interface AuthUser {
  full_name: string;
  email: string;
  role: "admin" | "manager" | "consultant";
  status: string;
  /** Còn nợ đổi mật khẩu: quản trị viên vừa đặt lại về dãy mặc định. */
  must_change_password?: boolean;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail || "Không thể đăng nhập.");
  return payload.user as AuthUser;
}

export async function logout(): Promise<void> {
  await fetch(`${BACKEND_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  }).catch(() => undefined);
}

export async function loadCurrentUser(): Promise<AuthUser> {
  const response = await fetch(`${BACKEND_URL}/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Phiên đăng nhập đã hết hạn.");
  return response.json() as Promise<AuthUser>;
}

/**
 * Đổi mật khẩu. Sau khi quản trị viên đặt lại về dãy mặc định, đây là endpoint
 * duy nhất còn gọi được — mọi màn hình khác bị máy chủ chặn bằng 409 cho tới
 * khi bước này xong.
 */
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/auth/change-password`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      typeof payload?.detail === "string" ? payload.detail : "Không đổi được mật khẩu.",
    );
  }
}

/** Nhân viên quên mật khẩu: gửi yêu cầu lên quản trị viên. */
export async function requestStaffPasswordReset(
  email: string,
  note?: string,
): Promise<string> {
  const response = await fetch(`${BACKEND_URL}/quen-mat-khau/nhan-vien`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim(), note: note?.trim() || null }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      typeof payload?.detail === "string" ? payload.detail : "Không gửi được yêu cầu.",
    );
  }
  return payload?.message || "Đã gửi yêu cầu.";
}
