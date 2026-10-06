"use client";

/**
 * Kết quả tư vấn cho **một đơn** — phần khách đọc sau khi khai hồ sơ.
 *
 * Thiết kế theo một nguyên tắc: người đọc phải thấy được **hệ thống biết gì** và
 * **suy ra thế nào**, không chỉ thấy một kết luận. Nên câu văn của mô hình đứng
 * trên, còn bảng từng tiêu chí nằm ngay dưới và mở ra được — ai muốn tin thì đọc
 * câu, ai muốn kiểm thì mở bảng.
 *
 * Ba chỗ cố ý làm khác lẽ thường:
 *
 * - **Nói rõ câu đang hiện do ai viết.** Có nhãn "mô hình viết lại" hoặc "hệ
 *   thống ghép". Người dùng nên biết mình đang đọc gì, và khi bảo vệ thì đây là
 *   chỗ mở ra so hai bản cạnh nhau.
 * - **Đơn chưa đạt thì không hiện điểm.** Ghi "45/100 · chưa đạt" cạnh nhau là
 *   mời người đọc đem đi so sánh với đơn khác, trong khi con số ấy vô nghĩa khi
 *   đã trượt điều kiện bắt buộc.
 * - **Học phí không bao giờ đứng một mình.** Luôn kèm tổng chi phí chương trình,
 *   vì 35 triệu là một chặng của 90 triệu — hiện trơ trọi là để khách chuẩn bị
 *   thiếu tiền.
 */

import { useState } from "react";
import type { CriterionRow, OrderAdvice } from "@/lib/candidateApi";

const NHAN_KET_QUA: Record<string, { chu: string; mau: string }> = {
  DAT: { chu: "Đạt", mau: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  KHONG_DAT: { chu: "Chưa đạt", mau: "bg-red-50 text-red-700 ring-red-200" },
  CHUA_RO: { chu: "Chưa rõ", mau: "bg-amber-50 text-amber-700 ring-amber-200" },
};

const VIEN_NHANH: Record<OrderAdvice["branch"], string> = {
  phu_hop: "border-emerald-300 bg-emerald-50/60",
  chua_phu_hop: "border-red-200 bg-red-50/50",
  thieu_thong_tin: "border-amber-200 bg-amber-50/50",
};

function tien(so: number | null): string {
  if (!so) return "—";
  return `${so.toLocaleString("vi-VN")}đ`;
}

function BangTieuChi({ rows }: { rows: CriterionRow[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="py-2 pr-3 font-medium">Tiêu chí</th>
            <th className="py-2 pr-3 font-medium">Đơn yêu cầu</th>
            <th className="py-2 pr-3 font-medium">Hồ sơ của bạn</th>
            <th className="py-2 font-medium">Kết quả</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const nhan = NHAN_KET_QUA[row.result] ?? NHAN_KET_QUA.CHUA_RO;
            return (
              <tr key={row.key} className="border-b border-slate-100 align-top">
                <td className="py-2.5 pr-3 font-medium text-slate-700">{row.label}</td>
                <td className="py-2.5 pr-3 text-slate-600">{row.requirement_text}</td>
                <td className="py-2.5 pr-3 text-slate-600">{row.candidate_text}</td>
                <td className="py-2.5">
                  <span
                    className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${nhan.mau}`}
                  >
                    {nhan.chu}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function OrderAdvicePanel({
  advice,
  onRegister,
  onAskStaff,
  onAskLearning,
  registering,
}: {
  advice: OrderAdvice;
  onRegister?: () => void;
  onAskStaff?: () => void;
  onAskLearning?: () => void;
  registering?: boolean;
}) {
  const [moBang, setMoBang] = useState(false);
  const [moBanGoc, setMoBanGoc] = useState(false);

  const tatCaDong = [...advice.blockers, ...advice.unknowns, ...advice.strengths];
  const lo = advice.learning;

  return (
    <section className="space-y-5">
      {/* --- Kết luận --- */}
      <div className={`rounded-2xl border p-5 ${VIEN_NHANH[advice.branch]}`}>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              {advice.order_code}
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">
              {advice.order_title}
            </h2>
          </div>
          {/* Đơn chưa đạt thì không hiện điểm — xem docstring đầu file. */}
          {advice.branch === "phu_hop" && advice.score_ranked !== false && (
            <p className="text-right">
              <span className="text-2xl font-semibold text-slate-900">{advice.score}</span>
              <span className="ml-1 text-xs text-slate-500">/100 điểm phù hợp</span>
            </p>
          )}
          {/* Chưa nêu nguyện vọng thì nói thẳng là chưa xếp hạng được, đừng
              hiện một con số đo mức khớp với thứ chưa tồn tại. */}
          {advice.branch === "phu_hop" && advice.score_ranked === false && (
            <p className="max-w-[11rem] text-right text-xs leading-5 text-slate-500">
              Chưa xếp hạng được — bạn nêu khu vực hoặc loại cơ sở mong muốn để
              hệ thống so thứ tự giữa các đơn.
            </p>
          )}
        </div>

        <p className="mt-3 text-sm font-medium text-slate-700">{advice.branch_label}</p>

        <p className="mt-3 leading-7 text-slate-700">{advice.text}</p>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
          <span className="rounded-full bg-white/70 px-2.5 py-1 ring-1 ring-slate-200">
            {advice.text_source === "mo_hinh"
              ? "Đoạn trên do trợ lý viết lại từ kết quả đối chiếu"
              : "Đoạn trên do hệ thống ghép từ kết quả đối chiếu"}
          </span>
          {advice.text_source === "mo_hinh" && (
            <button
              type="button"
              onClick={() => setMoBanGoc((mo) => !mo)}
              className="underline decoration-dotted hover:text-slate-700"
            >
              {moBanGoc ? "Ẩn bản hệ thống ghép" : "Xem bản hệ thống ghép"}
            </button>
          )}
        </div>

        {moBanGoc && (
          <p className="mt-3 rounded-xl bg-white/80 p-3 text-sm leading-6 text-slate-600 ring-1 ring-slate-200">
            {advice.text_template}
          </p>
        )}
      </div>

      {/* --- Cần hỏi thêm --- */}
      {advice.questions.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5">
          <h3 className="font-semibold text-slate-900">Khai thêm mấy mục này thì kết quả chắc hơn</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Thiếu thông tin không làm bạn mất đơn nào — hệ thống để “chưa rõ” chứ không loại.
          </p>
          <ul className="mt-3 space-y-1.5 text-sm text-slate-700">
            {advice.questions.map((cau) => (
              <li key={cau} className="flex gap-2">
                <span aria-hidden className="text-amber-500">•</span>
                <span>{cau}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* --- Bảng từng tiêu chí --- */}
      {tatCaDong.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <button
            type="button"
            onClick={() => setMoBang((mo) => !mo)}
            aria-expanded={moBang}
            className="text-sm font-semibold text-[#cb1d1e] hover:underline"
          >
            {moBang ? "Thu gọn bảng tiêu chí" : "Xem từng tiêu chí đạt hay chưa"}
          </button>
          {moBang && (
            <div className="mt-4">
              <BangTieuChi rows={tatCaDong} />
            </div>
          )}
        </div>
      )}

      {/* --- Lộ trình học --- */}
      {lo && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="font-semibold text-slate-900">
            Cần học gì để đủ điều kiện đơn này
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            Từ {lo.level_from_label} lên {lo.level_to_label}
          </p>

          <dl className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Thời gian học</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900">{lo.months_text}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Học phí</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900">
                {lo.tuition_incomplete ? "Nhân viên sẽ báo lại" : tien(lo.tuition_vnd)}
              </dd>
              {/* Học phí không bao giờ đứng một mình — xem docstring đầu file. */}
              {!lo.tuition_incomplete && lo.package_total_vnd && (
                <dd className="mt-1 text-xs leading-5 text-slate-500">
                  Là một chặng trong tổng chi phí chương trình{" "}
                  {tien(lo.package_total_vnd)}
                </dd>
              )}
            </div>
          </dl>

          <ul className="mt-4 space-y-2 text-sm text-slate-700">
            {lo.courses.map((khoa) => (
              <li key={khoa.code} className="rounded-xl bg-slate-50 p-3">
                <p className="font-medium">{khoa.title}</p>
                {khoa.format && (
                  <p className="mt-1 text-xs leading-5 text-slate-500">{khoa.format}</p>
                )}
              </li>
            ))}
          </ul>

          {onAskLearning && (
            <button
              type="button"
              onClick={onAskLearning}
              className="mt-4 rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#b01819]"
            >
              Tôi muốn được tư vấn về việc học
            </button>
          )}
        </div>
      )}

      {/* --- Vì sao không có lộ trình --- */}
      {!lo && advice.learning_note && (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <h3 className="font-semibold text-slate-900">Về việc học thêm</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{advice.learning_note}</p>
        </div>
      )}

      {/* --- Điều kiện sức khỏe --- */}
      {(advice.branch !== "chua_phu_hop" || lo) && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="font-semibold text-slate-900">Còn một bước khám sức khỏe</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Không nhiễm bệnh truyền nhiễm:{" "}
            <strong>{advice.suc_khoe.benh_loai_tru.join(", ")}</strong>
          </p>
          <p className="mt-2 text-xs leading-5 text-slate-500">{advice.suc_khoe.loi_nhac}</p>
        </div>
      )}

      {/* --- Việc tiếp theo --- */}
      <div className="flex flex-wrap gap-3">
        {advice.can_register && onRegister && (
          <button
            type="button"
            onClick={onRegister}
            disabled={registering}
            className="rounded-xl bg-[#cb1d1e] px-5 py-3 font-semibold text-white disabled:opacity-60"
          >
            {registering ? "Đang gửi…" : "Đăng ký đơn này"}
          </button>
        )}
        {onAskStaff && (
          <button
            type="button"
            onClick={onAskStaff}
            className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:border-[#cb1d1e]"
          >
            Nói chuyện với nhân viên
          </button>
        )}
      </div>

      {/* Nhánh phù hợp nhưng hồ sơ chưa xác nhận: nói rõ vì sao chưa cho đăng ký,
          thay vì chỉ ẩn cái nút đi và để khách tự đoán. */}
      {advice.branch === "phu_hop" && !advice.profile_confirmed && (
        <p className="rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-800 ring-1 ring-amber-200">
          Hồ sơ này hệ thống đọc từ CV của bạn và bạn chưa xem lại. Bạn xác nhận hồ
          sơ trước khi đăng ký nhé — máy có thể đọc nhầm, và hồ sơ đăng ký thì phải
          đúng.
        </p>
      )}
    </section>
  );
}
