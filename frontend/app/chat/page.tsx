"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import ChatMessage from "@/components/ChatMessage";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const { messages, input, setInput, loading, handleSend } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div
        className="flex items-center justify-between px-6 py-4 text-white shadow"
        style={{ backgroundColor: "#cb1d1e" }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            aria-label="Quay lại"
            className="text-white hover:text-gray-200 text-xl"
          >
            ←
          </button>
          <div>
            <div className="font-bold text-base">
              Tư vấn điều dưỡng Nhật Bản
            </div>
            <div className="text-xs text-red-200 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full inline-block" />
              Đang hoạt động
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 max-w-2xl w-full mx-auto">
        {messages.map((message, index) => (
          <ChatMessage
            key={`${message.role}-${index}`}
            message={message}
          />
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

      <div className="border-t bg-white px-4 py-3">
        <div className="max-w-2xl mx-auto flex gap-2">
          <input
            className="flex-1 border border-gray-300 rounded-full px-5 py-2.5 text-sm outline-none focus:border-red-400"
            placeholder="Nhập câu hỏi của bạn..."
            aria-label="Câu hỏi tư vấn"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            aria-label="Gửi câu hỏi"
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
