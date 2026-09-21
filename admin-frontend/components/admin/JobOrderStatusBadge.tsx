import { JobOrder } from "@/lib/managementApi";

// Nhãn tiếng Việt lấy từ backend chứ không chép lại ở đây. Giữ bảng nhãn ở hai
// nơi là cách chắc chắn để chúng lệch nhau sau vài lần sửa.
const TONE: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600 ring-slate-200",
  open: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  paused: "bg-amber-50 text-amber-700 ring-amber-200",
  filled: "bg-blue-50 text-blue-700 ring-blue-200",
  expired: "bg-orange-50 text-orange-700 ring-orange-200",
  closed: "bg-slate-200 text-slate-600 ring-slate-300",
};

export function JobOrderStatusBadge({ order }: { order: JobOrder }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${
        TONE[order.status] || "bg-violet-50 text-violet-700 ring-violet-200"
      }`}
    >
      {order.labels.status || order.status}
    </span>
  );
}

/**
 * Một đơn chỉ thật sự lên website khi đồng thời đủ ba điều: bật công khai, đang
 * tuyển, và còn hạn nộp. Nhân viên hay bật công khai rồi tưởng đơn đã hiển thị,
 * nên trạng thái này cần nói thẳng ra thay vì chỉ hiện một dấu tích.
 */
export function PublicVisibilityBadge({
  order,
  today,
}: {
  order: JobOrder;
  today: string;
}) {
  if (!order.published) {
    return (
      <span className="text-xs text-slate-400">Chưa công khai</span>
    );
  }
  if (order.status !== "open") {
    return (
      <span className="text-xs text-amber-700">
        Đã bật công khai nhưng {(order.labels.status || "").toLowerCase()}
      </span>
    );
  }
  if (order.deadline < today) {
    return (
      <span className="text-xs text-orange-700">
        Đã bật công khai nhưng quá hạn nộp
      </span>
    );
  }
  return (
    <span className="text-xs font-medium text-emerald-700">
      Đang hiển thị trên website
    </span>
  );
}
