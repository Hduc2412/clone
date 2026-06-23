"use client";

import { useState, useRef, useEffect } from "react";
import { sendMessage, Message } from "@/lib/api";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Xin chào! Tôi có thể tư vấn về chương trình điều dưỡng Nhật Bản. Bạn muốn hỏi gì?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendMessage(input, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Xin lỗi, có lỗi kết nối. Vui lòng thử lại." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 text-white shadow"
        style={{ backgroundColor: "#cb1d1e" }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="text-white hover:text-gray-200 text-xl"
          >
            ←
          </button>
          <div>
            <div className="font-bold text-base">Tư vấn điều dưỡng Nhật Bản</div>
            <div className="text-xs text-red-200 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full inline-block" />
              Đang hoạt động
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 max-w-2xl w-full mx-auto">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                msg.role === "user"
                  ? "text-white"
                  : "bg-white text-gray-800 border border-gray-200 shadow-sm"
              }`}
              style={msg.role === "user" ? { backgroundColor: "#cb1d1e" } : {}}
            >
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 px-4 py-2.5 rounded-2xl text-sm text-gray-400 shadow-sm">
              Đang trả lời...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t bg-white px-4 py-3">
        <div className="max-w-2xl mx-auto flex gap-2">
          <input
            className="flex-1 border border-gray-300 rounded-full px-5 py-2.5 text-sm outline-none focus:border-red-400"
            placeholder="Nhập câu hỏi của bạn..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="w-10 h-10 rounded-full text-white flex items-center justify-center disabled:opacity-50 hover:opacity-90"
            style={{ backgroundColor: "#cb1d1e" }}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}