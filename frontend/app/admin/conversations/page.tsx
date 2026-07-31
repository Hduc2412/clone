"use client";

import { useEffect, useState } from "react";
import {
  Conversation,
  ConversationMessage,
  managementApi,
} from "@/lib/managementApi";
import {
  EmptyState,
  ErrorBanner,
  PageHeader,
} from "@/components/admin/AdminUI";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    managementApi
      .conversations()
      .then(setConversations)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  const openConversation = async (sessionId: string) => {
    setSelected(sessionId);
    setMessages([]);
    try {
      const detail = await managementApi.conversation(sessionId);
      setMessages(detail.messages);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đọc hội thoại.");
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Lịch sử chatbot"
        title="Quản lý hội thoại"
        description="Tìm và xem lại các cuộc tư vấn đã được chatbot lưu trong MongoDB."
      />
      {error && <ErrorBanner message={error} />}

      {!loading && conversations.length === 0 ? (
        <EmptyState
          title="Chưa có hội thoại"
          description="Khi khách hàng sử dụng chatbot, lịch sử sẽ xuất hiện tại đây."
        />
      ) : (
        <div className="grid min-h-[620px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm lg:grid-cols-[360px_1fr]">
          <div className="border-b border-slate-200 lg:border-b-0 lg:border-r">
            <div className="border-b border-slate-100 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
              {conversations.length} cuộc hội thoại
            </div>
            <div className="max-h-[680px] overflow-y-auto">
              {conversations.map((conversation) => (
                <button
                  key={conversation.session_id}
                  onClick={() => openConversation(conversation.session_id)}
                  className={`w-full border-b border-slate-100 px-4 py-4 text-left transition ${
                    selected === conversation.session_id
                      ? "bg-red-50"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-medium">
                      Phiên {conversation.session_id.slice(0, 10)}
                    </p>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
                      {conversation.message_count || 0} tin
                    </span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
                    {conversation.latest_message?.content || "Chưa có nội dung"}
                  </p>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span>{conversation.last_intent || "chung"}</span>
                    <span>
                      {conversation.last_active
                        ? new Date(conversation.last_active).toLocaleString("vi-VN")
                        : ""}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex min-h-[620px] flex-col bg-[#f8f9fb]">
            {!selected ? (
              <div className="m-auto max-w-sm px-6 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-2xl shadow-sm">
                  ◌
                </div>
                <p className="mt-4 font-medium text-slate-700">
                  Chọn một hội thoại
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Nội dung tin nhắn, intent và thời gian sẽ được hiển thị tại đây.
                </p>
              </div>
            ) : (
              <>
                <div className="border-b border-slate-200 bg-white px-5 py-4">
                  <p className="text-sm font-medium">Chi tiết hội thoại</p>
                  <p className="mt-1 break-all text-xs text-slate-400">{selected}</p>
                </div>
                <div className="flex-1 space-y-4 overflow-y-auto p-5">
                  {messages.map((message, index) => {
                    const user = message.role === "user";
                    return (
                      <div
                        key={`${message.created_at}-${index}`}
                        className={`flex ${user ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
                            user
                              ? "bg-[#cb1d1e] text-white"
                              : "border border-slate-200 bg-white text-slate-700"
                          }`}
                        >
                          <p>{message.content}</p>
                          <p
                            className={`mt-2 text-[10px] ${
                              user ? "text-red-100" : "text-slate-400"
                            }`}
                          >
                            {message.intent || message.role}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
