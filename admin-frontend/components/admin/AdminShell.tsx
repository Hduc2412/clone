"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { managementApi } from "@/lib/managementApi";
import { AuthUser, loadCurrentUser, logout } from "@/lib/auth";
import { SU_KIEN_THONG_BAO } from "@/lib/thongBao";
import { chuVietTat } from "@/lib/chuVietTat";

const navigation = [
  { href: "/admin", label: "Tổng quan", icon: "▦" },
  { href: "/admin/queue", label: "Hàng đợi hồ sơ", icon: "⇥" },
  // Hai hàng đợi tách nhau có chủ ý: trên là hồ sơ đăng ký của khách đã đủ
  // điều kiện; dưới là yêu cầu của khách phần lớn CHƯA đủ điều kiện nhưng vẫn
  // muốn nói chuyện. Hai nhịp việc khác nhau, trộn thì việc gấp bị lỡ.
  { href: "/admin/support", label: "Hàng đợi hỗ trợ", icon: "☏" },
  { href: "/admin/appointments", label: "Lịch hẹn", icon: "◷" },
  { href: "/admin/leads", label: "Khách hàng", icon: "♙" },
  { href: "/admin/profiles", label: "Hồ sơ ứng viên", icon: "☺" },
  { href: "/admin/applications", label: "Hồ sơ tuyển dụng", icon: "▤" },
  { href: "/admin/job-orders", label: "Đơn tuyển dụng", icon: "▣" },
  { href: "/admin/courses", label: "Khóa học tiếng Nhật", icon: "▨" },
  { href: "/admin/recommendation-logs", label: "Nhật ký giới thiệu", icon: "◈" },
  { href: "/admin/conversations", label: "Hội thoại", icon: "◌" },
  { href: "/admin/knowledge", label: "Tri thức AI", icon: "◇" },
  { href: "/admin/staff-scores", label: "Điểm hiệu suất", icon: "★" },
  { href: "/admin/password-resets", label: "Đặt lại mật khẩu", icon: "⚿" },
  { href: "/admin/users", label: "Người dùng", icon: "♧" },
  { href: "/admin/audit-logs", label: "Nhật ký hệ thống", icon: "≡" },
];

/** Trang chỉ Admin/Manager dùng. Một danh sách cho cả thanh bên lẫn việc chặn khi gõ
 *  thẳng địa chỉ (12/10): trước đó consultant mở `/admin/users` vẫn thấy khung trang và
 *  nút "Thêm người dùng" — máy chủ vẫn từ chối, nhưng trang không nên hiện ra. */
const CHI_QUAN_LY = ["/admin/users", "/admin/audit-logs"];

export default function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  // Số lịch hẹn đang chờ xử lý — KHÁC với số thông báo chưa đọc.
  //
  // Bản trước gắn `unread` lên chính mục "Lịch hẹn". Hai con số không liên quan
  // gì nhau: toàn bộ thông báo hiện có là hồ sơ mới đăng ký và tin nhắn khách
  // để lại, không có cái nào là lịch hẹn. Nhân viên thấy "10" cạnh chữ Lịch hẹn,
  // bấm vào thì màn hình trống — một con số nói sai nhãn của chính nó.
  const [lichCho, setLichCho] = useState(0);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    loadCurrentUser()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setCheckingAuth(false));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    const load = () => {
      // Lịch chờ theo PHẠM VI người xem (12/10): số của trang tổng quan là cả hệ thống,
      // consultant thấy "34" mà mở danh sách thì 0 lịch.
      managementApi
        .pendingAppointmentCount()
        .then((data) => setLichCho(data.count))
        .catch(() => setLichCho(0));
      // Số thông báo theo PHẠM VI người xem (12/10). Trước đó lấy tổng của cả hệ thống
      // từ trang tổng quan: consultant thấy cả việc của người khác, và con số chỉ tăng.
      managementApi
        .notificationCount()
        .then((data) => setUnread(data.count))
        .catch(() => setUnread(0));
    };
    load();
    const interval = window.setInterval(load, 30000);
    window.addEventListener(SU_KIEN_THONG_BAO, load);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener(SU_KIEN_THONG_BAO, load);
    };
  }, [user]);

  if (checkingAuth || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-kem text-sm text-slate-500">
        Đang kiểm tra phiên đăng nhập...
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
    router.refresh();
  };

  return (
    <div className="min-h-screen bg-kem text-slate-900">
      {open && (
        <button
          aria-label="Đóng menu"
          className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        // Thanh bên sáng theo bản thiết kế 08/10 ("Không gian làm việc"), thay nền tối.
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-200 bg-kem-dam text-slate-800 transition-transform duration-200 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 border-b border-slate-200 px-6 py-5">
          <span
            aria-hidden
            className="grid h-10 w-10 shrink-0 place-items-center bg-brand-600 text-sm font-semibold text-white"
            style={{ borderRadius: "50% 50% 5px 50%", fontFamily: "var(--font-serif, Georgia), Georgia, serif" }}
          >
            DC
          </span>
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">Không gian làm việc</p>
            <h1 className="mt-0.5 text-base font-semibold text-slate-900">Trung tâm quản lý</h1>
          </div>
        </div>
        {/* `min-h-0 overflow-y-auto`: 16 mục cao hơn màn hình ≤ ~900px. Trước 12/10 thanh
            này không cuộn được, khối tài khoản bị đẩy khỏi màn hình và nút "Thoát" không
            bấm được trên máy tính xách tay thường. */}
        <nav className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
          {navigation
            .filter((item) => !CHI_QUAN_LY.includes(item.href) || user.role !== "consultant")
            .map((item) => {
            const active =
              item.href === "/admin"
                ? pathname === item.href
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                  active
                    ? "bg-reu-100 font-semibold text-slate-900"
                    : "text-slate-600 hover:bg-white/70 hover:text-slate-900"
                }`}
              >
                <span aria-hidden className="w-5 text-center text-base text-slate-500">{item.icon}</span>
                {item.label}
                {item.href === "/admin/appointments" && lichCho > 0 && (
                  <span className="ml-auto rounded-full bg-brand-600 px-2 py-0.5 text-[11px] font-bold text-white">
                    {lichCho}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 p-4">
          <div className="flex items-center gap-3 rounded-xl bg-white/70 p-3">
            <div
              className="flex h-9 w-9 items-center justify-center rounded-full bg-[#e9e6db] text-sm text-[#776f57]"
              style={{ fontFamily: "var(--font-serif, Georgia), Georgia, serif" }}
            >
              {chuVietTat(user.full_name)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-900">{user.full_name}</p>
              <p className="text-xs capitalize text-slate-500">{user.role}</p>
            </div>
            <button onClick={handleLogout} className="ml-auto rounded-md px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50">Thoát</button>
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200 bg-[#fbfaf7]/95 px-4 backdrop-blur md:px-8">
          <button
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Mở menu"
          >
            ☰
          </button>
          <div className="hidden lg:block">
            <p className="text-sm font-medium text-slate-700">
              Hệ thống tư vấn và quản lý tuyển dụng
            </p>
            <p className="text-xs text-slate-400">
              Dữ liệu cập nhật từ backend local
            </p>
          </div>
          {/* Trỏ về trang Thông báo (12/10). Trước đó trỏ hàng đợi hồ sơ vì chưa màn hình
            * nào đọc `/notifications` — con số chỉ tăng, không ai đánh dấu đã đọc được. */}
          <Link
            href="/admin/notifications"
            className="relative rounded-md border border-[#bbc7bd] bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-reu-50"
          >
            Thông báo
            {unread > 0 && (
              <span className="ml-2 rounded-full bg-brand-600 px-2 py-0.5 text-xs font-semibold text-white">
                {unread}
              </span>
            )}
          </Link>
        </header>
        <main className="p-4 md:p-8">
          {user.role === "consultant" && CHI_QUAN_LY.some((p) => pathname === p || pathname.startsWith(`${p}/`)) ? (
            <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800" role="alert">
              Trang này chỉ dành cho Admin và Manager.
            </p>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
