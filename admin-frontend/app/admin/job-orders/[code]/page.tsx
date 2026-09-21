"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import JobOrderForm from "@/components/admin/JobOrderForm";
import {
  JobOrderStatusBadge,
  PublicVisibilityBadge,
} from "@/components/admin/JobOrderStatusBadge";
import {
  JobOrder,
  JobOrderEvent,
  JobOrderMeta,
  managementApi,
} from "@/lib/managementApi";
import { loadCurrentUser } from "@/lib/auth";

const ACTION_LABELS: Record<string, string> = {
  created: "Tạo đơn",
  updated: "Cập nhật nội dung",
  status_changed: "Đổi trạng thái",
  published_changed: "Đổi hiển thị công khai",
  imported: "Nhập từ Excel",
};

export default function JobOrderDetailPage() {
  const params = useParams<{ code: string }>();
  const router = useRouter();
  const code = params.code;

  const [order, setOrder] = useState<JobOrder | null>(null);
  const [meta, setMeta] = useState<JobOrderMeta | null>(null);
  const [events, setEvents] = useState<JobOrderEvent[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [role, setRole] = useState("");

  const today = new Date().toISOString().slice(0, 10);
  const canManage = role === "admin" || role === "manager";

  const load = useCallback(() => {
    setError("");
    Promise.all([managementApi.jobOrder(code), managementApi.jobOrderEvents(code)])
      .then(([orderData, eventData]) => {
        setOrder(orderData);
        setEvents(eventData);
      })
      .catch((reason) => setError(reason.message));
  }, [code]);

  useEffect(load, [load]);

  useEffect(() => {
    managementApi.jobOrderMeta().then(setMeta).catch(() => undefined);
    loadCurrentUser()
      .then((user) => setRole(user.role))
      .catch(() => undefined);
  }, []);

  const run = async (action: () => Promise<unknown>, message: string) => {
    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Thao tác không thành công.");
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async () => {
    if (!confirm(`Xóa hẳn đơn ${code}? Thao tác này không hoàn lại được.`)) return;
    setSubmitting(true);
    try {
      await managementApi.deleteJobOrder(code);
      router.push("/admin/job-orders");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không xóa được đơn.");
      setSubmitting(false);
    }
  };

  if (!order || !meta) {
    return <p className="text-sm text-slate-500">{error || "Đang tải đơn tuyển dụng..."}</p>;
  }

  const nextStatuses = meta.transitions[order.status] ?? [];
  const statusLabel = (value: string) =>
    meta.statuses.find((item) => item.code === value)?.label ?? value;

  return (
    <>
      <PageHeader
        eyebrow={`Đơn ${order.code}`}
        title={order.title}
        description={`${order.employer_name} · ${order.prefecture} · ${order.labels.program}`}
        action={
          <Link
            href="/admin/job-orders"
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700"
          >
            Quay lại danh sách
          </Link>
        }
      />
      {error && <ErrorBanner message={error} />}
      {notice && (
        <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {notice}
        </div>
      )}

      <section className="mb-6 flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <JobOrderStatusBadge order={order} />
          <div className="mt-1">
            <PublicVisibilityBadge order={order} today={today} />
          </div>
        </div>
        <div className="text-sm text-slate-500">
          Đã tuyển {order.hired_count}/{order.quota} · Hạn nộp {order.deadline}
        </div>

        {canManage && (
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {nextStatuses.map((next) => (
              <button
                key={next}
                disabled={submitting}
                onClick={() =>
                  run(
                    () => managementApi.setJobOrderStatus(code, next),
                    `Đã chuyển đơn sang ${statusLabel(next)}.`,
                  )
                }
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:border-red-200 disabled:opacity-50"
              >
                {statusLabel(next)}
              </button>
            ))}
            <button
              disabled={submitting}
              onClick={() =>
                run(
                  () => managementApi.setJobOrderPublished(code, !order.published),
                  order.published
                    ? "Đã tắt hiển thị công khai."
                    : "Đã bật hiển thị công khai.",
                )
              }
              className="rounded-xl bg-[#171b22] px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
            >
              {order.published ? "Tắt công khai" : "Bật công khai"}
            </button>
            {role === "admin" && order.status === "draft" && (
              <button
                disabled={submitting}
                onClick={remove}
                className="rounded-xl border border-red-200 px-3 py-2 text-xs font-medium text-red-700 disabled:opacity-50"
              >
                Xóa đơn nháp
              </button>
            )}
          </div>
        )}
      </section>

      {order.status === "closed" && (
        <div className="mb-5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          Đơn đã đóng nên không sửa được nội dung. Mở lại đơn trước nếu cần chỉnh sửa.
        </div>
      )}

      {canManage && order.status !== "closed" && (
        <JobOrderForm
          meta={meta}
          initial={order}
          mode="edit"
          submitting={submitting}
          onSubmit={(payload) =>
            run(() => managementApi.updateJobOrder(code, payload), "Đã lưu thay đổi.")
          }
        />
      )}

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Lịch sử thao tác</h3>
        <p className="mt-1 text-xs text-slate-500">
          Mỗi lần đổi trạng thái hoặc nội dung đều được ghi lại kèm người thao tác.
        </p>
        {events.length === 0 ? (
          <p className="mt-4 text-sm text-slate-400">Chưa có thao tác nào.</p>
        ) : (
          <ol className="mt-4 space-y-3">
            {[...events].reverse().map((event, index) => (
              <li key={index} className="border-l-2 border-slate-200 pl-4 text-sm">
                <p className="font-medium text-slate-700">
                  {ACTION_LABELS[event.action] || event.action}
                  {event.old_status && event.new_status && (
                    <span className="font-normal text-slate-500">
                      {" "}
                      · {statusLabel(event.old_status)} → {statusLabel(event.new_status)}
                    </span>
                  )}
                </p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {event.actor_name || event.actor_email || "Hệ thống"} ·{" "}
                  {new Date(event.created_at).toLocaleString("vi-VN")}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}
