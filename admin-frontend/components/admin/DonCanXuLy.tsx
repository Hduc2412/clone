"use client";

/**
 * "Đơn cần xử lý" trên trang tổng quan — chỉ Admin/Manager (12/10).
 *
 * Hai loại việc, cùng một chỗ:
 *
 * 1. **Đơn quá hạn chưa gỡ.** Lấy thẳng từ danh sách đơn (trạng thái "Đang tuyển" mà hạn
 *    nộp đã qua), không lấy từ thông báo — Admin đánh dấu đã đọc mà chưa gỡ thì đơn vẫn
 *    phải nằm đây. Đơn đã tự ẩn khỏi website; nút "Gỡ đơn" chuyển nó sang "Hết hạn".
 * 2. **Thông báo về chỉ tiêu** chưa đọc: đơn vừa đủ chỉ tiêu (đã tự ẩn), hoặc một người
 *    trúng tuyển rút/hủy nên trả lại chỉ tiêu (đơn KHÔNG tự mở lại — Admin quyết).
 *
 * Đổi trạng thái đơn ở đây hay ở trang đơn đều tắt các thông báo của đơn ấy (máy chủ).
 */
import Link from "next/link";
import { useEffect, useState } from "react";
import { loadCurrentUser } from "@/lib/auth";
import { JobOrder, Notification, managementApi } from "@/lib/managementApi";

function ngay(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return d ? `${d}/${m}/${y}` : iso;
}

export default function DonCanXuLy({
  orders,
  homNay,
  onDaDoi,
}: {
  orders: JobOrder[];
  homNay: string;
  onDaDoi: () => void;
}) {
  const [duocXem, setDuocXem] = useState(false);
  const [thongBao, setThongBao] = useState<Notification[]>([]);
  const [dangLam, setDangLam] = useState("");
  const [loi, setLoi] = useState("");

  useEffect(() => {
    loadCurrentUser()
      .then((u) => setDuocXem(u.role === "admin" || u.role === "manager"))
      .catch(() => setDuocXem(false));
  }, []);

  useEffect(() => {
    if (!duocXem) return;
    managementApi
      .notifications(true)
      .then((ds) => setThongBao(ds.filter((t) => t.reference_type === "job_order" && t.type !== "job_order.expired")))
      .catch(() => setThongBao([]));
  }, [duocXem, orders]);

  if (!duocXem) return null;

  const quaHan = orders.filter((o) => o.status === "open" && o.deadline < homNay);
  if (quaHan.length === 0 && thongBao.length === 0) return null;

  const goDon = async (code: string) => {
    setDangLam(code);
    setLoi("");
    try {
      await managementApi.setJobOrderStatus(code, "expired", "Gỡ đơn quá hạn từ trang tổng quan");
      onDaDoi();
    } catch (reason) {
      setLoi(reason instanceof Error ? reason.message : "Không gỡ được đơn.");
    } finally {
      setDangLam("");
    }
  };

  const daXem = async (code: string) => {
    try {
      await managementApi.markNotificationRead(code);
      setThongBao((ds) => ds.filter((t) => t.reference_code !== code));
    } catch (reason) {
      setLoi(reason instanceof Error ? reason.message : "Không đánh dấu được.");
    }
  };

  return (
    <section className="mt-6 rounded-[10px] border border-amber-200 bg-white p-5" aria-labelledby="don-can-xu-ly">
      <h3 id="don-can-xu-ly" className="text-sm font-semibold text-slate-900">
        Đơn cần xử lý
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        Đơn quá hạn và đơn đủ chỉ tiêu đã tự ẩn khỏi website. Ở đây là phần còn chờ bạn quyết định.
      </p>
      {loi && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{loi}</p>}

      <ul className="mt-4 divide-y divide-slate-200">
        {quaHan.map((o) => (
          <li key={`han-${o.code}`} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="text-sm text-slate-900">
                <Link href={`/admin/job-orders/${o.code}`} className="font-medium hover:text-brand-600">
                  {o.code}
                </Link>{" "}
                · {o.title}
              </p>
              <p className="mt-0.5 text-xs text-amber-800">
                Hết hạn nộp ngày {ngay(o.deadline)} — đã tự ẩn khỏi website, trạng thái vẫn &quot;Đang tuyển&quot;.
              </p>
            </div>
            <button
              type="button"
              disabled={dangLam === o.code}
              onClick={() => goDon(o.code)}
              className="rounded-md bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {dangLam === o.code ? "Đang gỡ…" : "Gỡ đơn (chuyển Hết hạn)"}
            </button>
          </li>
        ))}
        {thongBao.map((t) => (
          <li key={`tb-${t.reference_code}-${t.created_at}`} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <p className="min-w-0 text-sm text-slate-800">{t.title}</p>
            <div className="flex gap-2">
              <Link
                href={`/admin/job-orders/${t.reference_code}`}
                className="rounded-md border border-[#bbc7bd] px-3 py-2 text-xs font-medium text-slate-800 hover:bg-reu-50"
              >
                Mở đơn
              </Link>
              <button
                type="button"
                onClick={() => t.reference_code && daXem(t.reference_code)}
                className="rounded-md px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                Đã xem
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
