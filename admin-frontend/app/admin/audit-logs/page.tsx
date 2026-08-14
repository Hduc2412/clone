"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { AuditLog, managementApi } from "@/lib/managementApi";

const labels: Record<string, string> = {
  "auth.login": "Đăng nhập",
  "auth.logout": "Đăng xuất",
  "auth.password_changed": "Đổi mật khẩu",
  "staff_user.created": "Tạo tài khoản",
  "staff_user.updated": "Cập nhật tài khoản",
  "lead.created": "Tạo khách hàng",
  "lead.updated": "Cập nhật khách hàng",
  "appointment.assigned": "Phân công lịch",
  "appointment.status_changed": "Đổi trạng thái lịch",
  "appointment.rescheduled": "Đổi lịch hẹn",
  "application.created": "Tạo hồ sơ tuyển dụng",
  "application.updated": "Cập nhật hồ sơ tuyển dụng",
};

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [actorEmail, setActorEmail] = useState("");
  const [action, setAction] = useState("");
  const [outcome, setOutcome] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    managementApi
      .auditLogs({ actorEmail, action, outcome, dateFrom, dateTo })
      .then(setLogs)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [action, actorEmail, dateFrom, dateTo, outcome]);

  useEffect(() => load(), [load]);

  return (
    <>
      <PageHeader
        eyebrow="Kiểm soát hệ thống"
        title="Nhật ký thao tác"
        description="Theo dõi đăng nhập và các thay đổi quan trọng trong hệ thống quản trị."
        action={
          <button
            onClick={load}
            className="rounded-xl bg-[#171b22] px-4 py-2.5 text-sm font-medium text-white"
          >
            Làm mới
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="mb-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-5">
        <input
          aria-label="Email người thao tác"
          placeholder="Email người thao tác"
          value={actorEmail}
          onChange={(event) => setActorEmail(event.target.value)}
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
        />
        <select
          aria-label="Hành động"
          value={action}
          onChange={(event) => setAction(event.target.value)}
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
        >
          <option value="">Tất cả hành động</option>
          {Object.entries(labels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select
          aria-label="Kết quả"
          value={outcome}
          onChange={(event) => setOutcome(event.target.value)}
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
        >
          <option value="">Tất cả kết quả</option>
          <option value="success">Thành công</option>
          <option value="failure">Thất bại</option>
        </select>
        <input
          aria-label="Từ ngày"
          type="date"
          value={dateFrom}
          onChange={(event) => setDateFrom(event.target.value)}
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
        />
        <input
          aria-label="Đến ngày"
          type="date"
          value={dateTo}
          onChange={(event) => setDateTo(event.target.value)}
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
        />
      </section>

      {!loading && logs.length === 0 ? (
        <EmptyState
          title="Chưa có nhật ký phù hợp"
          description="Thử thay đổi bộ lọc hoặc thực hiện một thao tác quản trị."
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Thời gian</th>
                  <th className="px-4 py-3">Người thao tác</th>
                  <th className="px-4 py-3">Hành động</th>
                  <th className="px-4 py-3">Đối tượng</th>
                  <th className="px-4 py-3">Kết quả</th>
                  <th className="px-4 py-3">Chi tiết</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log, index) => (
                  <tr key={`${log.created_at}-${index}`}>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                      {new Date(log.created_at).toLocaleString("vi-VN")}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium">{log.actor_name || log.actor_email || "Không xác định"}</p>
                      <p className="text-xs text-slate-400">{log.actor_email}</p>
                    </td>
                    <td className="px-4 py-3">{labels[log.action] || log.action}</td>
                    <td className="px-4 py-3 text-slate-500">{log.target_type} · {log.target_id}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${log.outcome === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
                        {log.outcome === "success" ? "Thành công" : "Thất bại"}
                      </span>
                    </td>
                    <td className="max-w-sm px-4 py-3">
                      <code className="break-all text-xs text-slate-500">{JSON.stringify(log.details)}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
