"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { CandidateDocument, CandidateProfile, managementApi } from "@/lib/managementApi";

const DOCUMENT_STATUS: Record<string, string> = {
  received: "Đang xử lý",
  unreadable: "Chưa đọc được chữ",
  failed: "Đọc hỏng",
};

const STATUS_LABELS: Record<string, string> = {
  extracted: "Chờ ứng viên xác nhận",
  confirmed: "Đã xác nhận",
};

const STATUS_STYLES: Record<string, string> = {
  extracted: "bg-amber-50 text-amber-700 ring-amber-200",
  confirmed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

function cellText(profile: CandidateProfile, key: string): string {
  const label = profile.labels?.[key];
  if (label) return label;
  const cell = profile.fields?.[key];
  if (!cell || cell.value === null || cell.value === undefined) return "—";
  return String(cell.value);
}

export default function CandidateProfilesPage() {
  const [profiles, setProfiles] = useState<CandidateProfile[]>([]);
  const [status, setStatus] = useState("");
  const [orphans, setOrphans] = useState<CandidateDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    managementApi
      .candidateProfiles({ status: status || undefined })
      .then(setProfiles)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));

    // Tư vấn viên không được xem danh sách này (403). Đó là chuyện bình thường,
    // không phải lỗi — nên nuốt và để trống, không làm hỏng cả trang.
    managementApi
      .documents()
      .then((items) =>
        setOrphans(items.filter((item) => item.profile_code === null)),
      )
      .catch(() => setOrphans([]));
  }, [status]);

  useEffect(load, [load]);

  return (
    <>
      <PageHeader
        eyebrow="Ứng viên"
        title="Hồ sơ ứng viên"
        description="Toàn bộ hồ sơ năng lực đã dựng được, dù ứng viên tự khai hay do hệ thống đọc từ CV gửi lên. Hồ sơ chỉ được đem đi đối chiếu đơn hàng sau khi chính ứng viên xác nhận là đúng."
      />
      {error && <ErrorBanner message={error} />}

      <section className="mb-6 flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Trạng thái
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700"
          >
            <option value="">Tất cả</option>
            <option value="extracted">Chờ ứng viên xác nhận</option>
            <option value="confirmed">Đã xác nhận</option>
          </select>
        </label>
        <button
          type="button"
          onClick={load}
          className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Tải lại
        </button>
      </section>

      {orphans.length > 0 && (
        <section className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="text-sm font-semibold text-amber-800">
            {orphans.length} tài liệu chưa dựng được hồ sơ
          </h3>
          <p className="mt-1 text-xs leading-5 text-amber-700">
            Ảnh chụp và bản scan hiện chưa đọc được chữ, nên chúng không thuộc hồ sơ
            nào. File vẫn được lưu đầy đủ — mở ra đọc rồi nhập tay giúp ứng viên.
          </p>
          <ul className="mt-3 space-y-2">
            {orphans.map((document) => (
              <li
                key={document.code}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl bg-white/70 px-3 py-2 text-xs"
              >
                <span className="font-medium text-slate-700">{document.filename}</span>
                <span className="text-slate-400">{document.content_type}</span>
                <span className="text-amber-700">
                  {DOCUMENT_STATUS[document.status] || document.status}
                </span>
                <span className="text-slate-400">
                  {new Date(document.created_at).toLocaleString("vi-VN")}
                </span>
                <a
                  href={managementApi.documentOriginalUrl(document.code)}
                  className="ml-auto font-medium text-[#cb1d1e] hover:underline"
                >
                  Mở file ↓
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {loading ? (
        <p className="text-sm text-slate-400">Đang tải…</p>
      ) : profiles.length === 0 ? (
        <EmptyState
          title="Chưa có hồ sơ nào"
          description="Hồ sơ xuất hiện ở đây khi ứng viên gửi CV trong khung chat hoặc tự khai thông tin trên web."
        />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Mã</th>
                <th className="px-4 py-3">Họ tên</th>
                <th className="px-4 py-3">Tiếng Nhật</th>
                <th className="px-4 py-3">Bằng cấp</th>
                <th className="px-4 py-3">Trạng thái</th>
                <th className="px-4 py-3">Người phụ trách</th>
                <th className="px-4 py-3">Cập nhật</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {profiles.map((profile) => (
                <tr key={profile.code} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/admin/profiles/${profile.code}`}
                      className="font-medium text-[#cb1d1e] hover:underline"
                    >
                      {profile.code}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {cellText(profile, "full_name")}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {cellText(profile, "japanese_level")}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {cellText(profile, "education_level")}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${
                        STATUS_STYLES[profile.status] ||
                        "bg-slate-50 text-slate-600 ring-slate-200"
                      }`}
                    >
                      {STATUS_LABELS[profile.status] || profile.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {profile.assigned_to || "Chưa giao"}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {new Date(profile.updated_at).toLocaleString("vi-VN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
