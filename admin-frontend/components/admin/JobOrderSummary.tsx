/**
 * Nội dung đơn, chỉ đọc — cho nhân viên tư vấn (consultant).
 *
 * Biểu mẫu sửa chỉ hiện cho Admin/Manager, nên trước 09/10 consultant mở trang chi
 * tiết đơn chỉ thấy trạng thái và hạn nộp: phải tư vấn một đơn mà không đọc được
 * đơn ấy cần gì, lương bao nhiêu, tổng chi phí bao nhiêu.
 *
 * Hai nhóm tách như trên biểu mẫu và như bộ đối chiếu: **điều kiện bắt buộc** (thứ
 * loại ứng viên) và **thông tin tham khảo** (chỉ để hiển thị và xếp hạng). Gộp lại
 * thì nhân viên dễ nói với khách "lương thấp hơn mong muốn nên chưa đạt" — sai luật.
 *
 * Nhãn lấy từ `order.labels` máy chủ gửi kèm, không tự dựng lại bảng danh mục.
 * Không có `internal_note` ở đây: máy chủ đã gỡ khỏi bản trả cho consultant.
 */
import type { JobOrder } from "@/lib/managementApi";

const CHUA_CO = "Chưa có thông tin";

function yen(so: number | null): string | null {
  return so == null ? null : `${so.toLocaleString("vi-VN")} ¥`;
}

export function luongText(min: number | null, max: number | null): string {
  if (min == null && max == null) return CHUA_CO;
  if (min != null && max != null && min !== max) return `${yen(min)} – ${yen(max)} / tháng`;
  return `${yen(min ?? max)} / tháng`;
}

export function tuoiText(min: number | null, max: number | null): string {
  if (min == null && max == null) return "Không giới hạn";
  if (min != null && max != null) return `${min}–${max} tuổi`;
  return min != null ? `Từ ${min} tuổi` : `Đến ${max} tuổi`;
}

function Dong({ nhan, giaTri }: { nhan: string; giaTri: string | null | undefined }) {
  const co = Boolean(giaTri && giaTri.trim());
  return (
    <div>
      <dt className="text-xs text-slate-500">{nhan}</dt>
      <dd className={`mt-0.5 text-sm ${co ? "text-slate-900" : "text-slate-400"}`}>{co ? giaTri : CHUA_CO}</dd>
    </div>
  );
}

export default function JobOrderSummary({ order }: { order: JobOrder }) {
  const yc = order.requirements;
  const tk = order.reference;
  const nhan = order.labels;
  return (
    <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-label="Nội dung đơn">
      <h3 className="text-sm font-semibold text-slate-900">Nội dung đơn</h3>
      <p className="mt-1 text-xs text-slate-500">
        Chỉ đọc. Muốn sửa nội dung đơn thì báo Admin hoặc Manager.
      </p>

      <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Dong nhan="Loại hình cơ sở" giaTri={nhan.employer_type ?? order.employer_type} />
        <Dong nhan="Diện chương trình" giaTri={nhan.program ?? order.program} />
        <Dong
          nhan="Nơi làm việc"
          giaTri={[order.city, order.prefecture, nhan.region_group].filter(Boolean).join(" · ")}
        />
        <Dong nhan="Số lượng tuyển" giaTri={`${order.quota} (đã tuyển ${order.hired_count})`} />
      </dl>

      <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50/60 p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-amber-900">Điều kiện bắt buộc</h4>
        <p className="mt-0.5 text-xs text-amber-900/80">Không đáp ứng thì bộ đối chiếu loại ứng viên khỏi đơn này.</p>
        <dl className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Dong nhan="Tiếng Nhật" giaTri={nhan.japanese_required ? `Từ ${nhan.japanese_required}` : yc.japanese_required} />
          <Dong nhan="Bằng cấp" giaTri={nhan.education_required ?? (yc.education_required ? yc.education_required : "Không yêu cầu")} />
          <Dong nhan="Kinh nghiệm" giaTri={yc.experience_min > 0 ? `Từ ${yc.experience_min} năm` : "Không yêu cầu"} />
          <Dong nhan="Độ tuổi" giaTri={tuoiText(yc.age_min, yc.age_max)} />
          <Dong nhan="Giới tính" giaTri={nhan.gender_pref ?? yc.gender_pref} />
          <Dong nhan="Hạn nộp hồ sơ" giaTri={order.deadline} />
        </dl>
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Thông tin tham khảo</h4>
        <p className="mt-0.5 text-xs text-slate-500">Chỉ để hiển thị và xếp hạng theo nguyện vọng — không loại ai.</p>
        <dl className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Dong nhan="Lương" giaTri={luongText(tk.salary_min, tk.salary_max)} />
          <Dong
            nhan="Tổng chi phí chương trình"
            giaTri={tk.cost_total_vnd != null ? `${tk.cost_total_vnd.toLocaleString("vi-VN")} đ` : null}
          />
          <Dong nhan="Phụ cấp" giaTri={tk.allowances.join(", ")} />
          <Dong nhan="Ngày phỏng vấn" giaTri={tk.interview_date} />
          <Dong nhan="Dự kiến xuất cảnh" giaTri={tk.departure_expected} />
          <Dong nhan="Điểm nổi bật" giaTri={tk.highlights.join(" · ")} />
        </dl>
      </div>

      {order.description?.trim() && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Mô tả</h4>
          <p className="mt-1 whitespace-pre-line text-sm leading-6 text-slate-700">{order.description}</p>
        </div>
      )}
    </section>
  );
}
