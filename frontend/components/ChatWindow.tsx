"use client";

import { useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import { useChat } from "@/hooks/useChat";

interface ChatWindowProps {
  onExpand: () => void;
}

export default function ChatWindow({ onExpand }: ChatWindowProps) {
  const { messages, input, setInput, loading, handleSend } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex flex-col h-full">
      <div
        className="flex items-center justify-between px-4 py-3 text-white"
        style={{ backgroundColor: "#cb1d1e" }}
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-400 rounded-full" />
          <span className="font-semibold text-sm">
            Tư vấn điều dưỡng Nhật Bản
          </span>
        </div>
        <button
          onClick={onExpand}
          title="Mở rộng"
          aria-label="Mở trang chat toàn màn hình"
          className="text-white hover:text-gray-200 text-lg"
        >
          ⛶
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-gray-50">
        {messages.map((message, index) => (
          <ChatMessage
            key={`${message.role}-${index}`}
            message={message}
            compact
          />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 px-3 py-2 rounded-2xl text-sm text-gray-500">
              Đang trả lời...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-3 border-t bg-white flex gap-2">
        <input
          className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm outline-none focus:border-red-400"
          placeholder="Nhập câu hỏi..."
          aria-label="Câu hỏi tư vấn"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && handleSend()}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          aria-label="Gửi câu hỏi"
          className="w-9 h-9 rounded-full text-white flex items-center justify-center disabled:opacity-50"
          style={{ backgroundColor: "#cb1d1e" }}
        >
          ➤
        </button>
      </div>
    </div>
  );
}
