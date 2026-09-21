import { ReactNode } from "react";

/**
 * Nhãn tiếng Việt cho mọi trạng thái hiện lên trong huy hiệu trạng thái.
 *
 * `StatusBadge` rơi về `|| status` khi thiếu khóa, nghĩa là **thiếu một dòng ở
 * đây thì nhân viên thấy nguyên chuỗi tiếng Anh trong mã nguồn**. Trước đây bảy
 * trạng thái hồ sơ đăng ký thiếu ở bảng này, nên trên `/admin/applications` một
 * hàng hiện ra là `[collecting_documents] [Thu giấy tờ ▾]` — huy hiệu tiếng Anh
 * nằm ngay cạnh ô chọn tiếng Việt của cùng cái trạng thái đó.
 *
 * Bảng này dùng chung cho lịch hẹn, khách hàng, hồ sơ đăng ký và người dùng, nên
 * thêm khóa mới phải kiểm xem tên đó đã mang nghĩa khác ở nơi khác chưa.
 */
export const statusLabels: Record<string, string> = {
  pending: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  completed: "Đã hoàn thành",
  unreachable: "Không liên lạc được",
  rescheduled: "Đã đổi lịch",
  cancelled: "Đã hủy",
  new: "Mới",
  assigned: "Đã phân công",
  contacted: "Đã liên hệ",
  consulting: "Đang tư vấn",
  qualified: "Đủ điều kiện",
  preparing_documents: "Chuẩn bị hồ sơ",
  training: "Đang đào tạo",
  waiting_interview: "Chờ phỏng vấn",
  passed: "Đã trúng tuyển",
  visa_processing: "Đang làm visa",
  departed: "Đã xuất cảnh",
  active: "Hoạt động",
  inactive: "Đã khóa",
  // Trạng thái hồ sơ đăng ký. Bảy dòng dưới đây từng thiếu.
  draft: "Mới tạo",
  collecting_documents: "Thu giấy tờ",
  screening: "Sơ tuyển",
  eligible: "Đủ điều kiện",
  ready_departure: "Chờ xuất cảnh",
  rejected: "Không đạt",
  withdrawn: "Khách rút hồ sơ",
};

const statusStyles: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700 ring-amber-200",
  confirmed: "bg-blue-50 text-blue-700 ring-blue-200",
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  unreachable: "bg-orange-50 text-orange-700 ring-orange-200",
  cancelled: "bg-slate-100 text-slate-600 ring-slate-200",
  new: "bg-red-50 text-red-700 ring-red-200",
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  inactive: "bg-slate-100 text-slate-600 ring-slate-200",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${
        statusStyles[status] || "bg-violet-50 text-violet-700 ring-violet-200"
      }`}
    >
      {statusLabels[status] || status}
    </span>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#cb1d1e]">
          {eyebrow}
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">
          {title}
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          {description}
        </p>
      </div>
      {action}
    </div>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <p className="font-medium text-slate-700">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
        {description}
      </p>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}
