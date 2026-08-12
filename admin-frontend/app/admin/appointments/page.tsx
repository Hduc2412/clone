"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Appointment,
  AppointmentEvent,
  AppointmentStats,
  StaffUser,
  managementApi,
} from "@/lib/managementApi";
import { loadCurrentUser } from "@/lib/auth";
import {
  EmptyState,
  ErrorBanner,
  PageHeader,
  StatusBadge,
  statusLabels,
} from "@/components/admin/AdminUI";

const statusFilters = [
  ["", "Tất cả trạng thái"],
  ["pending", "Chờ xác nhận"],
  ["confirmed", "Đã xác nhận"],
  ["completed", "Đã hoàn thành"],
  ["unreachable", "Không liên lạc được"],
  ["cancelled", "Đã hủy"],
];

const eventLabels: Record<string, string> = {
  created: "Chatbot tạo lịch",
  assigned: "Phân công nhân viên",
  status_changed: "Cập nhật trạng thái",
  rescheduled: "Đổi lịch hẹn",
};

const emptyStats: AppointmentStats = {
  total: 0,
  pending: 0,
  confirmed: 0,
  completed: 0,
  unreachable: 0,
  cancelled: 0,
  confirmation_rate: 0,
  completion_rate: 0,
  unreachable_rate: 0,
  cancellation_rate: 0,
};

function isUpcoming(appointment: Appointment) {
  if (["completed", "cancelled"].includes(appointment.status)) return false;
  const scheduledAt = new Date(`${appointment.appointment_date}T${appointment.appointment_time}:00`);
  const remaining = scheduledAt.getTime() - Date.now();
  return remaining >= 0 && remaining <= 24 * 60 * 60 * 1000;
}

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [stats, setStats] = useState<AppointmentStats>(emptyStats);
  const [assignees, setAssignees] = useState<StaffUser[]>([]);
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [selectedAssignees, setSelectedAssignees] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [scheduleDates, setScheduleDates] = useState<Record<string, string>>({});
  const [scheduleTimes, setScheduleTimes] = useState<Record<string, string>>({});
  const [events, setEvents] = useState<Record<string, AppointmentEvent[]>>({});
  const [openHistory, setOpenHistory] = useState("");
  const [canAssign, setCanAssign] = useState(false);
  const [isConsultant, setIsConsultant] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    Promise.all([
      managementApi.appointments({ status, dateFrom, dateTo, assignedTo }),
      managementApi.appointmentStats({ dateFrom, dateTo, assignedTo }),
    ])
      .then(([appointmentRows, statsData]) => {
        setAppointments(appointmentRows);
        setStats(statsData);
      })
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [assignedTo, dateFrom, dateTo, status]);

  useEffect(() => load(), [load]);

  useEffect(() => {
    loadCurrentUser()
      .then((user) => {
        const canManageAssignments = ["admin", "manager"].includes(user.role);
        setCanAssign(canManageAssignments);
        setIsConsultant(user.role === "consultant");
        if (canManageAssignments) {
          managementApi.appointmentAssignees().then(setAssignees).catch(() => setAssignees([]));
        }
      })
      .catch(() => {
        setCanAssign(false);
        setIsConsultant(false);
      });
  }, []);

  const update = async (appointment: Appointment, nextStatus: string) => {
    setBusy(appointment.appointment_code);
    setError("");
    try {
      await managementApi.updateAppointment(
        appointment.appointment_code,
        nextStatus,
        notes[appointment.appointment_code],
      );
      if (nextStatus === "confirmed") {
        await managementApi.markNotificationRead(appointment.appointment_code).catch(() => null);
      }
      setEvents((current) => {
        const copy = { ...current };
        delete copy[appointment.appointment_code];
        return copy;
      });
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Cập nhật thất bại.");
    } finally {
      setBusy("");
    }
  };

  const assign = async (appointment: Appointment) => {
    const email = selectedAssignees[appointment.appointment_code] || appointment.assigned_to || "";
    if (!email) return;
    setBusy(appointment.appointment_code);
    setError("");
    try {
      await managementApi.assignAppointment(appointment.appointment_code, email);
      setEvents((current) => {
        const copy = { ...current };
        delete copy[appointment.appointment_code];
        return copy;
      });
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Phân công thất bại.");
    } finally {
      setBusy("");
    }
  };

  const toggleHistory = async (appointmentCode: string) => {
    if (openHistory === appointmentCode) {
      setOpenHistory("");
      return;
    }
    setOpenHistory(appointmentCode);
    if (!events[appointmentCode]) {
      try {
        const rows = await managementApi.appointmentEvents(appointmentCode);
        setEvents((current) => ({ ...current, [appointmentCode]: rows }));
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Không tải được lịch sử.");
      }
    }
  };

  const reschedule = async (appointment: Appointment) => {
    const appointmentDate = scheduleDates[appointment.appointment_code] || appointment.appointment_date;
    const appointmentTime = scheduleTimes[appointment.appointment_code] || appointment.appointment_time;
    setBusy(appointment.appointment_code);
    setError("");
    try {
      await managementApi.rescheduleAppointment(
        appointment.appointment_code,
        appointmentDate,
        appointmentTime,
        notes[appointment.appointment_code],
      );
      setEvents((current) => {
        const copy = { ...current };
        delete copy[appointment.appointment_code];
        return copy;
      });
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Đổi lịch thất bại.");
    } finally {
      setBusy("");
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Vận hành tư vấn"
        title="Quản lý lịch hẹn"
        description="Lọc lịch, phân công nhân viên và theo dõi toàn bộ lịch sử xử lý từ một màn hình."
        action={
          <button onClick={load} className="rounded-xl bg-[#171b22] px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700">
            Làm mới dữ liệu
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Tổng lịch", stats.total, "Toàn bộ trong bộ lọc"],
          ["Đã xác nhận", `${stats.confirmation_rate}%`, `${stats.confirmed} đang chờ xử lý`],
          ["Hoàn thành", `${stats.completion_rate}%`, `${stats.completed} lịch`],
          ["Không liên hệ", `${stats.unreachable_rate}%`, `${stats.unreachable} lịch`],
          ["Đã hủy", `${stats.cancellation_rate}%`, `${stats.cancelled} lịch`],
        ].map(([label, value, note]) => (
          <article key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-slate-800">{loading ? "—" : value}</p>
            <p className="mt-1 text-xs text-slate-400">{note}</p>
          </article>
        ))}
      </section>

      <section className="mb-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-4">
        <label className="text-xs font-medium text-slate-500">
          Trạng thái
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-red-400">
            {statusFilters.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="text-xs font-medium text-slate-500">
          Từ ngày
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-red-400" />
        </label>
        <label className="text-xs font-medium text-slate-500">
          Đến ngày
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-red-400" />
        </label>
        {!isConsultant && (
          <label className="text-xs font-medium text-slate-500">
            Nhân viên phụ trách
            <select value={assignedTo} onChange={(event) => setAssignedTo(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-red-400">
              <option value="">Tất cả nhân viên</option>
              {assignees.map((user) => <option key={user.email} value={user.email}>{user.full_name}</option>)}
            </select>
          </label>
        )}
      </section>

      {!loading && appointments.length === 0 ? (
        <EmptyState title="Không có lịch phù hợp" description="Thử thay đổi bộ lọc hoặc chờ lịch mới từ chatbot." />
      ) : (
        <div className="space-y-4">
          {appointments.map((appointment) => {
            const disabled = busy === appointment.appointment_code;
            const terminal = ["completed", "cancelled"].includes(appointment.status);
            return (
              <article key={appointment.appointment_code} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
                  <div className="flex min-w-0 flex-1 gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-red-50 font-semibold text-[#cb1d1e]">
                      {appointment.customer_name.slice(0, 1).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold">{appointment.customer_name}</h3>
                        <StatusBadge status={appointment.status} />
                        {isUpcoming(appointment) && (
                          <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700">
                            Sắp tới trong 24 giờ
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-slate-400">{appointment.appointment_code}</p>
                      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                        <a href={`tel:${appointment.phone}`} className="rounded-xl bg-slate-50 px-3 py-2.5 font-medium text-[#cb1d1e]">Gọi {appointment.phone}</a>
                        <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-slate-600">
                          {appointment.appointment_time} · {new Date(`${appointment.appointment_date}T00:00:00`).toLocaleDateString("vi-VN")}
                        </div>
                        <div className="rounded-xl bg-slate-50 px-3 py-2.5 text-slate-600">
                          {appointment.assigned_name || "Chưa phân công"}
                        </div>
                      </div>

                      {canAssign && !terminal && (
                        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                          <select
                            value={selectedAssignees[appointment.appointment_code] ?? appointment.assigned_to ?? ""}
                            onChange={(event) => setSelectedAssignees((current) => ({ ...current, [appointment.appointment_code]: event.target.value }))}
                            className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-red-400"
                          >
                            <option value="">Chọn nhân viên phụ trách</option>
                            {assignees.map((user) => <option key={user.email} value={user.email}>{user.full_name} · {user.role}</option>)}
                          </select>
                          <button disabled={disabled || !(selectedAssignees[appointment.appointment_code] ?? appointment.assigned_to)} onClick={() => assign(appointment)} className="rounded-xl border border-red-200 px-4 py-2.5 text-sm font-semibold text-[#cb1d1e] disabled:opacity-40">
                            Phân công
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="w-full xl:max-w-md">
                    <label className="text-xs font-medium text-slate-500">Ghi chú kết quả</label>
                    <input
                      value={notes[appointment.appointment_code] ?? appointment.result_note ?? ""}
                      onChange={(event) => setNotes((current) => ({ ...current, [appointment.appointment_code]: event.target.value }))}
                      placeholder="Ví dụ: Khách đã nghe máy và đồng ý tư vấn"
                      className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-red-400 focus:ring-2 focus:ring-red-100"
                    />
                    {!terminal && (
                      <div className="mt-3 grid grid-cols-[1fr_8rem_auto] gap-2">
                        <input
                          aria-label={`Ngày hẹn mới cho ${appointment.customer_name}`}
                          type="date"
                          min={new Date().toLocaleDateString("en-CA")}
                          value={scheduleDates[appointment.appointment_code] ?? appointment.appointment_date}
                          onChange={(event) => setScheduleDates((current) => ({ ...current, [appointment.appointment_code]: event.target.value }))}
                          className="min-w-0 rounded-lg border border-slate-200 px-2 py-2 text-xs outline-none focus:border-red-400"
                        />
                        <input
                          aria-label={`Giờ hẹn mới cho ${appointment.customer_name}`}
                          type="time"
                          value={scheduleTimes[appointment.appointment_code] ?? appointment.appointment_time}
                          onChange={(event) => setScheduleTimes((current) => ({ ...current, [appointment.appointment_code]: event.target.value }))}
                          className="min-w-0 rounded-lg border border-slate-200 px-2 py-2 text-xs outline-none focus:border-red-400"
                        />
                        <button
                          disabled={disabled}
                          onClick={() => reschedule(appointment)}
                          className="rounded-lg border border-orange-200 px-3 py-2 text-xs font-semibold text-orange-700 disabled:opacity-50"
                        >
                          Đổi lịch
                        </button>
                      </div>
                    )}
                    <div className="mt-3 flex flex-wrap gap-2">
                      {appointment.status === "pending" && <button disabled={disabled} onClick={() => update(appointment, "confirmed")} className="rounded-lg bg-[#cb1d1e] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Xác nhận nhận lịch</button>}
                      {appointment.status === "confirmed" && <>
                        <button disabled={disabled} onClick={() => update(appointment, "completed")} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Đã tư vấn</button>
                        <button disabled={disabled} onClick={() => update(appointment, "unreachable")} className="rounded-lg bg-amber-100 px-3 py-2 text-xs font-semibold text-amber-800 disabled:opacity-50">Không nghe máy</button>
                      </>}
                      {!terminal && <button disabled={disabled} onClick={() => update(appointment, "cancelled")} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 disabled:opacity-50">Hủy lịch</button>}
                      <button onClick={() => toggleHistory(appointment.appointment_code)} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600">
                        {openHistory === appointment.appointment_code ? "Ẩn lịch sử" : "Xem lịch sử"}
                      </button>
                    </div>
                  </div>
                </div>

                {openHistory === appointment.appointment_code && (
                  <div className="mt-5 border-t border-slate-100 pt-5">
                    <h4 className="text-sm font-semibold text-slate-700">Lịch sử xử lý</h4>
                    {!events[appointment.appointment_code] ? (
                      <p className="mt-3 text-sm text-slate-400">Đang tải lịch sử...</p>
                    ) : events[appointment.appointment_code].length === 0 ? (
                      <p className="mt-3 text-sm text-slate-400">Lịch cũ chưa có sự kiện được ghi nhận.</p>
                    ) : (
                      <ol className="mt-4 space-y-3 border-l-2 border-slate-100 pl-5">
                        {events[appointment.appointment_code].map((event, index) => (
                          <li key={`${event.created_at}-${index}`} className="relative rounded-xl bg-slate-50 px-4 py-3 text-sm">
                            <span className="absolute -left-[1.65rem] top-4 h-3 w-3 rounded-full border-2 border-white bg-[#cb1d1e]" />
                            <div className="flex flex-wrap justify-between gap-2">
                              <p className="font-medium text-slate-700">{eventLabels[event.action] || event.action}</p>
                              <time className="text-xs text-slate-400">{new Date(event.created_at).toLocaleString("vi-VN")}</time>
                            </div>
                            <p className="mt-1 text-xs text-slate-500">
                              {event.actor_name}
                              {event.old_status !== event.new_status && event.new_status ? ` · ${statusLabels[event.old_status || ""] || event.old_status || "Mới"} → ${statusLabels[event.new_status] || event.new_status}` : ""}
                              {event.details?.assigned_name ? ` · Giao cho ${event.details.assigned_name}` : ""}
                            </p>
                            {event.action === "rescheduled" && event.details?.appointment_date && (
                              <p className="mt-2 text-xs font-medium text-orange-700">
                                {event.details.previous_time} {event.details.previous_date} → {event.details.appointment_time} {event.details.appointment_date}
                              </p>
                            )}
                            {event.note && <p className="mt-2 text-xs text-slate-600">{event.note}</p>}
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}
