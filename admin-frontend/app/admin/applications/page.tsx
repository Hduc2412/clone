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
  ["visa_processing", "Đang làm visa"],
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
  const [soTuyenCode, setSoTuyenCode] = useState<string | null>(null);
  const [canhBao, setCanhBao] = useState("");

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

  const ghiSoTuyen = async (code: string, form: HTMLFormElement) => {
    const data = new FormData(form);
    setError("");
    setCanhBao("");
    try {
      const ra = await managementApi.recordScreening(code, {
        japanese_level: String(data.get("japanese_level")),
        chung_cu: String(data.get("chung_cu")) as "ban_goc",
        hinh_thuc: String(data.get("hinh_thuc")) as "truc_tiep",
        next_status: String(data.get("next_status")),
        note: String(data.get("note") || "") || undefined,
      });
      // Cảnh báo không phải lỗi: hồ sơ đã lưu, nhưng trình độ vẫn là lời khai vì
      // ứng viên không xuất trình được gì. Phải hiện ra, không được lặng lẽ bỏ.
      if (ra.canh_bao) setCanhBao(ra.canh_bao);
      setSoTuyenCode(null);
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không ghi được kết quả sơ tuyển.");
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

      {canhBao && (
        <p className="mb-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200">
          {canhBao}
        </p>
      )}

      {soTuyenCode && <SoTuyenForm code={soTuyenCode} onSubmit={ghiSoTuyen} onCancel={() => setSoTuyenCode(null)} />}

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
                    <td className="px-5 py-4"><div className="flex items-center gap-3"><StatusBadge status={application.status} /><select aria-label={`Chuyển trạng thái hồ sơ ${application.application_code}`} value={application.status} disabled={(allowedTransitions[application.status] || []).length === 0} onChange={(event) => updateStatus(application, event.target.value)} className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs disabled:cursor-not-allowed disabled:bg-slate-100"><option value={application.status}>{statusLabels[application.status] || application.status}</option>{(allowedTransitions[application.status] || []).map((value) => <option key={value} value={value}>{statusLabels[value] || value}</option>)}</select>{application.status === "screening" && <button type="button" onClick={() => setSoTuyenCode(soTuyenCode === application.application_code ? null : application.application_code)} className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">{soTuyenCode === application.application_code ? "Đóng" : "Ghi kết quả sơ tuyển"}</button>}</div></td>
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

/**
 * Biểu mẫu ghi kết quả buổi sơ tuyển.
 *
 * Một lần gửi đổi hai thứ: trình độ tiếng Nhật trong hồ sơ năng lực, và trạng
 * thái hồ sơ tuyển dụng. Máy chủ kiểm hết trước khi ghi bất cứ thứ gì, và chuyển
 * trạng thái vẫn đi qua đúng máy trạng thái như đường sửa hồ sơ thường.
 *
 * Không có ô nào để tải ảnh chụp bằng, và đó là chủ ý: nhìn ảnh không phân biệt
 * được bằng thật với bằng giả, còn ngồi đối diện thì hỏi vài câu tiếng Nhật là
 * biết ngay. Thêm một loại giấy tờ cá nhân vào kho là thêm một thứ để mất.
 */
function SoTuyenForm({
  code,
  onSubmit,
  onCancel,
}: {
  code: string;
  onSubmit: (code: string, form: HTMLFormElement) => void;
  onCancel: () => void;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(code, event.currentTarget);
      }}
      className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <h2 className="text-base font-bold text-slate-900">
        Kết quả buổi sơ tuyển · {code}
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Một lần lưu chốt cả trình độ tiếng Nhật lẫn trạng thái hồ sơ, để hai chỗ
        không nói hai điều khác nhau về cùng một người.
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <SelectField name="japanese_level" label="Trình độ tiếng Nhật đã xác định" required>
          {["chua_hoc", "N5", "N4", "N3", "N2", "N1"].map((muc) => (
            <option key={muc} value={muc}>
              {muc === "chua_hoc" ? "Chưa học" : muc}
            </option>
          ))}
        </SelectField>

        <SelectField name="chung_cu" label="Đối chứng bằng cách nào" required>
          <option value="ban_goc">Ứng viên cầm bằng gốc</option>
          <option value="tra_cuu_truc_tuyen">Tra kết quả trên trang chính thức</option>
          <option value="khong_xuat_trinh">Không xuất trình được gì</option>
        </SelectField>

        <SelectField name="hinh_thuc" label="Hình thức gặp" required>
          <option value="truc_tiep">Gặp trực tiếp</option>
          <option value="truc_tuyen">Gặp trực tuyến</option>
        </SelectField>

        <SelectField name="next_status" label="Trạng thái hồ sơ sau buổi gặp" required>
          <option value="eligible">Đạt sơ tuyển</option>
          <option value="collecting_documents">Còn thiếu giấy tờ</option>
          <option value="rejected">Không đạt</option>
        </SelectField>
      </div>

      <label className="mt-4 block text-sm font-medium text-slate-600">
        Ghi chú buổi gặp
        <textarea
          name="note"
          rows={3}
          placeholder="Nói được câu chào và giới thiệu bản thân, phát âm rõ. Có bằng N4 gốc, số báo danh khớp khi tra trên trang JLPT."
          className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-red-400"
        />
      </label>

      <p className="mt-3 text-xs text-slate-500">
        Chọn <b>&ldquo;Không xuất trình được gì&rdquo;</b> thì trình độ vẫn được ghi là{" "}
        <b>tự khai</b>, kể cả khi bạn cho hồ sơ đi tiếp — để người sau biết trình độ
        này chưa có căn cứ nào chống lưng.
      </p>

      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white"
        >
          Lưu kết quả
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600"
        >
          Hủy
        </button>
      </div>
    </form>
  );
}
