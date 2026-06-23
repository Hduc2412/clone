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
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Cửa sổ chat nhỏ */}
      {isOpen && (
        <div className="w-80 h-[480px] bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-200">
          <ChatWindow onExpand={handleExpand} />
        </div>
      )}

      {/* Nút mở widget */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-14 h-14 rounded-full text-white shadow-lg flex items-center justify-center text-2xl hover:scale-105 transition-transform"
        style={{ backgroundColor: "#cb1d1e" }}
        title="Tư vấn ngay"
      >
        {isOpen ? "✕" : "💬"}
      </button>
    </div>
  );
}