/** Định dạng hiển thị dùng chung cho website khách hàng. */

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [year, month, day] = iso.split("-");
  if (!year || !month || !day) return iso;
  return `${day}/${month}/${year}`;
}

/**
 * Lương ghi bằng nghìn yên thay vì con số đầy đủ: "195.000 ¥" dài và khó so
 * sánh nhanh giữa các đơn, trong khi "195 nghìn ¥" đọc lướt là thấy ngay.
 */
export function formatSalaryRange(
  min: number | null,
  max: number | null,
): string {
  if (!min && !max) return "Thỏa thuận";
  const toThousand = (value: number) => Math.round(value / 1000);
  if (min && max && min !== max) {
    return `${toThousand(min)}–${toThousand(max)} nghìn ¥`;
  }
  return `${toThousand((min || max) as number)} nghìn ¥`;
}

export function formatVnd(value: number | null): string {
  if (!value) return "Liên hệ";
  if (value >= 1_000_000) {
    const millions = value / 1_000_000;
    const rounded = Number.isInteger(millions) ? millions : millions.toFixed(1);
    return `${String(rounded).replace(".", ",")} triệu đ`;
  }
  return `${value.toLocaleString("vi-VN")} đ`;
}

export function formatYears(value: number): string {
  if (!value) return "Không yêu cầu";
  const text = Number.isInteger(value) ? String(value) : String(value).replace(".", ",");
  return `${text} năm`;
}

/**
 * Số ngày còn lại tới hạn nộp. Trả về `null` khi đã quá hạn, để nơi gọi tự
 * quyết định hiển thị thế nào thay vì nhận một số âm khó hiểu.
 */
export function daysUntil(iso: string): number | null {
  const deadline = new Date(`${iso}T00:00:00+07:00`).getTime();
  const today = new Date().getTime();
  const days = Math.ceil((deadline - today) / 86_400_000);
  return days < 0 ? null : days;
}

export function ageRangeText(
  min: number | null,
  max: number | null,
): string {
  if (min && max) return `${min}–${max} tuổi`;
  if (min) return `Từ ${min} tuổi`;
  if (max) return `Đến ${max} tuổi`;
  return "Không giới hạn";
}
