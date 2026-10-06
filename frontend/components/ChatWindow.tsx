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
        {/* Nói rõ khung này làm gì, ngay trên tiêu đề.
          *
          * Bản trước ghi "Tư vấn điều dưỡng Nhật Bản" — không phân biệt được với
          * phòng tư vấn theo hồ sơ, nên người dùng mang câu "em còn thiếu gì" vào
          * đây rồi nhận một câu trả lời chung chung từ tài liệu công ty.
          *
          * Hai khung biết hai thứ khác nhau: khung này đọc tài liệu công ty và
          * không có hồ sơ của ai; phòng tư vấn hồ sơ thì ngược lại. Người dùng
          * biết ranh giới thì hỏi đúng chỗ. */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-400 rounded-full" />
            <span className="font-semibold text-sm">Hỏi đáp chung</span>
          </div>
          <span className="text-[11px] leading-4 text-white/80">
            Chương trình, chi phí, quy trình
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

      {/* Đường sang phòng tư vấn hồ sơ.
        *
        * Khung này không có hồ sơ của ai, nên câu "em còn thiếu gì" ở đây chỉ
        * nhận được câu trả lời chung. Để người dùng tự dò ra điều đó sau ba câu
        * hỏi trượt là bắt họ trả giá cho một ranh giới họ không nhìn thấy. */}
      <div className="border-t bg-amber-50 px-3 py-2 text-[11px] leading-4 text-amber-900">
        Hỏi về <strong>hồ sơ của bạn</strong> hay đơn cụ thể thì sang{" "}
        <a href="/tu-van" className="font-semibold underline">
          phòng tư vấn theo hồ sơ
        </a>{" "}
        — ở đó trợ lý có dữ liệu của bạn.
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
