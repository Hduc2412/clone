/** Trình bày thông báo — tách khỏi `app/admin/notifications/page.tsx` để kiểm thử được
 * (Next chỉ cho tệp page xuất `default`). */
import type { Notification } from "@/lib/managementApi";

/** Trang Thông báo vừa đánh dấu đã đọc → nút "Thông báo" ở đầu trang nạp lại số ngay,
 * không chờ vòng 30 giây (kiểm trên trình duyệt 12/10: danh sách rỗng mà nút vẫn ghi 53). */
export const SU_KIEN_THONG_BAO = "thong-bao-doi";

export function baoThongBaoDaDoi(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(SU_KIEN_THONG_BAO));
}

/** Mỗi loại việc dẫn về đúng màn hình xử lý nó. */
export function noiXuLy(tb: Notification): string {
  switch (tb.reference_type) {
    case "job_order":
      return `/admin/job-orders/${tb.reference_code}`;
    case "support_request":
      return "/admin/support";
    case "application":
      return "/admin/queue";
    default:
      return "/admin/appointments";
  }
}

/** Thông báo lịch hẹn cũ không có `title` — dựng câu từ các trường của nó. */
export function tieuDe(tb: Notification): string {
  if (tb.title) return tb.title;
  if (tb.appointment_code) {
    return `Lịch hẹn mới${tb.customer_name ? ` — ${tb.customer_name}` : ""}${
      tb.appointment_date ? ` · ${tb.appointment_date} ${tb.appointment_time ?? ""}` : ""
    }`;
  }
  return "Thông báo";
}

export function moTa(tb: Notification): string {
  const d = (tb.detail ?? {}) as Record<string, unknown>;
  const phan: string[] = [];
  if (typeof d.customer_name === "string" && d.customer_name) phan.push(`Khách: ${d.customer_name}`);
  if (typeof d.job_order_code === "string" && d.job_order_code) phan.push(`Đơn ${d.job_order_code}`);
  if (tb.reference_code) phan.push(tb.reference_code);
  return phan.join(" · ");
}

