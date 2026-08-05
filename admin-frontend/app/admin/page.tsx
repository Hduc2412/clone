"use client";

import { useEffect, useState } from "react";
import {
  Appointment,
  ManagedLead,
  managementApi,
  Overview,
} from "@/lib/managementApi";
import {
  EmptyState,
  ErrorBanner,
  PageHeader,
  StatusBadge,
} from "@/components/admin/AdminUI";

const initialOverview: Overview = {
  appointments_total: 0,
  appointments_pending: 0,
  appointments_confirmed: 0,
  appointments_completed: 0,
  leads_total: 0,
  leads_new: 0,
  conversations_total: 0,
  messages_total: 0,
  notifications_unread: 0,
  staff_active: 0,
};

export default function AdminDashboard() {
  const [overview, setOverview] = useState(initialOverview);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [leads, setLeads] = useState<ManagedLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      managementApi.overview(),
      managementApi.appointments(),
      managementApi.leads(),
    ])
      .then(([overviewData, appointmentData, leadData]) => {
        setOverview(overviewData);
        setAppointments(appointmentData.slice(0, 5));
        setLeads(leadData.slice(0, 5));
      })
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    {
      label: "Lịch chờ xác nhận",
      value: overview.appointments_pending,
      note: `${overview.appointments_total} lịch trong hệ thống`,
      tone: "bg-red-50 text-[#b51718]",
      symbol: "◷",
    },
    {
      label: "Khách hàng mới",
      value: overview.leads_new,
      note: `${overview.leads_total} hồ sơ được quản lý`,
      tone: "bg-blue-50 text-blue-700",
      symbol: "♙",
    },
    {
      label: "Hội thoại",
      value: overview.conversations_total,
      note: `${overview.messages_total} tin nhắn đã lưu`,
      tone: "bg-violet-50 text-violet-700",
      symbol: "◌",
    },
    {
      label: "Thông báo chưa đọc",
      value: overview.notifications_unread,
      note: `${overview.staff_active} nhân viên hoạt động`,
      tone: "bg-amber-50 text-amber-700",
      symbol: "!",
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Trung tâm điều hành"
        title="Tổng quan hôm nay"
        description="Theo dõi lịch tư vấn, khách hàng và hoạt động chatbot từ một màn hình."
        action={
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-500 shadow-sm">
            Cập nhật tự động mỗi 30 giây
          </div>
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <article
            key={card.label}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-slate-500">{card.label}</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight">
                  {loading ? "—" : card.value}
                </p>
              </div>
              <span
                className={`flex h-11 w-11 items-center justify-center rounded-xl text-xl font-semibold ${card.tone}`}
              >
                {card.symbol}
              </span>
            </div>
            <p className="mt-4 text-xs text-slate-400">{card.note}</p>
          </article>
        ))}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <div>
              <h3 className="font-semibold">Lịch hẹn gần nhất</h3>
              <p className="mt-1 text-xs text-slate-400">
                Ưu tiên các lịch đang chờ nhân viên
              </p>
            </div>
            <a
              href="/admin/appointments"
              className="text-sm font-medium text-[#cb1d1e]"
            >
              Xem tất cả
            </a>
          </div>
          {appointments.length === 0 && !loading ? (
            <div className="p-5">
              <EmptyState
                title="Chưa có lịch hẹn"
                description="Lịch do chatbot tạo sẽ xuất hiện tại đây."
              />
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {appointments.map((appointment) => (
                <div
                  key={appointment.appointment_code}
                  className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-50 text-sm font-semibold text-[#cb1d1e]">
                    {appointment.customer_name.slice(0, 1).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {appointment.customer_name}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {appointment.phone} · {appointment.appointment_time}{" "}
                      {new Date(
                        `${appointment.appointment_date}T00:00:00`,
                      ).toLocaleDateString("vi-VN")}
                    </p>
                  </div>
                  <StatusBadge status={appointment.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-5 py-4">
            <h3 className="font-semibold">Khách hàng mới</h3>
            <p className="mt-1 text-xs text-slate-400">
              Hồ sơ được nhân viên tạo gần đây
            </p>
          </div>
          {leads.length === 0 && !loading ? (
            <div className="p-5">
              <EmptyState
                title="Chưa có khách hàng"
                description="Tạo hồ sơ đầu tiên từ trang Khách hàng."
              />
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {leads.map((lead) => (
                <div key={lead.lead_code} className="px-5 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {lead.customer_name}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {lead.phone} · {lead.source}
                      </p>
                    </div>
                    <StatusBadge status={lead.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
