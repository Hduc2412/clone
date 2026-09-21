/** One anonymous journey for chat and CV. Never merge two existing identities. */
const KEY = "xkld-candidate-session";
const CHAT_KEY = "xkld-chat-state-v1";
const UUID = /^(?:[a-f0-9]{32}|[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})$/i;

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  const existing = window.localStorage.getItem(KEY);
  if (existing && UUID.test(existing)) return existing;
  // Preserve a legacy chat identity only when no candidate identity exists.
  let legacy: string | undefined;
  if (!existing) {
    try {
      legacy = JSON.parse(window.sessionStorage.getItem(CHAT_KEY) || "null")?.sessionId;
    } catch { /* Corrupt local chat state is not an identity. */ }
  }
  const id = legacy && UUID.test(legacy) ? legacy : crypto.randomUUID();
  window.localStorage.setItem(KEY, id);
  return id;
}

/**
 * Đọc mã phiên đang có mà **không** tạo mới.
 *
 * Trang theo dõi hồ sơ cần phân biệt "chưa từng dùng trên máy này" với "đã có
 * hồ sơ". `getSessionId` luôn sinh một mã mới khi chưa có, nên dùng nó ở trang
 * tra cứu sẽ khiến mọi khách lạ trông như vừa có phiên rỗng. Hàm này trả chuỗi
 * rỗng khi thật sự chưa có gì.
 */
export function peekSessionId(): string {
  if (typeof window === "undefined") return "";
  const existing = window.localStorage.getItem(KEY);
  return existing && UUID.test(existing) ? existing : "";
}

export function resetSession(): string {
  if (typeof window === "undefined") return "";
  window.localStorage.removeItem(KEY);
  window.sessionStorage.removeItem(CHAT_KEY);
  const id = getSessionId();
  window.dispatchEvent(new Event("xkld-journey-reset"));
  return id;
}
