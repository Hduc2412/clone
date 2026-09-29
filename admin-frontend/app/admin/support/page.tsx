"use client";

/**
 * Hàng đợi yêu cầu hỗ trợ.
 *
 * Trước màn hình này, khách bấm "xin gặp nhân viên" trên website thì yêu cầu rơi
 * vào bảng `support_requests` và **không ai mở bảng đó ra**. API có đủ cả hai
 * chiều từ 28/09, nhưng không có cửa nào để nhân viên nhìn thấy — nên nhánh
 * "chưa phù hợp vẫn được nói chuyện với người" là một cánh cửa dẫn vào phòng
 * trống. Đây là chỗ vá.
 *
 * ## Vì sao tách khỏi `/admin/queue`
 *
 * Hàng đợi kia là hồ sơ đăng ký: khách **đã chọn được một đơn và đủ điều kiện**,
 * việc của nhân viên là chốt hồ sơ. Hàng đợi này phần lớn là khách **chưa phù
 * hợp** nhưng vẫn muốn nói chuyện — việc của nhân viên là tư vấn hướng đi. Hai
 * loại việc có nhịp khác nhau hẳn, trộn một danh sách thì việc gấp lẫn với việc
 * dài hạn và cái gấp luôn là cái bị lỡ.
 *
 * ## Hiện khối đối chiếu ngay cạnh yêu cầu
 *
 * `advice_block` là đúng khối chữ khách đang nhìn thấy lúc bấm gửi. Đọc nó trước
 * khi bấm số là biết ngay khách vướng ở đâu — thay vì bắt một người vừa bị từ
 * chối phải kể lại từ đầu.
 */

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { loadCurrentUser } from "@/lib/auth";
import { SupportRequest, managementApi } from "@/lib/managementApi";

type Tab = "cho" | "cua-toi";

const NHAN_LOAI: Record<SupportRequest["kind"], string> = {
  gap_mat: "Xin gặp mặt",
  hoc_tap: "Tư vấn học",
  nhan_tin: "Nhắn tin",
};

const MAU_LOAI: Record<SupportRequest["kind"], string> = {
  gap_mat: "bg-amber-50 text-amber-800 ring-amber-200",
  hoc_tap: "bg-sky-50 text-sky-800 ring-sky-200",
  nhan_tin: "bg-slate-50 text-slate-700 ring-slate-200",
};

const NHAN_TRANG_THAI: Record<SupportRequest["status"], string> = {
  cho_xu_ly: "Chờ xử lý",
  dang_xu_ly: "Đang xử lý",
  da_xong: "Đã xong",
  da_huy: "Đã hủy",
};

function choBaoLau(createdAt: string): string {
  const phut = Math.floor((Date.now() - new Date(createdAt).getTime()) / 60000);
  if (phut < 1) return "vừa xong";
  if (phut < 60) return `${phut} phút trước`;
  const gio = Math.floor(phut / 60);
  if (gio < 24) return `${gio} giờ trước`;
  return `${Math.floor(gio / 24)} ngày trước`;
}

export default function SupportQueuePage() {
  const [tab, setTab] = useState<Tab>("cho");
  const [loai, setLoai] = useState<string>("");
  const [items, setItems] = useState<SupportRequest[]>([]);
  const [moCode, setMoCode] = useState<string | null>(null);
  const [traLoi, setTraLoi] = useState("");
  const [toi, setToi] = useState("");
  const [dangTai, setDangTai] = useState(true);
  const [ban, setBan] = useState<string | null>(null);
  const [loi, setLoi] = useState("");
  const [nhan, setNhan] = useState("");

  const tai = useCallback(() => {
    setDangTai(true);
    setLoi("");
    const doi =
      tab === "cho"
        ? managementApi.supportQueue({ status: "cho_xu_ly", kind: loai || undefined })
        : managementApi.mySupportRequests();
    doi
      .then((payload) => setItems(payload.items))
      .catch((ly_do) => setLoi(ly_do.message))
      .finally(() => setDangTai(false));
  }, [tab, loai]);

  useEffect(tai, [tai]);

  useEffect(() => {
    loadCurrentUser()
      .then((user) => setToi(user.email))
      .catch(() => undefined);
  }, []);

  const nhanXuLy = async (code: string) => {
    setBan(code);
    setLoi("");
    setNhan("");
    try {
      await managementApi.claimSupportRequest(code);
      setNhan(`Đã nhận ${code}. Yêu cầu nay nằm ở tab "Tôi đang xử lý".`);
      tai();
    } catch (ly_do) {
      // 409 nghĩa là người khác vừa nhận trước — thông báo của máy chủ đã nói rõ
      // ai, nên hiện nguyên văn thay vì viết lại một câu chung chung.
      setLoi((ly_do as Error).message);
    } finally {
      setBan(null);
    }
  };

  const guiTraLoi = async (code: string) => {
    if (traLoi.trim().length < 5) {
      setLoi("Nội dung trả lời quá ngắn. Ghi rõ đã trao đổi gì với khách.");
      return;
    }
    setBan(code);
    setLoi("");
    try {
      await managementApi.replySupportRequest(code, traLoi.trim());
      setNhan(`Đã đóng ${code}.`);
      setTraLoi("");
      setMoCode(null);
      tai();
    } catch (ly_do) {
      setLoi((ly_do as Error).message);
    } finally {
      setBan(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Tư vấn"
        title="Hàng đợi hỗ trợ"
        description="Yêu cầu khách gửi từ website: xin gặp mặt, hỏi về việc học, hoặc nhắn tin cho nhân viên. Tách khỏi hàng đợi hồ sơ đăng ký vì đây phần lớn là khách chưa đủ điều kiện nhưng vẫn muốn nói chuyện."
      />

      {loi && <ErrorBanner message={loi} />}
      {nhan && (
        <p className="rounded-lg bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800 ring-1 ring-emerald-200">
          {nhan}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-lg bg-slate-100 p-1">
          {(
            [
              ["cho", "Chờ xử lý"],
              ["cua-toi", "Tôi đang xử lý"],
            ] as const
          ).map(([gia_tri, chu]) => (
            <button
              key={gia_tri}
              type="button"
              onClick={() => setTab(gia_tri)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                tab === gia_tri
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {chu}
            </button>
          ))}
        </div>

        {tab === "cho" && (
          <select
            value={loai}
            onChange={(e) => setLoai(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
          >
            <option value="">Mọi loại yêu cầu</option>
            <option value="gap_mat">Xin gặp mặt</option>
            <option value="hoc_tap">Tư vấn học</option>
            <option value="nhan_tin">Nhắn tin</option>
          </select>
        )}

        <button
          type="button"
          onClick={tai}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Tải lại
        </button>
      </div>

      {dangTai && <p className="text-sm text-slate-500">Đang tải…</p>}

      {!dangTai && items.length === 0 && (
        <EmptyState
          title={tab === "cho" ? "Không có yêu cầu nào đang chờ" : "Bạn chưa nhận yêu cầu nào"}
          description={
            tab === "cho"
              ? "Khách gửi yêu cầu từ trang tư vấn sẽ hiện ở đây."
              : 'Sang tab "Chờ xử lý" để nhận một yêu cầu.'
          }
        />
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const mo = moCode === item.code;
          const cuaToi = item.assigned_to === toi;
          return (
            <article
              key={item.code}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${
                        MAU_LOAI[item.kind]
                      }`}
                    >
                      {NHAN_LOAI[item.kind]}
                    </span>
                    <span className="font-mono text-xs text-slate-500">{item.code}</span>
                    <span className="text-xs text-slate-500">
                      {choBaoLau(item.created_at)}
                    </span>
                    {item.status !== "cho_xu_ly" && (
                      <span className="text-xs text-slate-500">
                        · {NHAN_TRANG_THAI[item.status]}
                      </span>
                    )}
                  </div>
                  <h3 className="mt-1.5 text-base font-bold text-slate-900">
                    {item.full_name}
                  </h3>
                  <p className="text-sm text-slate-600">
                    <a
                      href={`tel:${item.phone}`}
                      className="font-medium text-brand-600 hover:underline"
                    >
                      {item.phone}
                    </a>
                    {item.job_order_code && (
                      <span className="ml-2 text-slate-500">
                        · đang xem đơn{" "}
                        <span className="font-mono">{item.job_order_code}</span>
                      </span>
                    )}
                  </p>
                </div>

                <div className="flex shrink-0 gap-2">
                  {!item.assigned_to && (
                    <button
                      type="button"
                      disabled={ban === item.code}
                      onClick={() => nhanXuLy(item.code)}
                      className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                    >
                      {ban === item.code ? "Đang nhận…" : "Nhận xử lý"}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setMoCode(mo ? null : item.code);
                      setTraLoi("");
                    }}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {mo ? "Thu gọn" : "Xem chi tiết"}
                  </button>
                </div>
              </div>

              <p className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-700">
                {item.message}
              </p>

              {item.assigned_to && (
                <p className="mt-2 text-xs text-slate-500">
                  Người phụ trách: {item.assigned_to}
                  {cuaToi && " (bạn)"}
                </p>
              )}

              {mo && (
                <div className="mt-4 space-y-4 border-t border-slate-200 pt-4">
                  {item.advice_block ? (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Kết quả đối chiếu khách đang nhìn thấy lúc gửi
                      </h4>
                      <pre className="mt-1.5 overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-900 px-3 py-2.5 font-mono text-xs leading-5 text-slate-100">
                        {item.advice_block}
                      </pre>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500">
                      Yêu cầu này không kèm kết quả đối chiếu — khách gửi từ ngoài
                      luồng tư vấn theo đơn.
                    </p>
                  )}

                  {item.reply ? (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Đã trả lời
                      </h4>
                      <p className="mt-1.5 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                        {item.reply}
                      </p>
                    </div>
                  ) : (
                    <div>
                      <label
                        htmlFor={`tra-loi-${item.code}`}
                        className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      >
                        Ghi lại đã trao đổi gì với khách
                      </label>
                      <textarea
                        id={`tra-loi-${item.code}`}
                        rows={3}
                        value={mo ? traLoi : ""}
                        onChange={(e) => setTraLoi(e.target.value)}
                        placeholder="Đã gọi lúc 10h, khách muốn học tiếng từ tháng sau…"
                        className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      />
                      <p className="mt-1 text-xs text-slate-500">
                        Ghi xong là yêu cầu đóng lại. Nội dung này để người sau đọc
                        được đã trao đổi tới đâu, nên viết cho người khác hiểu.
                      </p>
                      <button
                        type="button"
                        disabled={ban === item.code}
                        onClick={() => guiTraLoi(item.code)}
                        className="mt-2 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
                      >
                        {ban === item.code ? "Đang lưu…" : "Lưu và đóng yêu cầu"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
