"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { managementApi } from "@/lib/managementApi";
import { AuthUser, loadCurrentUser, logout } from "@/lib/auth";

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
    const load = () =>
      managementApi
        .overview()
        .then((data) => {
          setUnread(data.notifications_unread);
          setLichCho(data.appointments_pending);
        })
        .catch(() => {
          setUnread(0);
          setLichCho(0);
        });
    load();
    const interval = window.setInterval(load, 30000);
    return () => window.clearInterval(interval);
  }, [user]);

  if (checkingAuth || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#171b22] text-sm text-slate-300">
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
    <div className="min-h-screen bg-[#f6f7f9] text-slate-900">
      {open && (
        <button
          aria-label="Đóng menu"
          className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-[#171b22] text-white transition-transform duration-200 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-white/10 px-6 py-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-red-400">
            DC Kaigo
          </p>
          <h1 className="mt-2 text-xl font-semibold">Trung tâm quản lý</h1>
          <p className="mt-1 text-xs text-slate-400">Điều dưỡng Nhật Bản</p>
        </div>
        <nav className="flex-1 space-y-1 px-4 py-6">
          {navigation
            .filter((item) => !["/admin/users", "/admin/audit-logs"].includes(item.href) || user.role !== "consultant")
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
                className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
                  active
                    ? "bg-[#cb1d1e] font-medium text-white shadow-lg shadow-red-950/30"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <span className="w-5 text-center text-lg">{item.icon}</span>
                {item.label}
                {item.href === "/admin/appointments" && lichCho > 0 && (
                  <span className="ml-auto rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-[#cb1d1e]">
                    {lichCho}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-4">
          <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-red-500/20 text-sm font-bold text-red-300">
              {user.full_name.split(" ").slice(-2).map((word) => word[0]).join("").toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{user.full_name}</p>
              <p className="text-xs capitalize text-slate-400">{user.role}</p>
            </div>
            <button onClick={handleLogout} className="ml-auto text-xs text-red-300">Thoát</button>
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur md:px-8">
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
          {/* Trỏ về hàng đợi hồ sơ, không phải lịch hẹn.
            *
            * Mọi thông báo hiện sinh ra đều thuộc một trong hai loại: hồ sơ mới
            * đăng ký (`application`) và tin nhắn khách để lại (`support_request`).
            * Không loại nào là lịch hẹn. Hàng đợi hồ sơ là chỗ xử lý loại đông
            * nhất, nên đưa người bấm về đó.
            *
            * Còn thiếu: API `/notifications` đã có đủ danh sách và nút đánh dấu
            * đã đọc, nhưng chưa màn hình nào đọc nó — nên con số này giảm được
            * chỉ khi nhân viên mở hồ sơ qua đường khác. Xem BAO_CAO_E2E_01_10.md.
            */}
          <Link
            href="/admin/queue"
            className="relative rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 shadow-sm hover:border-red-200"
          >
            Thông báo
            {unread > 0 && (
              <span className="ml-2 rounded-full bg-[#cb1d1e] px-2 py-0.5 text-xs font-semibold text-white">
                {unread}
              </span>
            )}
          </Link>
        </header>
        <main className="p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
