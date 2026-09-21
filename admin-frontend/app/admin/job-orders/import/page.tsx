"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { JobOrderImportResult, managementApi } from "@/lib/managementApi";

/**
 * Nhập danh mục đơn hàng từ file Excel, theo ba bước cố định:
 * chọn file → xem bảng kiểm tra → xác nhận ghi.
 *
 * Bước xem trước là bắt buộc chứ không phải tiện ích. Một file hai trăm dòng mà
 * ghi được tám mươi dòng rồi mới báo lỗi là tình huống không dọn được: không
 * biết dòng nào đã vào, dòng nào chưa.
 */
export default function ImportJobOrdersPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<JobOrderImportResult | null>(null);
  const [onlyErrors, setOnlyErrors] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const check = async (selected: File) => {
    setBusy(true);
    setError("");
    setPreview(null);
    try {
      setPreview(await managementApi.importJobOrders(selected, true));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không đọc được file.");
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const result = await managementApi.importJobOrders(file, false);
      setPreview(result);
      if ((result.applied?.failed.length ?? 0) === 0) {
        router.push("/admin/job-orders");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không ghi được vào hệ thống.");
    } finally {
      setBusy(false);
    }
  };

  const summary = preview?.summary;
  const rows = (preview?.rows ?? []).filter(
    (row) => !onlyErrors || row.action === "error",
  );
  const ready = Boolean(summary && summary.error === 0 && summary.total > 0);

  return (
    <>
      <PageHeader
        eyebrow="Danh mục tuyển dụng"
        title="Nhập đơn hàng từ Excel"
        description="Tải lên file danh sách đơn hàng công ty đang dùng. Hệ thống kiểm tra từng dòng trước, chưa ghi gì cho tới khi bạn xác nhận."
        action={
          <div className="flex flex-wrap gap-2">
            <a
              href={managementApi.jobOrderTemplateUrl()}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700"
            >
              Tải file mẫu
            </a>
            <Link
              href="/admin/job-orders"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700"
            >
              Quay lại danh sách
            </Link>
          </div>
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="mb-6 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center shadow-sm">
        <input
          id="job-order-file"
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(event) => {
            const selected = event.target.files?.[0] ?? null;
            setFile(selected);
            if (selected) check(selected);
          }}
        />
        <label
          htmlFor="job-order-file"
          className="inline-block cursor-pointer rounded-xl bg-[#cb1d1e] px-5 py-2.5 text-sm font-medium text-white"
        >
          Chọn file Excel
        </label>
        <p className="mt-3 text-sm text-slate-500">
          {file ? file.name : "Chỉ nhận định dạng .xlsx, tối đa 5MB và 500 dòng."}
        </p>
        {busy && <p className="mt-2 text-sm text-slate-400">Đang xử lý...</p>}
      </section>

      {summary && (
        <>
          <section className="mb-5 grid gap-4 md:grid-cols-4">
            <Stat label="Tổng số dòng" value={summary.total} />
            <Stat label="Thêm mới" value={summary.create} tone="text-emerald-700" />
            <Stat label="Cập nhật" value={summary.update} tone="text-blue-700" />
            <Stat label="Dòng lỗi" value={summary.error} tone="text-red-700" />
          </section>

          {preview?.applied && (
            <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              Đã ghi vào hệ thống: {preview.applied.created} đơn mới,{" "}
              {preview.applied.updated} đơn cập nhật.
              {preview.applied.failed.length > 0 && (
                <span className="text-red-700">
                  {" "}
                  {preview.applied.failed.length} dòng không ghi được.
                </span>
              )}
            </div>
          )}

          <div className="mb-4 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={onlyErrors}
                onChange={(event) => setOnlyErrors(event.target.checked)}
              />
              Chỉ xem dòng lỗi
            </label>
            {!preview?.applied && (
              <button
                disabled={!ready || busy}
                onClick={commit}
                className="ml-auto rounded-xl bg-[#cb1d1e] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
              >
                {ready
                  ? `Xác nhận ghi ${summary.total} dòng`
                  : "Sửa hết lỗi rồi mới ghi được"}
              </button>
            )}
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    {["Dòng", "Mã đơn", "Tên đơn", "Kết quả"].map((label) => (
                      <th key={label} className="px-5 py-3.5">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((row) => (
                    <tr
                      key={row.row_number}
                      className={row.action === "error" ? "bg-red-50/40" : ""}
                    >
                      <td className="px-5 py-3 font-medium text-slate-500">{row.row_number}</td>
                      <td className="px-5 py-3 text-slate-600">{row.code || "—"}</td>
                      <td className="px-5 py-3 text-slate-700">{row.title || "—"}</td>
                      <td className="px-5 py-3">
                        {row.action === "error" ? (
                          <ul className="space-y-1 text-xs text-red-700">
                            {row.errors.map((message, index) => (
                              <li key={index}>{message}</li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-xs font-medium text-slate-600">
                            {row.action === "create" ? "Thêm mới" : "Cập nhật"}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className={`text-3xl font-semibold tracking-tight ${tone ?? "text-slate-900"}`}>
        {value}
      </p>
      <p className="mt-2 text-sm text-slate-500">{label}</p>
    </article>
  );
}
