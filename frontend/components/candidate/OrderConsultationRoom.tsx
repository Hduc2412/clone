"use client";

/**
 * Phòng tư vấn cho một đơn cụ thể.
 *
 * Khách vừa đọc xong một đơn trên website và có đúng một câu hỏi trong đầu:
 * *"tôi có hợp đơn này không, và nếu chưa thì thiếu gì"*. Trang này trả lời câu
 * đó, thay vì bắt họ đi qua trang đối chiếu cả danh mục rồi tự tìm lại đơn mình
 * vừa xem trong danh sách xếp hạng.
 *
 * Ba trạng thái, không hơn:
 *
 * 1. **Chưa có hồ sơ** — mời gửi CV, hoặc sang biểu mẫu khai tay.
 * 2. **Đã có hồ sơ** — hiện kết quả đối chiếu với đúng đơn này.
 * 3. **Không mở được phiên** — nói thật là chưa kết nối được, kèm cách thoát.
 *
 * Không tự khai hồ sơ ở đây: biểu mẫu đầy đủ đã có ở `/tu-van` và nó xử lý cả
 * nguyện vọng, xác nhận từng dòng, khóa theo phiên bản. Dựng bản thứ hai ở đây
 * là hai chỗ phải sửa mỗi lần đổi một trường.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import CvUpload from "@/components/candidate/CvUpload";
import OrderAdvicePanel from "@/components/candidate/OrderAdvicePanel";
import AdvisorChat from "@/components/candidate/AdvisorChat";
import SupportRequestForm from "@/components/candidate/SupportRequestForm";
import { COMPANY } from "@/content/site";
import type { SupportKind } from "@/lib/candidateApi";
import {
  ApiError,
  type OrderAdvice,
  ensureSessionId,
  fetchOrderAdvice,
  fetchProfile,
  registerForOrder,
} from "@/lib/candidateApi";

type TrangThai = "dang-mo" | "chua-co-ho-so" | "co-ket-qua" | "khong-mo-duoc";

export default function OrderConsultationRoom({
  orderCode,
}: {
  orderCode: string;
}) {
  const [trangThai, setTrangThai] = useState<TrangThai>("dang-mo");
  const [sessionId, setSessionId] = useState("");
  const [advice, setAdvice] = useState<OrderAdvice | null>(null);
  const [loi, setLoi] = useState("");
  const [dangGui, setDangGui] = useState(false);
  const [daDangKy, setDaDangKy] = useState("");
  // Mở biểu mẫu hỗ trợ, và nhớ khách bấm từ nút nào để chọn sẵn đúng loại.
  const [loaiHoTro, setLoaiHoTro] = useState<SupportKind | null>(null);

  const doiChieu = useCallback(
    async (phien: string) => {
      try {
        setAdvice(await fetchOrderAdvice(phien, orderCode));
        setTrangThai("co-ket-qua");
      } catch (reason) {
        // 404 ở đây nghĩa là chưa có hồ sơ cho phiên — không phải lỗi, mà là
        // bước đầu của luồng. Phân biệt với lỗi thật, nếu không khách sẽ thấy
        // một thông báo đỏ ngay khi vừa mở trang.
        if (reason instanceof ApiError && reason.status === 404) {
          setTrangThai("chua-co-ho-so");
          return;
        }
        setLoi(reason instanceof Error ? reason.message : "Chưa đối chiếu được.");
        setTrangThai("chua-co-ho-so");
      }
    },
    [orderCode],
  );

  useEffect(() => {
    let huy = false;
    (async () => {
      const phien = await ensureSessionId();
      if (huy) return;
      if (!phien) {
        setTrangThai("khong-mo-duoc");
        return;
      }
      setSessionId(phien);
      // Có hồ sơ thì đối chiếu luôn. Không có thì mời gửi CV — không gọi đối
      // chiếu để khỏi tốn một lượt vô ích.
      try {
        const ho_so = await fetchProfile(phien);
        if (huy) return;
        if (ho_so) {
          await doiChieu(phien);
          return;
        }
      } catch {
        /* Không đọc được hồ sơ thì coi như chưa có, mời gửi CV. */
      }
      if (!huy) setTrangThai("chua-co-ho-so");
    })();
    return () => {
      huy = true;
    };
  }, [doiChieu]);

  const sauKhiDocCv = async () => {
    if (sessionId) await doiChieu(sessionId);
  };

  const dangKy = async () => {
    if (!sessionId || !advice) return;
    setDangGui(true);
    setLoi("");
    try {
      const ket_qua = await registerForOrder(sessionId, advice.order_code);
      setDaDangKy(ket_qua.application_code);
    } catch (reason) {
      setLoi(reason instanceof Error ? reason.message : "Chưa đăng ký được.");
    } finally {
      setDangGui(false);
    }
  };

  if (trangThai === "dang-mo") {
    return <p className="py-10 text-center text-sm text-slate-500">Đang mở phòng tư vấn…</p>;
  }

  if (trangThai === "khong-mo-duoc") {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
        <h2 className="font-semibold text-slate-900">Chưa mở được phiên tư vấn</h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Có thể mạng đang chập. Bạn tải lại trang giúp mình, hoặc gọi hotline để
          nhân viên tư vấn trực tiếp.
        </p>
      </div>
    );
  }

  if (daDangKy) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
        <h2 className="font-semibold text-slate-900">Đã gửi hồ sơ đăng ký</h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Mã hồ sơ của bạn là <strong>{daDangKy}</strong>. Xin vui lòng liên hệ với
          nhân viên trong khoảng thời gian từ <strong>{COMPANY.contactHours}</strong>,
          thứ Hai đến thứ Bảy.
        </p>
        <Link
          href="/ho-so-cua-toi"
          className="mt-4 inline-block rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-semibold text-white"
        >
          Theo dõi hồ sơ của tôi
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {loi && (
        <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700 ring-1 ring-red-200">
          {loi}
        </p>
      )}

      {trangThai === "chua-co-ho-so" && (
        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold text-slate-900">
              Gửi hồ sơ để biết bạn có hợp đơn này không
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Hệ thống đối chiếu hồ sơ của bạn với từng điều kiện của đơn{" "}
              <strong>{orderCode}</strong> rồi nói rõ đạt hay chưa đạt ở mục nào.
              Chưa đủ điều kiện thì chỉ ra còn thiếu gì và cần học bao lâu.
            </p>
            {sessionId && (
              <div className="mt-5">
                <CvUpload sessionId={sessionId} onProfileRead={sauKhiDocCv} />
              </div>
            )}
          </div>

          <p className="text-sm text-slate-600">
            Không sẵn tệp CV?{" "}
            <Link
              href={`/tu-van?don=${orderCode}`}
              className="font-semibold text-[#cb1d1e] hover:underline"
            >
              Khai nhanh vài mục bằng biểu mẫu
            </Link>{" "}
            — mất khoảng hai phút, mục nào chưa rõ thì cứ bỏ trống.
          </p>
        </div>
      )}

      {trangThai === "co-ket-qua" && advice && (
        <>
          <OrderAdvicePanel
            advice={advice}
            registering={dangGui}
            onRegister={dangKy}
            onAskStaff={() => setLoaiHoTro("nhan_tin")}
            onAskLearning={() => setLoaiHoTro("hoc_tap")}
          />

          {/* Vòng "Hỏi thêm" của sơ đồ. Đặt ngay dưới kết quả đối chiếu, vì phần
              lớn câu hỏi phát sinh từ chính thứ vừa đọc: vì sao chưa đạt, học
              bao lâu thì đủ, tổng tiền là bao nhiêu. */}
          {sessionId && (
            <AdvisorChat sessionId={sessionId} orderCode={advice.order_code} />
          )}

          {loaiHoTro && sessionId && (
            <SupportRequestForm
              sessionId={sessionId}
              orderCode={advice.order_code}
              // Gửi kèm đúng khối chữ khách vừa đọc. Nhân viên gọi lại đọc được
              // chính thứ khách đã đọc, thay vì tự dựng lại rồi đoán xem khách
              // đang hiểu thế nào.
              loaiMacDinh={loaiHoTro}
            />
          )}
          <p className="text-sm text-slate-600">
            Muốn xem những đơn khác phù hợp với hồ sơ này?{" "}
            <Link href="/tu-van" className="font-semibold text-[#cb1d1e] hover:underline">
              Xem toàn bộ đơn phù hợp
            </Link>
          </p>
        </>
      )}

      <p className="text-xs leading-5 text-slate-500">
        Mức độ phù hợp tính trên giấy tờ, không phải cam kết trúng tuyển. Nhân viên
        tư vấn sẽ xác nhận lại trước khi nộp hồ sơ.
      </p>
    </div>
  );
}
