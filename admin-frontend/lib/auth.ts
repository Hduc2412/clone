const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const TOKEN_KEY = "xkld_admin_token";
const USER_KEY = "xkld_admin_user";

export interface AuthUser {
  full_name: string;
  email: string;
  role: "admin" | "manager" | "consultant";
  status: string;
}

export function getToken() {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(USER_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export async function login(email: string, password: string) {
  const response = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail || "Không thể đăng nhập.");
  window.localStorage.setItem(TOKEN_KEY, payload.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
  return payload.user as AuthUser;
}

export async function loadCurrentUser(): Promise<AuthUser> {
  const token = getToken();
  if (!token) throw new Error("Bạn chưa đăng nhập.");
  const response = await fetch(`${BACKEND_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    clearAuth();
    throw new Error("Phiên đăng nhập đã hết hạn.");
  }
  const user = (await response.json()) as AuthUser;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}
