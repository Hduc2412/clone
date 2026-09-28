"use client";

import { useState } from "react";
import ChatWindow from "./ChatWindow";
import { useRouter } from "next/navigation";

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const router = useRouter();

  function handleExpand() {
    setIsOpen(false);
    router.push("/chat");
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3 sm:bottom-6 sm:right-6">
      {/* Cửa sổ chat nhỏ */}
      {isOpen && (
        <div id="tu-van-nhanh" className="w-[min(360px,calc(100vw-32px))] h-[min(480px,calc(100dvh-112px))] bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-200">
          <ChatWindow onExpand={handleExpand} />
        </div>
      )}

      {/* Nút mở widget */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="min-h-14 gap-2 rounded-full bg-brand-700 px-5 py-3 text-white shadow-lg flex items-center justify-center text-base hover:bg-brand-800 transition-colors"
        aria-expanded={isOpen}
        aria-controls={isOpen ? "tu-van-nhanh" : undefined}
        title="Tư vấn ngay"
      >
        {isOpen ? "Đóng tư vấn ×" : "Trò chuyện tư vấn"}
      </button>
    </div>
  );
}
