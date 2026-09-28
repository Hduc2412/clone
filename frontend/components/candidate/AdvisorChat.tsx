"use client";

/**
 * Hộp hỏi đáp trong phòng tư vấn — vòng "Hỏi thêm" của sơ đồ nghiệp vụ.
 *
 * Khác khung chat ở góc màn hình: khung kia trả lời câu hỏi chung về chương
 * trình bằng kho tài liệu công ty, và nó không biết người đang hỏi là ai. Hộp
 * này thì ngược lại — không có kho tài liệu nào, nhưng biết hồ sơ của người
 * đang hỏi, biết đơn họ đang xem, và biết kết quả đối chiếu giữa hai thứ đó.
 *
 * ## Nói rõ bot biết gì và không biết gì, ngay từ đầu
 *
 * Đặt một dòng ngắn trên ô nhập thay vì để người ta tự dò ra sau ba câu hỏi
 * trượt. Người dùng biết ranh giới thì hỏi đúng chỗ; không biết thì họ thử vài
 * câu, nhận toàn "chưa có thông tin", rồi kết luận là hệ thống hỏng.
 *
 * ## Câu "chưa có thông tin" được đánh dấu khác
 *
 * Không tô như một câu trả lời bình thường. Người đọc phải nhận ra ngay đây là
 * lúc bot **từ chối đoán**, không phải lúc nó trả lời qua loa — và biết đường đi
 * tiếp nằm ngay trong câu đó.
 */

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  type AdvisorTurn,
  askAdvisor,
  fetchAdvisorTurns,
} from "@/lib/candidateApi";

const GOI_Y = [
  "Vì sao em chưa đạt đơn này?",
  "Em cần học bao lâu thì đủ điều kiện?",
  "Tổng chi phí em phải chuẩn bị là bao nhiêu?",
];

export default function AdvisorChat({
  sessionId,
  orderCode,
}: {
  sessionId: string;
  orderCode: string;
}) {
  const [luot, setLuot] = useState<AdvisorTurn[]>([]);
  const [dangHoi, setDangHoi] = useState(false);
  const [loi, setLoi] = useState("");
  const [noiDung, setNoiDung] = useState("");
  const cuoiRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let huy = false;
    fetchAdvisorTurns(sessionId, orderCode)
      .then((ra) => {
        if (!huy) setLuot(ra.items);
      })
      .catch(() => {
        /* Chưa có lượt nào, hoặc chưa đọc được. Không phải lỗi đáng báo. */
      });
    return () => {
      huy = true;
    };
  }, [sessionId, orderCode]);

  useEffect(() => {
    cuoiRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [luot.length]);

  const hoi = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cau = noiDung.trim();
    if (!cau || dangHoi) return;

    setDangHoi(true);
    setLoi("");
    // Hiện câu hỏi ngay, không đợi máy chủ. Người dùng thấy câu mình vừa gõ nằm
    // đó thì biết hệ thống đã nhận, thay vì nhìn ô trống và tự hỏi đã gửi chưa.
    setNoiDung("");
    try {
      const ra = await askAdvisor(sessionId, orderCode, cau);
      setLuot((truoc) => [...truoc, ra]);
    } catch (reason) {
      setNoiDung(cau);
      setLoi(reason instanceof Error ? reason.message : "Chưa gửi được câu hỏi.");
    } finally {
      setDangHoi(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <h3 className="font-semibold text-slate-900">Hỏi thêm về đơn này</h3>
      <p className="mt-1 text-sm leading-6 text-slate-600">
        Trợ lý biết <strong>hồ sơ của bạn</strong> và <strong>đơn {orderCode}</strong>,
        nên trả lời được những câu như “em còn thiếu gì”, “học bao lâu thì đủ”.
        Câu hỏi chung về chương trình thì hỏi khung chat ở góc màn hình.
      </p>

      {luot.length > 0 && (
        <div className="mt-4 space-y-4">
          {luot.map((l, i) => (
            <div key={`${l.question}-${i}`} className="space-y-2">
              <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-slate-100 px-4 py-2.5 text-sm leading-6 text-slate-800">
                {l.question}
              </p>
              {/* Ba trạng thái, không phải hai. "Trợ lý không đoán" là bot đã
                  cân nhắc rồi chịu dừng — đáng để khoe. "Trợ lý đang bận" là
                  không gọi được mô hình, một sự cố kỹ thuật. Dán nhãn thận
                  trọng lên một lần dịch vụ chết là nhận công không phải của
                  mình, và tệ hơn: ứng viên tưởng công ty không có thông tin
                  nên thôi không hỏi lại nữa. */}
              <div
                className={`max-w-[92%] rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm leading-6 ${
                  l.source === "khong_biet"
                    ? "bg-amber-50 text-amber-900 ring-1 ring-amber-200"
                    : l.source === "khong_goi_duoc"
                      ? "bg-slate-50 text-slate-700 ring-1 ring-slate-200"
                      : "bg-[#fdf2f2] text-slate-800"
                }`}
              >
                {l.source === "khong_biet" && (
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
                    Trợ lý không đoán
                  </p>
                )}
                {l.source === "khong_goi_duoc" && (
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Trợ lý đang bận
                  </p>
                )}
                {l.answer}
              </div>
            </div>
          ))}
          <div ref={cuoiRef} />
        </div>
      )}

      {luot.length === 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {GOI_Y.map((cau) => (
            <button
              key={cau}
              type="button"
              onClick={() => setNoiDung(cau)}
              className="rounded-full border border-slate-300 px-3.5 py-1.5 text-sm text-slate-700 hover:border-[#cb1d1e] hover:text-[#cb1d1e]"
            >
              {cau}
            </button>
          ))}
        </div>
      )}

      {loi && (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{loi}</p>
      )}

      <form onSubmit={hoi} className="mt-4 flex gap-2">
        <input
          value={noiDung}
          onChange={(e) => setNoiDung(e.target.value)}
          maxLength={500}
          placeholder="Bạn muốn hỏi gì về đơn này?"
          aria-label="Câu hỏi về đơn này"
          className="flex-1 rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-[#cb1d1e]"
        />
        <button
          disabled={dangHoi || !noiDung.trim()}
          className="rounded-xl bg-[#cb1d1e] px-5 py-3 font-semibold text-white disabled:opacity-50"
        >
          {dangHoi ? "Đang hỏi…" : "Hỏi"}
        </button>
      </form>
    </section>
  );
}
