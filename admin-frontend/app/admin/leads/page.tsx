"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ManagedLead, managementApi } from "@/lib/managementApi";
import {
  EmptyState,
  ErrorBanner,
  PageHeader,
  StatusBadge,
} from "@/components/admin/AdminUI";

const leadStatuses = [
  ["new", "Mới"],
  ["assigned", "Đã phân công"],
  ["contacted", "Đã liên hệ"],
  ["consulting", "Đang tư vấn"],
  ["qualified", "Đủ điều kiện"],
  ["preparing_documents", "Chuẩn bị hồ sơ"],
  ["training", "Đang đào tạo"],
  ["waiting_interview", "Chờ phỏng vấn"],
  ["passed", "Đã trúng tuyển"],
  ["visa_processing", "Đang làm visa"],
  ["departed", "Đã xuất cảnh"],
  ["paused", "Tạm dừng"],
  ["cancelled", "Đã hủy"],
];

export default function LeadsPage() {
  const [leads, setLeads] = useState<ManagedLead[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    managementApi
      .leads()
      .then(setLeads)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await managementApi.createLead({
        customer_name: String(form.get("customer_name") || ""),
        phone: String(form.get("phone") || ""),
        source: String(form.get("source") || "manual"),
        assigned_to: String(form.get("assigned_to") || "") || undefined,
      });
      event.currentTarget.reset();
      setShowForm(false);
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tạo hồ sơ.");
    }
  };

  const changeStatus = async (lead: ManagedLead, status: string) => {
    try {
      await managementApi.updateLead(lead.lead_code, { status });
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Cập nhật thất bại.");
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Quy trình tuyển dụng"
        title="Khách hàng và lead"
        description="Quản lý hồ sơ do nhân viên tạo. Chatbot đặt lịch không tự động tạo lead."
        action={
          <button
            onClick={() => setShowForm((value) => !value)}
            className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white"
          >
            {showForm ? "Đóng biểu mẫu" : "Thêm khách hàng"}
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}

      {showForm && (
        <form
          onSubmit={submit}
          className="mb-6 grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2 xl:grid-cols-4"
        >
          <Field name="customer_name" label="Họ tên" placeholder="Nguyễn Văn Nam" />
          <Field
            name="phone"
            label="Số điện thoại"
            placeholder="0912345678 hoặc +84 912 345 678"
            inputMode="tel"
          />
          <label className="text-sm font-medium text-slate-600">
            Nguồn
            <select
              name="source"
              className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none"
            >
              <option value="manual">Nhân viên nhập</option>
              <option value="website">Website</option>
              <option value="facebook">Facebook</option>
              <option value="referral">Giới thiệu</option>
            </select>
          </label>
          <Field
            name="assigned_to"
            label="Nhân viên phụ trách"
            placeholder="Chưa phân công"
            required={false}
          />
          <button className="rounded-xl bg-[#171b22] px-4 py-2.5 text-sm font-medium text-white md:col-span-2 xl:col-span-4">
            Lưu hồ sơ khách hàng
          </button>
        </form>
      )}

      {!loading && leads.length === 0 ? (
        <EmptyState
          title="Chưa có hồ sơ khách hàng"
          description="Nhấn “Thêm khách hàng” để tạo hồ sơ đầu tiên. Lịch chatbot vẫn được quản lý độc lập."
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  {["Khách hàng", "Liên hệ", "Nguồn", "Phụ trách", "Trạng thái"].map(
                    (label) => (
                      <th key={label} className="px-5 py-3.5">
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {leads.map((lead) => (
                  <tr key={lead.lead_code} className="hover:bg-slate-50/70">
                    <td className="px-5 py-4">
                      <Link
                        href={`/admin/leads/${encodeURIComponent(lead.lead_code)}`}
                        className="font-medium hover:text-[#cb1d1e] hover:underline"
                      >
                        {lead.customer_name}
                      </Link>
                      <p className="mt-1 text-xs text-slate-400">
                        {lead.lead_code}
                      </p>
                    </td>
                    <td className="px-5 py-4">
                      <a href={`tel:${lead.phone}`} className="font-medium text-[#cb1d1e]">
                        {lead.phone}
                      </a>
                    </td>
                    <td className="px-5 py-4 text-slate-500">{lead.source}</td>
                    <td className="px-5 py-4 text-slate-500">
                      {lead.assigned_to || "Chưa phân công"}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <StatusBadge status={lead.status} />
                        <select
                          value={lead.status}
                          onChange={(event) => changeStatus(lead, event.target.value)}
                          className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs outline-none"
                        >
                          {leadStatuses.map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
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

function Field({
  name,
  label,
  placeholder,
  pattern,
  inputMode,
  required = true,
}: {
  name: string;
  label: string;
  placeholder: string;
  pattern?: string;
  inputMode?: "tel";
  required?: boolean;
}) {
  return (
    <label className="text-sm font-medium text-slate-600">
      {label}
      <input
        required={required}
        name={name}
        pattern={pattern}
        inputMode={inputMode}
        className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-red-400"
        placeholder={placeholder}
      />
    </label>
  );
}
