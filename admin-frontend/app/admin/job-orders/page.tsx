"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import {
  JobOrderStatusBadge,
  PublicVisibilityBadge,
} from "@/components/admin/JobOrderStatusBadge";
import { JobOrder, JobOrderMeta, managementApi } from "@/lib/managementApi";
import { loadCurrentUser } from "@/lib/auth";

export default function JobOrdersPage() {
  const [orders, setOrders] = useState<JobOrder[]>([]);
  const [meta, setMeta] = useState<JobOrderMeta | null>(null);
  const [status, setStatus] = useState("");
  const [program, setProgram] = useState("");
  const [regionGroup, setRegionGroup] = useState("");
  const [published, setPublished] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canManage, setCanManage] = useState(false);

  const today = new Date().toISOString().slice(0, 10);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    managementApi
      .jobOrders({
        status: status || undefined,
        program: program || undefined,
        regionGroup: regionGroup || undefined,
        published: published === "" ? undefined : published === "true",
      })
      .then(setOrders)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [program, published, regionGroup, status]);

  useEffect(load, [load]);

  useEffect(() => {
    managementApi.jobOrderMeta().then(setMeta).catch(() => undefined);
    loadCurrentUser()
      .then((user) => setCanManage(user.role === "admin" || user.role === "manager"))
      .catch(() => undefined);
  }, []);

  const visibleCount = orders.filter(
    (order) => order.published && order.status === "open" && order.deadline >= today,
  ).length;

  return (
    <>
      <PageHeader
        eyebrow="Danh mục tuyển dụng"
        title="Đơn tuyển dụng"
        description="Nguồn dữ liệu để giới thiệu việc làm cho ứng viên. Điều kiện bắt buộc của mỗi đơn chính là thứ hệ thống dùng để loại hoặc giữ hồ sơ khi đối chiếu."
        action={
          canManage ? (
            <div className="flex flex-wrap gap-2">
              <a
                href={managementApi.jobOrderTemplateUrl()}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700"
              >
                Tải file mẫu
              </a>
              <Link
                href="/admin/job-orders/import"
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700"
              >
                Nhập từ Excel
              </Link>
              <Link
                href="/admin/job-orders/new"
                className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white"
              >
                Thêm đơn
              </Link>
            </div>
          ) : undefined
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="mb-6 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <Filter value={status} onChange={setStatus} label="Tất cả trạng thái">
          {(meta?.statuses ?? []).map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </Filter>
        <Filter value={program} onChange={setProgram} label="Tất cả chương trình">
          {(meta?.programs ?? []).map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </Filter>
        <Filter value={regionGroup} onChange={setRegionGroup} label="Tất cả vùng">
          {(meta?.regions ?? []).map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </Filter>
        <Filter value={published} onChange={setPublished} label="Công khai và chưa">
          <option value="true">Đã bật công khai</option>
          <option value="false">Chưa công khai</option>
        </Filter>
        <p className="ml-auto text-xs text-slate-500">
          {orders.length} đơn · <span className="font-medium text-emerald-700">{visibleCount}</span> đang
          hiển thị trên website
        </p>
      </section>

      {!loading && orders.length === 0 ? (
        <EmptyState
          title="Chưa có đơn tuyển dụng nào"
          description="Thêm đơn thủ công, hoặc tải file mẫu rồi nhập hàng loạt danh sách đơn công ty đang dùng."
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  {["Đơn hàng", "Địa điểm", "Điều kiện bắt buộc", "Tuyển", "Hạn nộp", "Trạng thái"].map(
                    (label) => (
                      <th key={label} className="px-5 py-3.5">
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {orders.map((order) => (
                  <tr key={order.code} className="hover:bg-slate-50/70">
                    <td className="px-5 py-4">
                      <Link
                        href={`/admin/job-orders/${order.code}`}
                        className="font-medium text-slate-900 hover:text-[#cb1d1e]"
                      >
                        {order.title}
                      </Link>
                      <p className="mt-1 text-xs text-slate-400">
                        {order.code} · {order.employer_name}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      <p>{order.prefecture}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {order.labels.region_group} · {order.labels.employer_type}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      <p>
                        {order.labels.japanese_required}
                        {order.labels.education_required
                          ? ` · ${order.labels.education_required}`
                          : ""}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {order.requirements.age_min ?? "?"}–{order.requirements.age_max ?? "?"} tuổi
                        {order.requirements.experience_min > 0
                          ? ` · ${order.requirements.experience_min} năm KN`
                          : ""}
                        {order.requirements.gender_pref !== "khong_yeu_cau"
                          ? ` · ${order.labels.gender_pref}`
                          : ""}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {order.hired_count}/{order.quota}
                    </td>
                    <td
                      className={`px-5 py-4 ${
                        order.deadline < today ? "text-orange-700" : "text-slate-600"
                      }`}
                    >
                      {formatDate(order.deadline)}
                    </td>
                    <td className="px-5 py-4">
                      <JobOrderStatusBadge order={order} />
                      <div className="mt-1">
                        <PublicVisibilityBadge order={order} today={today} />
                      </div>
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

function formatDate(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function Filter({
  value,
  onChange,
  label,
  children,
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
    >
      <option value="">{label}</option>
      {children}
    </select>
  );
}
