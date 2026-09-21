const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8020";

export interface Source {
  title: string;
  url: string;
  image?: string;
  score: number;
  topic?: string;
  is_primary?: boolean;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  image?: string;
  sources?: Source[];
}

export interface ChatResponse {
  answer: string;
  session_id: string;
  intent: string;
  sources: Source[];
  /** True khi hệ thống không đủ căn cứ để trả lời và phải dùng câu dự phòng. */
  is_fallback?: boolean;
}

export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) throw new Error("Lỗi kết nối server");
  return res.json();
}
