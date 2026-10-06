"use client";

/**
 * Khối liên hệ biết ngữ cảnh — cho trang `/lien-he`.
 *
 * ## Vì sao trang liên hệ cần biết phiên
 *
 * Trước khối này, `/lien-he` là một trang tĩnh: ba địa chỉ văn phòng và một số
 * điện thoại. Người vừa đi hết luồng tư vấn, vừa đọc một kết quả nói họ vướng ở
 * tiếng Nhật, bấm sang đây và phải **kể lại toàn bộ từ đầu** — cho một hệ thống
 * đã biết tất cả những điều đó.
 *
 * Nay nếu phiên đã có hồ sơ thì trang hiện tóm tắt tình trạng, và yêu cầu gửi đi
 * mang theo bản bàn giao do máy chủ dựng. Khách chỉ cần viết thêm điều họ muốn
 * nói riêng.
 *
 * ## Cho khách xem trước bản bàn giao, có chủ ý
 *
 * Họ sắp gửi một bản mô tả về chính mình cho một người sẽ gọi điện cho họ. Họ có
 * quyền đọc nó trước. Và nếu có dòng nào sai thì đây là lúc rẻ nhất để sửa —
 * rẻ hơn nhiều so với lúc nhân viên đã nói câu đó ra miệng.
 *
 * ## Không có hồ sơ thì không hỏi gì thêm
 *
 * Người vào thẳng `/lien-he` từ Google chỉ muốn một số điện thoại. Hiện cho họ
 * một khối "tình trạng hồ sơ của bạn" trống rỗng là thêm một thứ phải đọc rồi bỏ
 * qua. Khi chưa có hồ sơ, khối này chỉ còn biểu mẫu nhắn tin.
 */

import { useEffect, useState } from "react";
import {
  type AgentState,
  fetchAgentState,
  fetchHandoffSummary,
} from "@/lib/candidateApi";
import { ensureSessionId } from "@/lib/journeySession";
import SupportRequestForm from "./SupportRequestForm";

export default function ContactStatus() {
  const [sessionId, setSessionId] = useState("");
  const [trangThai, setTrangThai] = useState<AgentState | null>(null);
  const [tomTat, setTomTat] = useState("");
  const [moTomTat, setMoTomTat] = useState(false);
  const [dangTai, setDangTai] = useState(true);

  useEffect(() => {
    let huy = false;
    (async () => {
      try {
        const id = await ensureSessionId();
        if (huy || !id) return;
        setSessionId(id);
        const ra = await fetchAgentState(id);
        if (!huy) setTrangThai(ra);
      } catch {
        /* Chưa có phiên hoặc máy chủ chưa với tới được. Trang vẫn phải dùng
           được: biểu mẫu nhắn tin không cần trạng thái nào. */
      } finally {
        if (!huy) setDangTai(false);
      }
    })();
    return () => {
      huy = true;
    };
  }, []);

  const xemTomTat = async () => {
    setMoTomTat(true);
    if (tomTat || !sessionId) return;
    try {
      const ra = await fetchHandoffSummary(sessionId);
      setTomTat(ra.summary);
    } catch {
      setTomTat("Chưa dựng được bản tóm tắt. Nhân viên sẽ hỏi bạn khi gọi.");
    }
  };

  // Có hồ sơ nghĩa là đã khai gì đó. `known_fields` rỗng thì coi như chưa.
  const coHoSo = Boolean(trangThai && trangThai.known_fields.length > 0);

  if (dangTai) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">
        Đang kiểm tra hồ sơ của bạn…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {coHoSo && trangThai && (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-sky-800">
            Hồ sơ của bạn trên hệ thống
          </p>
          <p className="mt-2 text-sm leading-6 text-sky-900">
            Tình trạng: <strong>{trangThai.stage_label}</strong>
            {trangThai.eligible_count !== null && (
              <>
                {" · "}
                {trangThai.eligible_count > 0
                  ? `${trangThai.eligible_count} đơn bạn đủ điều kiện nộp`
                  : "chưa có đơn nào bạn đủ điều kiện"}
              </>
            )}
            {trangThai.interested_order_codes.length > 0 && (
              <>{` · đang xem đơn ${trangThai.interested_order_codes[0]}`}</>
            )}
          </p>
          <p className="mt-2 text-sm leading-6 text-sky-900">
            Bạn <strong>không phải kể lại từ đầu</strong>. Yêu cầu gửi đi sẽ mang
            theo hồ sơ và kết quả đối chiếu; bạn chỉ cần viết thêm điều muốn nói
            riêng.
          </p>

          {!moTomTat ? (
            <button
              type="button"
              onClick={() => void xemTomTat()}
              className="mt-3 text-sm font-semibold text-sky-800 underline"
            >
              Xem trước thứ nhân viên sẽ đọc
            </button>
          ) : (
            <div className="mt-3">
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-xl bg-white p-4 text-xs leading-5 text-slate-700">
                {tomTat || "Đang dựng…"}
              </pre>
              <button
                type="button"
                onClick={() => setMoTomTat(false)}
                className="mt-2 text-sm font-semibold text-sky-800 underline"
              >
                Thu gọn
              </button>
            </div>
          )}
        </div>
      )}

      {sessionId ? (
        <SupportRequestForm
          sessionId={sessionId}
          orderCode={trangThai?.interested_order_codes[0]}
          loaiMacDinh="nhan_tin"
        />
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
          Chưa mở được phiên nên biểu mẫu tạm chưa dùng được. Bạn gọi hotline
          hoặc thử tải lại trang nhé.
        </div>
      )}
    </div>
  );
}
