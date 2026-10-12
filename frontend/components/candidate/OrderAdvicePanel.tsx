"use client";

/**
 * Kết quả tư vấn cho **một đơn** — phần khách đọc sau khi khai hồ sơ.
 *
 * ## Bố cục hai cột (bản thiết kế "Hành trình Nhật Bản", 08/10)
 *
 * Cột chính đi theo đúng câu hỏi trong đầu khách (yêu cầu 08/10):
 *
 * 1. **Đối chiếu điều kiện** — bảng từng tiêu chí của đơn đặt cạnh thông tin của
 *    khách, dấu ✓ ở tiêu chí đạt. Hiện sẵn, không phải bấm mở: đây là câu trả lời
 *    chính. Bảng **đứng yên** — không chuyển slide, không gập — vì khách cần đọc và
 *    so từng dòng.
 * 2. **Tư vấn dựa trên hồ sơ** — đoạn phân tích có nhãn ai viết, rồi khung hỏi thêm.
 * 3. Lộ trình học, khám sức khỏe, **bước tiếp theo** do khách chọn.
 *
 * Cột phải: thẻ hồ sơ (để khách thấy kết luận dựng trên thông tin nào) và thẻ điểm
 * nguyện vọng. Điểm tách khỏi bảng điều kiện bắt buộc — một con số to cạnh dấu ✓
 * dễ bị đọc thành "khả năng đậu".
 *
 * Màn hẹp: một cột, cột phải xuống dưới — đúng thứ tự đọc của bản thiết kế.
 *
 * ## Chưa xác nhận hồ sơ thì chưa có bảng
 *
 * Hồ sơ do máy đọc từ CV mà khách chưa xem lại thì có thể sai — đọc nhầm năm sinh là
 * đổi hẳn kết luận tuổi. Hiện bảng ✓ trên hồ sơ ấy là đưa khách một kết luận dựng
 * trên dữ liệu chưa ai kiểm. Nên chưa xác nhận thì chỉ mời xác nhận, không hiện
 * kết luận, điểm, bảng hay lộ trình học. Trợ lý ở phòng hỏi thêm cũng được dặn
 * cùng điều đó (xem `api/consultation_room.hoi_them`).
 *
 * Hai chỗ cố ý làm khác lẽ thường vẫn giữ:
 *
 * - **Nói rõ đoạn phân tích do ai viết** — "trợ lý viết lại" hay "hệ thống ghép".
 * - **Học phí không bao giờ đứng một mình.** Luôn kèm tổng chi phí chương trình,
 *   vì 35 triệu là một chặng của 90 triệu — hiện trơ trọi là để khách chuẩn bị
 *   thiếu tiền.
 */

import Link from "next/link";
import { type ReactNode, useState } from "react";
import BangDoiChieu, { CHUA_CUNG_CAP, TheDiem, demKetQua } from "@/components/candidate/BangDoiChieu";
import type { CandidateProfile, OrderAdvice } from "@/lib/candidateApi";

const NHANH: Record<OrderAdvice["branch"], string> = {
  phu_hop: "bg-reu-50 text-reu-700",
  chua_phu_hop: "bg-brand-50 text-brand-700",
  thieu_thong_tin: "bg-amber-50 text-amber-800",
};

const PANEL = "rounded-[10px] border border-slate-200 bg-white p-5 md:p-7";
const NHAN_NHO = "text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500";

function tien(so: number | null): string {
  if (!so) return "—";
  return `${so.toLocaleString("vi-VN")}đ`;
}

/**
 * Hồ sơ chưa xác nhận: chỉ mời xác nhận. Dùng ở đây và ở phòng tư vấn theo đơn khi
 * máy chủ trả mã `ho_so_chua_xac_nhan` (cửa chặn ở API từ 08/10).
 */
export function XacNhanTruoc({
  orderCode,
  orderTitle,
  onAskStaff,
}: {
  orderCode: string;
  orderTitle?: string;
  onAskStaff?: () => void;
}) {
  return (
    <section className="space-y-5">
      <div className="rounded-[10px] border border-amber-200 bg-amber-50/60 p-5 md:p-7">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{orderCode}</p>
        {orderTitle && <h2 className="mt-1 text-lg font-semibold text-slate-900">{orderTitle}</h2>}
        <p className="mt-3 leading-7 text-slate-700">
          Hệ thống đã đọc hồ sơ của bạn nhưng bạn chưa xem lại. Bạn kiểm tra và xác
          nhận hồ sơ trước, rồi bảng đối chiếu với đơn này mới hiện — máy có thể đọc
          nhầm, và kết luận dựng trên thông tin sai thì không giúp gì cho bạn.
        </p>
        <Link
          href={`/tu-van?don=${orderCode}`}
          className="mt-4 inline-flex min-h-[46px] items-center rounded-md bg-brand-600 px-6 font-semibold text-white hover:bg-brand-700"
        >
          Kiểm tra và xác nhận hồ sơ
        </Link>
      </div>
      {onAskStaff && (
        <button
          type="button"
          onClick={onAskStaff}
          className="inline-flex min-h-[46px] items-center rounded-md border border-slate-300 bg-white px-6 font-semibold text-slate-800 hover:bg-reu-50"
        >
          Nói chuyện với nhân viên
        </button>
      )}
    </section>
  );
}

function giaTri(o: CandidateProfile["fields"], key: string): unknown {
  return (o?.[key] ?? null)?.value ?? null;
}

/** Hai chữ đầu của hai tiếng cuối trong tên — "Nguyễn Thị Hoa" → "TH". */
export function chuDauTen(ten: unknown): string {
  // Chỉ lấy tiếng bắt đầu bằng chữ cái (có dạng hoa/thường khác nhau — gồm cả "Đ", "Ư"):
  // tên kèm "(tạm)" hay "- KT" từng ra "(" — cùng lỗi đã sửa bên màn quản trị 12/10.
  const chu = String(ten ?? "")
    .trim()
    .split(/\s+/)
    .filter((t) => t.length > 0 && t[0].toLowerCase() !== t[0].toUpperCase());
  if (chu.length === 0) return "?";
  return chu.slice(-2).map((t) => t[0]!.toUpperCase()).join("");
}

/**
 * Thẻ hồ sơ cột phải: khách thấy kết luận bên trái dựng trên thông tin nào.
 *
 * Tiếng Nhật dùng nguyên nhãn máy chủ ghép (`trang_thai_tieng_nhat`) — nó nói luôn căn
 * cứ: tự khai, nhân viên đã đối chứng, hay hoàn thành chương trình tại trung tâm (chưa
 * xác minh chứng chỉ). Không tự dựng lại nhãn ở đây để khỏi nói khác máy chủ.
 */
export function TheHoSo({ profile, orderCode }: { profile: CandidateProfile; orderCode: string }) {
  const nhan = profile.labels ?? {};
  const tn = profile.trang_thai_tieng_nhat;
  const kn = giaTri(profile.fields, "experience_years");
  const nguyenVong = [nhan.desired_region_group, nhan.desired_employer_type].filter(Boolean).join(" · ");
  const dong: [string, ReactNode][] = [
    ["Chuyên ngành", (giaTri(profile.fields, "major") as string | null) || CHUA_CUNG_CAP],
    ["Bằng cấp", nhan.education_level || CHUA_CUNG_CAP],
    ["Kinh nghiệm", kn != null && kn !== "" ? `${kn} năm` : CHUA_CUNG_CAP],
    ["Nguyện vọng", nguyenVong || CHUA_CUNG_CAP],
  ];
  return (
    <section className="rounded-[10px] border border-slate-200 bg-white p-6 text-center" aria-label="Hồ sơ của bạn">
      <span
        aria-hidden
        className="inline-grid h-12 w-12 place-items-center rounded-full bg-[#e9e6db] text-[#776f57]"
        style={{ fontFamily: "var(--font-serif, Georgia), Georgia, serif" }}
      >
        {chuDauTen(giaTri(profile.fields, "full_name"))}
      </span>
      <h3 className="mt-3 text-xl font-semibold text-slate-900">Hồ sơ của bạn</h3>
      <p className="mt-1 text-[11px] text-slate-500">
        {nhan.status || (profile.confirmed_at ? "Bạn đã xác nhận" : "Chưa xác nhận")}
      </p>
      <dl className="mt-6 grid grid-cols-2 gap-x-2 gap-y-4 text-left text-xs">
        <div className="col-span-2">
          <dt className="text-slate-500">Tiếng Nhật</dt>
          <dd className="mt-0.5 text-slate-900">{tn?.nhan || nhan.japanese_level || CHUA_CUNG_CAP}</dd>
          {tn?.chuong_trinh && <dd className="mt-1 text-slate-600">{tn.chuong_trinh.nhan}</dd>}
          {tn?.dang_hoc && <dd className="mt-1 text-slate-600">{tn.dang_hoc.nhan}</dd>}
        </div>
        {dong.map(([ten, gt]) => (
          <div key={ten}>
            <dt className="text-slate-500">{ten}</dt>
            <dd className={`mt-0.5 ${gt === CHUA_CUNG_CAP ? "text-slate-400" : "text-slate-900"}`}>{gt}</dd>
          </div>
        ))}
      </dl>
      <Link
        href={`/tu-van?don=${orderCode}`}
        className="mt-6 flex min-h-[44px] w-full items-center justify-center rounded-md border border-[#bbc7bd] text-sm font-semibold text-slate-900 hover:bg-reu-50"
      >
        Kiểm tra &amp; sửa hồ sơ
      </Link>
    </section>
  );
}

export default function OrderAdvicePanel({
  advice,
  profile,
  chat,
  onRegister,
  onAskStaff,
  onAskLearning,
  registering,
}: {
  advice: OrderAdvice;
  /** Hồ sơ khách — có thì hiện thẻ hồ sơ ở cột phải. */
  profile?: CandidateProfile | null;
  /** Khung hỏi thêm, đặt trong thẻ "Tư vấn dựa trên hồ sơ". */
  chat?: ReactNode;
  onRegister?: () => void;
  onAskStaff?: () => void;
  onAskLearning?: () => void;
  registering?: boolean;
}) {
  const [moBanGoc, setMoBanGoc] = useState(false);

  if (!advice.profile_confirmed) {
    return (
      <XacNhanTruoc
        orderCode={advice.order_code}
        orderTitle={advice.order_title}
        onAskStaff={onAskStaff}
      />
    );
  }

  // Bản máy chủ cũ chưa gửi `rows` thì ghép lại từ ba nhóm — thiếu thứ tự engine,
  // nhưng vẫn đủ dòng và đủ trạng thái.
  const dong = advice.rows ?? [...advice.blockers, ...advice.unknowns, ...advice.strengths];
  const dem = demKetQua(dong);
  const lo = advice.learning;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0 space-y-6">
        {/* --- Đối chiếu điều kiện: câu trả lời chính, hiện sẵn, đứng yên --- */}
        <section className={PANEL} aria-labelledby="doi-chieu-tieu-de">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className={NHAN_NHO}>Đối chiếu điều kiện</p>
              <h2 id="doi-chieu-tieu-de" className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
                Bạn đáp ứng những gì?
              </h2>
            </div>
            <span className="rounded bg-[#eaf0e9] px-3 py-2 text-[10px] font-semibold tracking-wide text-[#3d6153]">
              {dem.dat} / {dong.length} tiêu chí
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-500">
            Yêu cầu của đơn {advice.order_code} và thông tin của bạn, đặt cạnh nhau.
          </p>
          <p className={`mt-4 inline-block rounded px-3 py-1.5 text-sm font-medium first-letter:uppercase ${NHANH[advice.branch]}`}>
            {advice.branch_label}
          </p>
          <div className="mt-4">
            <BangDoiChieu
              rows={dong}
              softRows={advice.soft_rows ?? []}
              eligible={advice.eligible}
              score={advice.score}
              scoreRanked={advice.score_ranked}
              questions={advice.questions}
              anDiem
            />
          </div>
        </section>

        {/* --- Tư vấn dựa trên hồ sơ --- */}
        <section className={`${PANEL} border-t-[3px] border-t-[#708776]`} aria-labelledby="tu-van-tieu-de">
          <div className="flex items-center gap-4">
            <span
              aria-hidden
              className="grid h-[42px] w-[42px] shrink-0 place-items-center rounded-full border border-[#c5d7c8] text-2xl text-[#52725d]"
            >
              ✳
            </span>
            <div>
              <p className={NHAN_NHO}>Tư vấn dựa trên hồ sơ</p>
              <h2 id="tu-van-tieu-de" className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                Cùng nhìn rõ lựa chọn của bạn.
              </h2>
            </div>
          </div>
          <p className="mt-4 text-[15px] leading-[1.85] text-slate-800">{advice.text}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span className="rounded-full bg-slate-50 px-2.5 py-1 ring-1 ring-slate-200">
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
            <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-600 ring-1 ring-slate-200">
              {advice.text_template}
            </p>
          )}
          {chat && <div className="mt-6 border-t border-slate-200 pt-6">{chat}</div>}
        </section>

        {/* --- Lộ trình học --- */}
        {lo && (
          <section className={PANEL}>
            <h3 className="text-lg font-semibold text-slate-900">Cần học gì để đủ điều kiện đơn này</h3>
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
                <li key={khoa.code} className="rounded-lg bg-slate-50 p-3">
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
                className="mt-4 inline-flex min-h-[44px] items-center rounded-md bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Tôi muốn được tư vấn về việc học
              </button>
            )}
          </section>
        )}

        {/* --- Vì sao không có lộ trình --- */}
        {!lo && advice.learning_note && (
          <section className="rounded-[10px] bg-[#f7f4e9] p-5 md:p-6">
            <h3 className="font-semibold text-slate-900">Về việc học thêm</h3>
            <p className="mt-2 text-sm leading-6 text-[#716754]">{advice.learning_note}</p>
          </section>
        )}

        {/* --- Điều kiện sức khỏe --- */}
        {(advice.branch !== "chua_phu_hop" || lo) && (
          <section className={PANEL}>
            <h3 className="font-semibold text-slate-900">Còn một bước khám sức khỏe</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              Không nhiễm bệnh truyền nhiễm:{" "}
              <strong>{advice.suc_khoe.benh_loai_tru.join(", ")}</strong>
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-500">{advice.suc_khoe.loi_nhac}</p>
          </section>
        )}

        {/* --- Bước tiếp theo: khách chọn --- */}
        <section
          className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-5"
          aria-labelledby="buoc-tiep-tieu-de"
        >
          <div>
            <p className={NHAN_NHO}>Bạn chọn bước tiếp theo</p>
            <h3 id="buoc-tiep-tieu-de" className="mt-2 text-lg font-semibold text-slate-900">
              {advice.can_register ? "Muốn đăng ký đơn này?" : "Muốn trao đổi kỹ hơn?"}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Không có gì được gửi đi cho tới khi bạn bấm.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            {advice.can_register && onRegister && (
              <button
                type="button"
                onClick={onRegister}
                disabled={registering}
                className="inline-flex min-h-[46px] items-center rounded-md bg-brand-600 px-6 font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {registering ? "Đang gửi…" : "Đăng ký đơn này"}
              </button>
            )}
            {onAskStaff && (
              <button
                type="button"
                onClick={onAskStaff}
                className="inline-flex min-h-[46px] items-center rounded-md border border-[#bbc7bd] bg-white px-6 font-semibold text-slate-900 hover:bg-reu-50"
              >
                Nói chuyện với nhân viên
              </button>
            )}
          </div>
        </section>
      </div>

      {/* Máy tính: cột phải dính theo khi cuộn — đọc bảng dài vẫn thấy hồ sơ và điểm. */}
      <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start" aria-label="Hồ sơ và điểm nguyện vọng">
        {profile && <TheHoSo profile={profile} orderCode={advice.order_code} />}
        <TheDiem
          eligible={advice.eligible}
          score={advice.score}
          scoreRanked={advice.score_ranked}
          softRows={advice.soft_rows ?? []}
        />
        <p className="flex gap-3 px-2 text-xs leading-5 text-slate-500">
          <span aria-hidden className="text-2xl leading-none">↳</span>
          Bạn có thể hỏi tiếp hoặc tham khảo. Chỉ gửi nhân viên khi bạn bấm gửi.
        </p>
      </aside>
    </div>
  );
}
