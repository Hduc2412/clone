"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import JobOrderForm from "@/components/admin/JobOrderForm";
import { JobOrderMeta, managementApi } from "@/lib/managementApi";

export default function NewJobOrderPage() {
  const router = useRouter();
  const [meta, setMeta] = useState<JobOrderMeta | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    managementApi
      .jobOrderMeta()
      .then(setMeta)
      .catch((reason) => setError(reason.message));
  }, []);

  const submit = async (payload: Record<string, unknown>) => {
    setSubmitting(true);
    setError("");
    try {
      const order = await managementApi.createJobOrder(payload);
      router.push(`/admin/job-orders/${order.code}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không tạo được đơn tuyển dụng.");
      setSubmitting(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Danh mục tuyển dụng"
        title="Thêm đơn tuyển dụng"
        description="Đơn mới bắt đầu ở trạng thái Nháp hoặc Đang tuyển. Các trạng thái còn lại đổi sau trên trang chi tiết, để hệ thống lưu được ai đổi và vì sao."
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
      {meta ? (
        <JobOrderForm meta={meta} mode="create" onSubmit={submit} submitting={submitting} />
      ) : (
        <p className="text-sm text-slate-500">Đang tải danh mục...</p>
      )}
    </>
  );
}
