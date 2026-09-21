"use client";

import { useEffect, useState } from "react";
import { Message, sendMessage } from "@/lib/api";
import { getSessionId } from "@/lib/journeySession";

const STORAGE_KEY = "xkld-chat-state-v1";
const INITIAL_MESSAGES: Message[] = [
  {
    role: "assistant",
    content:
      "Xin chào! Tôi có thể tư vấn về chương trình điều dưỡng Nhật Bản. Bạn muốn hỏi gì?",
  },
];

const INTENT_TO_TOPIC: Record<string, string> = {
  chi_phi: "chi_phi",
  quy_trinh: "quy_trinh",
  lead: "chi_phi",
  phong_van: "phong_van",
  dieu_kien: "dieu_kien",
  luong_thuong: "luong_thuong",
  thoi_gian: "thoi_gian",
  hoc_tap: "hoc_tap",
  ky_tuc_xa: "ky_tuc_xa",
  don_hang: "cong_viec",
  cong_viec: "cong_viec",
};

interface StoredChat {
  messages: Message[];
  sessionId?: string;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      const activeId = getSessionId();
      setSessionId(activeId);
      if (stored) {
        const parsed = JSON.parse(stored) as StoredChat;
        if (parsed.sessionId === activeId && Array.isArray(parsed.messages) && parsed.messages.length > 0) {
          setMessages(parsed.messages);
        }
      }
    } catch {
      sessionStorage.removeItem(STORAGE_KEY);
    } finally {
      setHydrated(true);
    }
  }, []);

  useEffect(() => {
    const reset = () => {
      setSessionId(getSessionId());
      setMessages(INITIAL_MESSAGES);
      setInput("");
    };
    window.addEventListener("xkld-journey-reset", reset);
    const storageReset = (event: StorageEvent) => {
      if (event.key === "xkld-candidate-session" || event.key === null) reset();
    };
    window.addEventListener("storage", storageReset);
    return () => {
      window.removeEventListener("xkld-journey-reset", reset);
      window.removeEventListener("storage", storageReset);
    };
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const state: StoredChat = { messages, sessionId };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [hydrated, messages, sessionId]);

  async function handleSend() {
    const query = input.trim();
    if (!query || loading || !hydrated) return;
    const activeId = getSessionId();

    setMessages((previous) => [
      ...previous,
      { role: "user", content: query },
    ]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendMessage(query, activeId);
      if (getSessionId() !== activeId) return;
      setSessionId(response.session_id);

      const currentTopic = INTENT_TO_TOPIC[response.intent];
      const bestImageSource = [...(response.sources || [])]
        .filter(
          (source) =>
            source.score >= 0.7 &&
            Boolean(source.image) &&
            source.topic === currentTopic
        )
        .sort((first, second) => second.score - first.score)[0];

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: response.answer,
          image: bestImageSource?.image,
          sources: (response.sources || []).slice(0, 3),
        },
      ]);
    } catch {
      if (getSessionId() !== activeId) return;
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: "Xin lỗi, có lỗi kết nối. Vui lòng thử lại.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return {
    messages,
    input,
    setInput,
    loading,
    handleSend,
  };
}
