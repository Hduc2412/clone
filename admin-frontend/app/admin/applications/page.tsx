"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader, StatusBadge } from "@/components/admin/AdminUI";
import {
  ManagedLead,
  RecruitmentApplication,
  StaffUser,
  managementApi,
} from "@/lib/managementApi";
import { loadCurrentUser } from "@/lib/auth";

const statuses = [
  ["draft", "Mới tạo"],
  ["collecting_documents", "Thu giấy tờ"],
  ["screening", "Sơ tuyển"],
  ["eligible", "Đủ điều kiện"],
  ["training", "Đang đào tạo"],
  ["waiting_interview", "Chờ phỏng vấn"],
  ["passed", "Đã trúng tuyển"],
  ["visa_processing", "Làm visa"],
  ["ready_departure", "Chờ xuất cảnh"],
  ["departed", "Đã xuất cảnh"],
  ["rejected", "Không đạt"],
  ["withdrawn", "Khách rút hồ sơ"],
  ["cancelled", "Đã hủy"],
];

const allowedTransitions: Record<string, string[]> = {
  draft: ["collecting_documents", "withdrawn", "cancelled"],
  collecting_documents: ["screening", "withdrawn", "cancelled"],
  screening: ["collecting_documents", "eligible", "rejected", "withdrawn", "cancelled"],
  eligible: ["training", "waiting_interview", "withdrawn", "cancelled"],
  training: ["waiting_interview", "withdrawn", "cancelled"],
  waiting_interview: ["training", "passed", "rejected", "withdrawn", "cancelled"],
  passed: ["visa_processing", "withdrawn", "cancelled"],
  visa_processing: ["ready_departure", "withdrawn", "cancelled"],
  ready_departure: ["departed", "withdrawn", "cancelled"],
  departed: [],
  rejected: [],
  withdrawn: [],
  cancelled: [],
};

const statusLabels = Object.fromEntries(statuses);

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<RecruitmentApplication[]>([]);
  const [leads, setLeads] = useState<ManagedLead[]>([]);
  const [users, setUsers] = useState<StaffUser[]>([]);
  const [status, setStatus] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [canManage, setCanManage] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    managementApi
      .applications({ status, activeOnly })
      .then(setApplications)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [activeOnly, status]);

  useEffect(load, [load]);
  useEffect(() => {
    loadCurrentUser()
      .then(async (user) => {
        const allowed = user.role === "admin" || user.role === "manager";
        setCanManage(allowed);
        if (!allowed) return;
        const [leadRows, userRows] = await Promise.all([
          managementApi.leads(),
          managementApi.users(),
        ]);
        setLeads(leadRows);
        setUsers(userRows.filter((staff) => staff.status === "active"));
      })
      .catch(() => undefined);
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await managementApi.createApplication({
        lead_code: String(form.get("lead_code") || ""),
        assigned_to: String(form.get("assigned_to") || "") || undefined,
        destination: String(form.get("destination") || "") || undefined,
        japanese_level: String(form.get("japanese_level") || "") || undefined,
        qualification: String(form.get("qualification") || "") || undefined,
        note: String(form.get("note") || "") || undefined,
      });
      event.currentTarget.reset();
      setShowForm(false);
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tạo hồ sơ.");
    }
  };

  const updateStatus = async (application: RecruitmentApplication, nextStatus: string) => {
    try {
      await managementApi.updateApplication(application.application_code, { status: nextStatus });
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật hồ sơ.");
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Quy trình tuyển dụng"
        title="Hồ sơ tuyển dụng"
        description="Theo dõi từng lần khách hàng tham gia quy trình. Mỗi khách chỉ có một hồ sơ đang hoạt động."
        action={canManage ? (
          <button
            onClick={() => setShowForm((value) => !value)}
            className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white"
          >
            {showForm ? "Đóng biểu mẫu" : "Tạo hồ sơ"}
          </button>
        ) : undefined}
      />
      {error && <ErrorBanner message={error} />}

      {showForm && canManage && (
        <form onSubmit={submit} className="mb-6 grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2 xl:grid-cols-3">
          <SelectField name="lead_code" label="Khách hàng" required>
            <option value="">Chọn khách hàng</option>
            {leads.map((lead) => <option key={lead.lead_code} value={lead.lead_code}>{lead.customer_name} · {lead.phone}</option>)}
          </SelectField>
          <SelectField name="assigned_to" label="Nhân viên phụ trách">
            <option value="">Theo người phụ trách khách hàng</option>
            {users.map((user) => <option key={user.email} value={user.email}>{user.full_name}</option>)}
          </SelectField>
          <InputField name="destination" label="Nơi mong muốn" placeholder="Tokyo, Osaka..." />
          <InputField name="japanese_level" label="Trình độ tiếng Nhật" placeholder="Chưa có, N5, N4..." />
          <InputField name="qualification" label="Trình độ/chứng chỉ" placeholder="Cao đẳng điều dưỡng..." />
          <InputField name="note" label="Ghi chú nội bộ" placeholder="Thông tin cần theo dõi" />
          <button className="rounded-xl bg-[#171b22] px-4 py-2.5 text-sm font-medium text-white md:col-span-2 xl:col-span-3">Lưu hồ sơ tuyển dụng</button>
        </form>
      )}

      <section className="mb-6 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <select value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm">
          <option value="">Tất cả trạng thái</option>
          {statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={activeOnly} onChange={(event) => setActiveOnly(event.target.checked)} />
          Chỉ hồ sơ đang hoạt động
        </label>
      </section>

      {!loading && applications.length === 0 ? (
        <EmptyState title="Chưa có hồ sơ tuyển dụng" description="Tạo hồ sơ từ một khách hàng đã được xác nhận đủ nhu cầu tham gia." />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{["Khách hàng", "Hồ sơ", "Thông tin", "Phụ trách", "Trạng thái"].map((label) => <th key={label} className="px-5 py-3.5">{label}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-100">
                {applications.map((application) => (
                  <tr key={application.application_code} className="hover:bg-slate-50/70">
                    <td className="px-5 py-4"><p className="font-medium">{application.customer_name}</p><a href={`tel:${application.phone}`} className="mt-1 block text-xs text-[#cb1d1e]">{application.phone}</a></td>
                    <td className="px-5 py-4"><p className="font-medium">{application.application_code}</p><p className="mt-1 text-xs text-slate-400">{application.lead_code}</p></td>
                    <td className="px-5 py-4 text-slate-500"><p>{application.destination || "Chưa có địa điểm"}</p><p className="mt-1 text-xs">Tiếng Nhật: {application.japanese_level || "Chưa cập nhật"}</p></td>
                    <td className="px-5 py-4 text-slate-500">{application.assigned_to || "Chưa phân công"}</td>
                    <td className="px-5 py-4"><div className="flex items-center gap-3"><StatusBadge status={application.status} /><select aria-label={`Chuyển trạng thái hồ sơ ${application.application_code}`} value={application.status} disabled={(allowedTransitions[application.status] || []).length === 0} onChange={(event) => updateStatus(application, event.target.value)} className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs disabled:cursor-not-allowed disabled:bg-slate-100"><option value={application.status}>{statusLabels[application.status] || application.status}</option>{(allowedTransitions[application.status] || []).map((value) => <option key={value} value={value}>{statusLabels[value] || value}</option>)}</select></div></td>
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

function InputField({ name, label, placeholder }: { name: string; label: string; placeholder: string }) {
  return <label className="text-sm font-medium text-slate-600">{label}<input name={name} placeholder={placeholder} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-red-400" /></label>;
}

function SelectField({ name, label, required = false, children }: { name: string; label: string; required?: boolean; children: React.ReactNode }) {
  return <label className="text-sm font-medium text-slate-600">{label}<select name={name} required={required} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none">{children}</select></label>;
}
