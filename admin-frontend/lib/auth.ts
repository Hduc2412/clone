const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface AuthUser {
  full_name: string;
  email: string;
  role: "admin" | "manager" | "consultant";
  status: string;
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
