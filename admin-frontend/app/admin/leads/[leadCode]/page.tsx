"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CustomerJourney, managementApi } from "@/lib/managementApi";
import { EmptyState, ErrorBanner, PageHeader, StatusBadge } from "@/components/admin/AdminUI";

const dateTime = (value?: string | null) =>
  value ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";

export default function CustomerJourneyPage() {
  const params = useParams<{ leadCode: string }>();
  const leadCode = decodeURIComponent(params.leadCode);
  const [journey, setJourney] = useState<CustomerJourney | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    managementApi.customerJourney(leadCode).then(setJourney).catch((reason) => setError(reason.message));
  }, [leadCode]);

  if (error) return <ErrorBanner message={error} />;
  if (!journey) return <p className="text-sm text-slate-500">Đang tải hành trình khách hàng...</p>;

  const { lead, applications, appointments, conversations } = journey;
  return (
    <>
      <PageHeader
        eyebrow="Hành trình khách hàng"
        title={lead.customer_name}
        description={`${lead.lead_code} · ${lead.phone} · Phụ trách: ${lead.assigned_to || "Chưa phân công"}`}
        action={<Link href="/admin/leads" className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium">← Danh sách khách hàng</Link>}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <Summary label="Trạng thái khách hàng"><StatusBadge status={lead.status} /></Summary>
        <Summary label="Hồ sơ tuyển dụng">{applications.length}</Summary>
        <Summary label="Lịch tư vấn">{appointments.length}</Summary>
        <Summary label="Hội thoại chatbot">{conversations.length}</Summary>
      </div>

      <Section title="Hồ sơ tuyển dụng">
        {applications.length ? applications.map((item) => (
          <article key={item.application_code} className="rounded-xl border border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><p className="font-semibold">{item.application_code}</p><p className="text-xs text-slate-500">Cập nhật {dateTime(item.updated_at)}</p></div>
              <StatusBadge status={item.status} />
            </div>
            <p className="mt-3 text-sm text-slate-600">Nơi đến: {item.destination || "Chưa có"} · Trình độ: {item.japanese_level || "Chưa có"} · Phụ trách: {item.assigned_to || "Chưa phân công"}</p>
          </article>
        )) : <EmptyState title="Chưa có hồ sơ tuyển dụng" description="Khách hàng này chưa được tạo hồ sơ tuyển dụng." />}
      </Section>

      <Section title="Lịch tư vấn">
        {appointments.length ? appointments.map((item) => (
          <article key={item.appointment_code} className="rounded-xl border border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3"><p className="font-semibold">{item.appointment_date} lúc {item.appointment_time}</p><StatusBadge status={item.status} /></div>
            <p className="mt-2 text-sm text-slate-600">{item.appointment_code} · {item.assigned_name || item.assigned_to || "Chưa phân công"}</p>
            {item.result_note && <p className="mt-2 text-sm text-slate-500">Kết quả: {item.result_note}</p>}
          </article>
        )) : <EmptyState title="Chưa có lịch tư vấn" description="Không tìm thấy lịch hẹn phù hợp với khách hàng và quyền truy cập hiện tại." />}
      </Section>

      <Section title="Hội thoại chatbot">
        {conversations.length ? conversations.map((conversation) => (
          <details key={conversation.session_id} className="rounded-xl border border-slate-200 p-4">
            <summary className="cursor-pointer font-semibold">{conversation.messages.length} tin nhắn · {dateTime(conversation.last_active)}</summary>
            <div className="mt-4 space-y-2">
              {conversation.messages.map((message, index) => (
                <div key={`${conversation.session_id}-${index}`} className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${message.role === "user" ? "ml-auto bg-red-50" : "bg-slate-100"}`}>
                  <p className="mb-1 text-xs font-medium text-slate-500">{message.role === "user" ? "Khách hàng" : "Chatbot"}</p>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              ))}
            </div>
          </details>
        )) : <EmptyState title="Chưa có hội thoại liên kết" description="Hệ thống chưa tìm thấy phiên chatbot hoặc lịch tư vấn liên kết với khách hàng này." />}
      </Section>
    </>
  );
}

function Summary({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs uppercase tracking-wide text-slate-500">{label}</p><div className="mt-2 text-2xl font-semibold">{children}</div></div>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="mb-4 text-lg font-semibold">{title}</h2><div className="space-y-3">{children}</div></section>;
}
