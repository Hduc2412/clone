/**
 * Thanh bước của luồng tư vấn chuyên sâu (yêu cầu 08/10).
 *
 * Khách đi theo một đường nhìn thấy được thay vì một khung chat dài: gửi CV → làm rõ
 * → xác nhận → bảng đối chiếu → phân tích → việc tiếp theo. Thanh này chỉ để khách
 * biết mình đang ở đâu; nó không phải nút điều hướng — nhảy cóc qua bước xác nhận
 * là đúng thứ luồng này cố ngăn.
 */

export const BUOC = [
  "Gửi CV",
  "Làm rõ thông tin",
  "Xác nhận hồ sơ",
  "Đối chiếu với đơn",
  "Phân tích",
  "Việc tiếp theo",
] as const;

/** Chỉ số bước đang ở, tính từ trạng thái thật của luồng — không để trang tự đếm. */
export function buocHienTai({
  coHoSo,
  daXacNhan,
  coKetQua,
}: {
  coHoSo: boolean;
  daXacNhan: boolean;
  coKetQua: boolean;
}): number {
  if (coKetQua && daXacNhan) return 3;
  if (daXacNhan) return 2;
  if (coHoSo) return 1;
  return 0;
}

export default function BuocTuVan({ hienTai }: { hienTai: number }) {
  // Hình thức theo bản thiết kế 08/10: số trong vòng tròn, bước đang ở màu đỏ trầm.
  return (
    <nav aria-label="Các bước tư vấn">
      <ol className="flex flex-wrap items-center gap-x-5 gap-y-3 text-[11px] text-[#718079] sm:justify-between sm:text-xs">
        {BUOC.map((ten, i) => {
          const xong = i < hienTai;
          const dangO = i === hienTai;
          return (
            <li
              key={ten}
              aria-current={dangO ? "step" : undefined}
              className={`flex items-center gap-2 ${dangO ? "font-semibold text-brand-600" : xong ? "text-slate-700" : ""}`}
            >
              <span
                aria-hidden
                className={`grid h-[22px] w-[22px] place-items-center rounded-full text-[11px] sm:h-[26px] sm:w-[26px] ${
                  dangO ? "bg-brand-600 text-white" : xong ? "bg-reu-600 text-white" : "bg-[#e4ebe2] text-[#436451]"
                }`}
              >
                {xong ? "✓" : i + 1}
              </span>
              <span>{ten}</span>
              {xong && <span className="sr-only">(đã xong)</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
