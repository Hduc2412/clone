"use client";

/**
 * Gửi một yêu cầu cần người xử lý.
 *
 * Ba loại, và chúng cần người khác nhau: nhắn tin hỏi thêm, tư vấn chuyện học,
 * xin gặp mặt. Tách ra để nhân viên phụ trách đào tạo không phải lọc thủ công
 * qua hai mươi câu hỏi về chi phí.
 *
 * ## Câu quan trọng nhất trên biểu mẫu này
 *
 * *"Nhân viên trả lời trong giờ làm việc"* — đặt ngay dưới nút gửi, không giấu
 * trong dòng chữ nhỏ. Phần lớn khách tìm hiểu vào buổi tối; hứa trả lời ngay rồi
 * để họ ngồi nhìn màn hình im lặng tới sáng là cách nhanh nhất để mất một người
 * thật sự đang quan tâm.
 *
 * ## Không hỏi chuyện bệnh tật
 *
 * Khách lo mình không đủ điều kiện sức khỏe thì cứ viết vào ô tin nhắn, nhưng
 * biểu mẫu **không có ô nào hỏi bệnh gì** và hệ thống không lưu chẩn đoán của ai.
 * Kết luận sức khỏe là của buổi khám, không phải của một ô chọn trên web.
 */

import { FormEvent, useState } from "react";
import { COMPANY } from "@/content/site";
import {
  type SupportKind,
  sendSupportRequest,
} from "@/lib/candidateApi";

const LOAI: { ma: SupportKind; nhan: string; goi_y: string }[] = [
  {
    ma: "nhan_tin",
    nhan: "Hỏi thêm",
    goi_y: "Điều bạn còn băn khoăn về đơn này, chi phí, hay quy trình…",
  },
  {
    ma: "hoc_tap",
    nhan: "Tư vấn việc học",
    goi_y: "Bạn muốn hỏi gì về khóa học tiếng Nhật, lịch khai giảng, học phí…",
  },
  {
    ma: "gap_mat",
    nhan: "Xin gặp mặt",
    goi_y: "Bạn ở đâu và rảnh khoảng thời gian nào, để nhân viên sắp lịch…",
  },
];

const O_NHAP =
  "mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-[#cb1d1e]";

export default function SupportRequestForm({
  sessionId,
  orderCode,
  loaiMacDinh = "nhan_tin",
  onDone,
}: {
  sessionId: string;
  orderCode?: string;
  loaiMacDinh?: SupportKind;
  onDone?: (code: string) => void;
}) {
  // Không nhận `adviceBlock` nữa. Máy chủ tự dựng lại khối kết quả đối chiếu từ
  // nhật ký giới thiệu — trình duyệt không còn là nguồn của thứ nhân viên đọc.
  // Chỉ cần `orderCode` là máy chủ tra ra đúng khối khách đã nhìn thấy.
  const [kind, setKind] = useState<SupportKind>(loaiMacDinh);
  const [ngay, setNgay] = useState("");
  const [gio, setGio] = useState("");
  const [hinhThuc, setHinhThuc] = useState<"truc_tiep" | "truc_tuyen">("truc_tuyen");
  const [dangGui, setDangGui] = useState(false);
  const [loi, setLoi] = useState("");
  const [maDaGui, setMaDaGui] = useState("");
  const [maLichHen, setMaLichHen] = useState("");

  const chon = LOAI.find((l) => l.ma === kind) ?? LOAI[0];

  const gui = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setDangGui(true);
    setLoi("");
    try {
      const ket_qua = await sendSupportRequest(sessionId, {
        kind,
        message: String(form.get("message") || ""),
        full_name: String(form.get("full_name") || ""),
        phone: String(form.get("phone") || ""),
        job_order_code: orderCode,
        // Chỉ gửi khung giờ với loại "xin gặp mặt", và chỉ khi khách điền đủ
        // cả ngày lẫn giờ. Gửi một nửa thì máy chủ từ chối cả yêu cầu — xem
        // `SupportRequestBody._ngay_va_gio_di_cung_nhau`.
        ...(kind === "gap_mat" && ngay && gio
          ? {
              appointment_date: ngay,
              appointment_time: gio,
              meeting_kind: hinhThuc,
            }
          : {}),
      });
      setMaDaGui(ket_qua.code);
      setMaLichHen(ket_qua.appointment_code ?? "");
      onDone?.(ket_qua.code);
    } catch (reason) {
      setLoi(reason instanceof Error ? reason.message : "Chưa gửi được, bạn thử lại nhé.");
    } finally {
      setDangGui(false);
    }
  };

  if (maDaGui) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
        <h3 className="font-semibold text-slate-900">Đã gửi tới nhân viên tư vấn</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Mã yêu cầu của bạn là <strong>{maDaGui}</strong>. Xin vui lòng liên hệ với
          nhân viên trong khoảng thời gian từ <strong>{COMPANY.contactHours}</strong>,
          thứ Hai đến thứ Bảy.
        </p>
        {/* Nói rõ lịch đã được ghi nhận hay chưa.
            Khách chọn giờ rồi gửi mà màn hình không nhắc lại thì họ không biết
            hệ thống có nhận hay không — và nếu trùng lịch (máy chủ bỏ qua, có
            chủ ý) thì họ càng cần biết. */}
        {maLichHen ? (
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Mình đã ghi lịch hẹn <strong>{maLichHen}</strong>. Nhân viên sẽ xác
            nhận lại với bạn trước buổi gặp.
          </p>
        ) : (
          kind === "gap_mat" &&
          Boolean(ngay) && (
            <p className="mt-2 text-sm leading-6 text-amber-800">
              Khung giờ bạn chọn chưa thành lịch hẹn — có thể bạn đã có lịch vào
              đúng giờ đó. Nhân viên sẽ xác nhận lại khi gọi.
            </p>
          )
        )}
      </div>
    );
  }

  return (
    <form onSubmit={gui} className="rounded-2xl border border-slate-200 bg-white p-5">
      <h3 className="font-semibold text-slate-900">Nói chuyện với nhân viên</h3>

      <div className="mt-4 flex flex-wrap gap-2">
        {LOAI.map((l) => (
          <button
            key={l.ma}
            type="button"
            onClick={() => setKind(l.ma)}
            aria-pressed={kind === l.ma}
            className={`rounded-full px-4 py-2 text-sm font-medium ring-1 transition ${
              kind === l.ma
                ? "bg-[#cb1d1e] text-white ring-[#cb1d1e]"
                : "bg-white text-slate-700 ring-slate-300 hover:ring-[#cb1d1e]"
            }`}
          >
            {l.nhan}
          </button>
        ))}
      </div>

      {/* Không `required`.
          Khách vừa đọc một khối kết quả nói rõ họ vướng ở đâu rồi bấm "xin gặp
          nhân viên". Bắt gõ lại bằng lời của mình là bắt diễn đạt lại thứ hệ
          thống đã biết — và với người vừa bị báo chưa đủ điều kiện thì đó là một
          bậc thềm đủ cao để họ bỏ đi.

          Máy chủ đã cho để trống từ 30/09 và tự điền một câu theo loại yêu cầu,
          nhưng thuộc tính `required` ở đây vẫn chặn — nên trên thực tế khách vẫn
          bị bắt viết. Bản rà soát 30/09 bắt đúng chỗ lệch này. */}
      <label className="mt-4 block text-sm font-medium text-slate-700">
        Nội dung
        <span className="ml-1 font-normal text-slate-400">(không bắt buộc)</span>
        <textarea
          name="message"
          rows={4}
          maxLength={2000}
          placeholder={chon.goi_y}
          className={`${O_NHAP} resize-y`}
        />
        <span className="mt-1 block text-xs font-normal text-slate-500">
          Để trống cũng được — nhân viên đã thấy kết quả đối chiếu của bạn.
        </span>
      </label>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-700">
          Họ và tên
          <input required name="full_name" maxLength={100} className={O_NHAP} />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Số điện thoại
          <input
            required
            name="phone"
            inputMode="tel"
            placeholder="09xx xxx xxx"
            className={O_NHAP}
          />
        </label>
      </div>

      {/* Khung giờ — chỉ hiện với "Xin gặp mặt".
          Trước đây khách bấm xin gặp rồi nhân viên phải gọi điện hỏi lại giờ nào
          tiện, trong khi khách đang ngồi trước màn hình. Vẫn để trống được: chưa
          biết lịch mình thì nhân viên hẹn lại. */}
      {kind === "gap_mat" && (
        <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-700">
            Bạn rảnh lúc nào?{" "}
            <span className="font-normal text-slate-500">
              Để trống cũng được — nhân viên sẽ hẹn lại.
            </span>
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="block text-sm text-slate-700">
              Ngày
              <input
                type="date"
                value={ngay}
                onChange={(e) => setNgay(e.target.value)}
                className={O_NHAP}
              />
            </label>
            <label className="block text-sm text-slate-700">
              Giờ
              <input
                type="time"
                value={gio}
                onChange={(e) => setGio(e.target.value)}
                className={O_NHAP}
              />
              <span className="mt-1 block text-xs text-slate-500">
                Nhận lịch 08:00–11:30 hoặc 13:30–17:00, thứ Hai đến thứ Bảy.
              </span>
            </label>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(
              [
                ["truc_tuyen", "Gặp trực tuyến"],
                ["truc_tiep", "Gặp tại văn phòng"],
              ] as const
            ).map(([ma, nhan]) => (
              <button
                key={ma}
                type="button"
                onClick={() => setHinhThuc(ma)}
                aria-pressed={hinhThuc === ma}
                className={`rounded-full px-4 py-2 text-sm font-medium ring-1 transition ${
                  hinhThuc === ma
                    ? "bg-[#cb1d1e] text-white ring-[#cb1d1e]"
                    : "bg-white text-slate-700 ring-slate-300"
                }`}
              >
                {nhan}
              </button>
            ))}
          </div>
          {/* Nói trước điều máy chủ sẽ từ chối, thay vì để khách bấm gửi rồi
              nhận một lời từ chối. */}
          {Boolean(ngay) !== Boolean(gio) && (
            <p className="mt-3 text-sm text-amber-800">
              Bạn chọn cả ngày và giờ giúp mình nhé, hoặc để trống cả hai.
            </p>
          )}
        </div>
      )}

      {loi && (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{loi}</p>
      )}

      <button
        disabled={dangGui}
        className="mt-5 w-full rounded-xl bg-[#cb1d1e] px-4 py-3 font-semibold text-white disabled:opacity-60 sm:w-auto sm:px-8"
      >
        {dangGui ? "Đang gửi…" : "Gửi cho nhân viên"}
      </button>

      {/* Đặt ngay dưới nút, không giấu trong dòng chữ nhỏ — xem docstring đầu file. */}
      <p className="mt-3 text-sm text-slate-600">
        Xin vui lòng liên hệ với nhân viên trong khoảng thời gian từ{" "}
        <strong>{COMPANY.contactHours}</strong>, thứ Hai đến thứ Bảy. Cần gấp thì
        bạn gọi hotline{" "}
        <a href={COMPANY.hotlineHref} className="font-semibold text-[#cb1d1e]">
          {COMPANY.hotline}
        </a>{" "}
        nhé.
      </p>
    </form>
  );
}
