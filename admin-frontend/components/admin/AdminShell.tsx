"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { managementApi } from "@/lib/managementApi";
import { AuthUser, loadCurrentUser, logout } from "@/lib/auth";

const navigation = [
  { href: "/admin", label: "Tổng quan", icon: "▦" },
  { href: "/admin/appointments", label: "Lịch hẹn", icon: "◷" },
  { href: "/admin/leads", label: "Khách hàng", icon: "♙" },
  { href: "/admin/conversations", label: "Hội thoại", icon: "◌" },
  { href: "/admin/knowledge", label: "Tri thức AI", icon: "◇" },
  { href: "/admin/users", label: "Người dùng", icon: "♧" },
  { href: "/admin/audit-logs", label: "Nhật ký hệ thống", icon: "≡" },
];

export default function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
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
        .then((data) => setUnread(data.notifications_unread))
        .catch(() => setUnread(0));
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
                {item.href === "/admin/appointments" && unread > 0 && (
                  <span className="ml-auto rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-[#cb1d1e]">
                    {unread}
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
          <Link
            href="/admin/appointments"
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
