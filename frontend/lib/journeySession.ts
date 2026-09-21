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

export function resetSession(): string {
  if (typeof window === "undefined") return "";
  window.localStorage.removeItem(KEY);
  window.sessionStorage.removeItem(CHAT_KEY);
  const id = getSessionId();
  window.dispatchEvent(new Event("xkld-journey-reset"));
  return id;
}
