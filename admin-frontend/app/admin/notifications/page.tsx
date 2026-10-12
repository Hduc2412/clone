"use client";

/**
 * Thông báo (12/10).
 *
 * Trước đó không màn hình nào đọc `/notifications`: nút "Thông báo" trỏ sang hàng đợi hồ
 * sơ, con số đếm cả hệ thống và chỉ tăng (161 trên database thật). Trang này đọc đúng
 * phạm vi người xem — máy chủ lọc và rút gọn tên khách ở việc chưa phải của người xem —
 * và cho đánh dấu đã đọc từng dòng hoặc tất cả.
 */
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { Notification, managementApi } from "@/lib/managementApi";
import { baoThongBaoDaDoi, moTa, noiXuLy, tieuDe } from "@/lib/thongBao";

function luc(iso: string): string {
  const t = new Date(iso);
  return Number.isNaN(t.getTime()) ? iso : t.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

export default function NotificationsPage() {
  const [ds, setDs] = useState<Notification[]>([]);
  const [chiChuaDoc, setChiChuaDoc] = useState(true);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");

  const nap = useCallback(() => {
    setDangTai(true);
    setLoi("");
    managementApi
      .notifications(chiChuaDoc)
      .then(setDs)
      .catch((r) => setLoi(r instanceof Error ? r.message : "Không tải được thông báo."))
      .finally(() => setDangTai(false));
  }, [chiChuaDoc]);

  useEffect(nap, [nap]);

  const docMot = async (tb: Notification) => {
    const ma = tb.reference_code ?? tb.appointment_code;
    if (!ma) return;
    try {
      await managementApi.markNotificationRead(ma);
      baoThongBaoDaDoi();
      nap();
    } catch (r) {
      setLoi(r instanceof Error ? r.message : "Không đánh dấu được.");
    }
  };

  const docHet = async () => {
    try {
      await managementApi.markAllNotificationsRead();
      baoThongBaoDaDoi();
      nap();
    } catch (r) {
      setLoi(r instanceof Error ? r.message : "Không đánh dấu được.");
    }
  };

  const chuaDoc = ds.filter((t) => !t.is_read).length;

  return (
    <>
      <PageHeader
        eyebrow="Việc đến với bạn"
        title="Thông báo"
        description="Hồ sơ đăng ký, yêu cầu hỗ trợ, lịch hẹn và việc về đơn tuyển dụng. Việc chưa phải của bạn chỉ hiện tên viết tắt của khách."
        action={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setChiChuaDoc((v) => !v)}
              className="rounded-md border border-[#bbc7bd] bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-reu-50"
            >
              {chiChuaDoc ? "Xem cả đã đọc" : "Chỉ chưa đọc"}
            </button>
            <button
              type="button"
              onClick={docHet}
              disabled={chuaDoc === 0}
              className="rounded-md bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40"
            >
              Đánh dấu tất cả đã đọc
            </button>
          </div>
        }
      />
      {loi && <ErrorBanner message={loi} />}

      {dangTai ? (
        <p className="text-sm text-slate-500">Đang tải thông báo…</p>
      ) : ds.length === 0 ? (
        <EmptyState
          title={chiChuaDoc ? "Không còn thông báo chưa đọc" : "Chưa có thông báo nào"}
          description="Thông báo mới sẽ hiện ở đây."
        />
      ) : (
        <ul className="divide-y divide-slate-200 rounded-[10px] border border-slate-200 bg-white">
          {ds.map((tb, i) => (
            <li
              key={`${tb.reference_code ?? tb.appointment_code}-${tb.created_at}-${i}`}
              className={`flex flex-wrap items-center justify-between gap-3 px-5 py-4 ${tb.is_read ? "" : "bg-kem"}`}
            >
              <div className="min-w-0">
                <p className={`text-sm ${tb.is_read ? "text-slate-600" : "font-semibold text-slate-900"}`}>
                  {!tb.is_read && <span className="sr-only">Chưa đọc: </span>}
                  {tieuDe(tb)}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {moTa(tb)}
                  {tb.created_at ? ` · ${luc(tb.created_at)}` : ""}
                </p>
              </div>
              <div className="flex gap-2">
                <Link
                  href={noiXuLy(tb)}
                  className="rounded-md border border-[#bbc7bd] px-3 py-2 text-xs font-medium text-slate-800 hover:bg-reu-50"
                >
                  Mở
                </Link>
                {!tb.is_read && (
                  <button
                    type="button"
                    onClick={() => docMot(tb)}
                    className="rounded-md px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"
                  >
                    Đã đọc
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
