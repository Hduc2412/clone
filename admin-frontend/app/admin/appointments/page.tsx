"use client";

import { useCallback, useEffect, useState } from "react";
import { Appointment, managementApi } from "@/lib/managementApi";
import {
  EmptyState,
  ErrorBanner,
  PageHeader,
  StatusBadge,
  statusLabels,
} from "@/components/admin/AdminUI";

const filters = [
  ["", "Tất cả"],
  ["pending", "Chờ xác nhận"],
  ["confirmed", "Đã xác nhận"],
  ["completed", "Đã hoàn thành"],
  ["unreachable", "Không liên lạc được"],
  ["cancelled", "Đã hủy"],
];

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [filter, setFilter] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    managementApi
      .appointments(filter || undefined)
      .then(setAppointments)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => load(), [load]);

  const update = async (appointment: Appointment, status: string) => {
    setBusy(appointment.appointment_code);
    setError("");
    try {
      await managementApi.updateAppointment(
        appointment.appointment_code,
        status,
        "Nhân viên local",
        notes[appointment.appointment_code],
      );
      if (status === "confirmed") {
        await managementApi
          .markNotificationRead(appointment.appointment_code)
          .catch(() => null);
      }
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Cập nhật thất bại.");
    } finally {
      setBusy("");
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Vận hành tư vấn"
        title="Quản lý lịch hẹn"
        description="Xác nhận lịch do chatbot tạo, gọi cho khách hàng và ghi nhận kết quả liên hệ."
        action={
          <button
            onClick={load}
            className="rounded-xl bg-[#171b22] px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            Làm mới dữ liệu
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}

      <div className="mb-5 flex gap-2 overflow-x-auto pb-1">
        {filters.map(([value, label]) => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition ${
              filter === value
                ? "bg-[#cb1d1e] text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:border-red-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {!loading && appointments.length === 0 ? (
        <EmptyState
          title="Không có lịch phù hợp"
          description="Lịch mới do khách hàng đặt qua chatbot sẽ xuất hiện tại đây."
        />
      ) : (
        <div className="space-y-4">
          {appointments.map((appointment) => {
            const disabled = busy === appointment.appointment_code;
            return (
              <article
                key={appointment.appointment_code}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
                  <div className="flex min-w-0 flex-1 gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-red-50 font-semibold text-[#cb1d1e]">
                      {appointment.customer_name.slice(0, 1).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold">
                          {appointment.customer_name}
                        </h3>
                        <StatusBadge status={appointment.status} />
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        {appointment.appointment_code}
                      </p>
                      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                        <a
                          href={`tel:${appointment.phone}`}
                          className="rounded-xl bg-slate-50 px-3 py-2.5 font-medium text-[#cb1d1e]"
                        >
                          Gọi {appointment.phone}
                        </a>
                        <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-slate-600">
                          {appointment.appointment_time} ·{" "}
                          {new Date(
                            `${appointment.appointment_date}T00:00:00`,
                          ).toLocaleDateString("vi-VN")}
                        </div>
                        <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-slate-600">
                          {appointment.confirmed_by || "Chưa có người nhận"}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="w-full xl:max-w-md">
                    <label className="text-xs font-medium text-slate-500">
                      Ghi chú kết quả
                    </label>
                    <input
                      value={
                        notes[appointment.appointment_code] ??
                        appointment.result_note ??
                        ""
                      }
                      onChange={(event) =>
                        setNotes((current) => ({
                          ...current,
                          [appointment.appointment_code]: event.target.value,
                        }))
                      }
                      placeholder="Ví dụ: Khách đã nghe máy và đồng ý tư vấn"
                      className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none transition focus:border-red-400 focus:ring-2 focus:ring-red-100"
                    />
                    <div className="mt-3 flex flex-wrap gap-2">
                      {appointment.status === "pending" && (
                        <button
                          disabled={disabled}
                          onClick={() => update(appointment, "confirmed")}
                          className="rounded-lg bg-[#cb1d1e] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                        >
                          Xác nhận nhận lịch
                        </button>
                      )}
                      {appointment.status === "confirmed" && (
                        <>
                          <button
                            disabled={disabled}
                            onClick={() => update(appointment, "completed")}
                            className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                          >
                            Đã tư vấn
                          </button>
                          <button
                            disabled={disabled}
                            onClick={() => update(appointment, "unreachable")}
                            className="rounded-lg bg-amber-100 px-3 py-2 text-xs font-semibold text-amber-800 disabled:opacity-50"
                          >
                            Không nghe máy
                          </button>
                        </>
                      )}
                      {!["completed", "cancelled"].includes(
                        appointment.status,
                      ) && (
                        <button
                          disabled={disabled}
                          onClick={() => update(appointment, "cancelled")}
                          className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 disabled:opacity-50"
                        >
                          Hủy lịch
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <p className="mt-5 text-xs text-slate-400">
        Trạng thái:{" "}
        {filters
          .slice(1)
          .map(([value]) => statusLabels[value])
          .join(" · ")}
      </p>
    </>
  );
}
