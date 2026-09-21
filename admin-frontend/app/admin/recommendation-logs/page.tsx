"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { RecommendationLogSummary, managementApi } from "@/lib/managementApi";

const TRIGGER_LABELS: Record<string, string> = {
  public: "Ứng viên xem",
  staff_rerun: "Nhân viên chạy lại",
  registration: "Lúc đăng ký",
};

export default function RecommendationLogsPage() {
  const [logs, setLogs] = useState<RecommendationLogSummary[]>([]);
  const [profileCode, setProfileCode] = useState("");
  const [trigger, setTrigger] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    managementApi
      .recommendationLogs({
        profileCode: profileCode.trim() || undefined,
        trigger: trigger || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
      })
      .then(setLogs)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [dateFrom, dateTo, profileCode, trigger]);

  useEffect(load, [load]);

  return (
    <>
      <PageHeader
        eyebrow="Đối chiếu đơn hàng"
        title="Nhật ký giới thiệu"
        description="Mỗi lần hệ thống giới thiệu đơn cho một ứng viên, toàn bộ đơn đã xét được ghi lại ở đây — kể cả đơn bị loại, kèm lý do từng tiêu chí. Đây là chỗ trả lời câu hỏi vì sao một đơn không được giới thiệu."
      />
      {error && <ErrorBanner message={error} />}

      <section className="mb-6 flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Mã hồ sơ ứng viên
          <input
            value={profileCode}
            onChange={(event) => setProfileCode(event.target.value)}
            placeholder="UV-..."
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Nguồn chạy
          <select
            value={trigger}
            onChange={(event) => setTrigger(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700"
          >
            <option value="">Tất cả</option>
            {Object.entries(TRIGGER_LABELS).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Từ ngày
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Đến ngày
          <input
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700"
          />
        </label>
        <p className="ml-auto text-xs text-slate-500">{logs.length} lần đối chiếu</p>
      </section>

      {!loading && logs.length === 0 ? (
        <EmptyState
          title="Chưa có lần đối chiếu nào"
          description="Nhật ký được ghi khi ứng viên xem danh sách đơn phù hợp, hoặc khi nhân viên bấm chạy lại trên một hồ sơ."
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  {["Lần đối chiếu", "Hồ sơ", "Kết quả", "Đơn đứng đầu", "Nguồn chạy", "Thời điểm"].map(
                    (label) => (
                      <th key={label} className="px-5 py-3.5">
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log) => (
                  <tr key={log.code} className="hover:bg-slate-50/70">
                    <td className="px-5 py-4">
                      <Link
                        href={`/admin/recommendation-logs/${log.code}`}
                        className="font-medium text-slate-900 hover:text-[#cb1d1e]"
                      >
                        {log.code}
                      </Link>
                      <p className="mt-1 text-xs text-slate-400">
                        Bộ đối chiếu {log.engine_version} · trọng số {log.weights_version}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {log.profile_code}
                      <p className="mt-1 text-xs text-slate-400">
                        bản {log.profile_version}
                        {log.assigned_to ? ` · ${log.assigned_to}` : " · chưa phân công"}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      <span className="font-medium text-emerald-700">{log.eligible_count}</span> đạt
                      {" / "}
                      {log.total_considered} đơn đã xét
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {log.top_codes.slice(0, 3).join(", ") || "—"}
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {TRIGGER_LABELS[log.trigger] ?? log.trigger}
                      {log.actor_email && (
                        <p className="mt-1 text-xs text-slate-400">{log.actor_email}</p>
                      )}
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {formatDateTime(log.created_at)}
                      <p className="mt-1 text-xs text-slate-400">tính theo ngày {log.as_of}</p>
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

function formatDateTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
