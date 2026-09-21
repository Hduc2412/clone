"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { PageHeader } from "@/components/admin/AdminUI";
import { AuthUser, changePassword, loadCurrentUser } from "@/lib/auth";

const INPUT =
  "mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-red-400";

const MIN_LENGTH = 8;

/**
 * Đổi mật khẩu cho nhân viên — bắt buộc sau khi quản trị viên đặt lại.
 *
 * Trang này nằm dưới `/admin` nhưng phải gọi được ngay cả khi tài khoản đang bị
 * chặn: máy chủ trả 409 cho mọi endpoint khác khi `must_change_password` còn
 * bật, và chỉ chừa ba cửa — xem mình là ai, đổi mật khẩu, đăng xuất. Nếu trang
 * này cũng bị chặn thì người vừa bị đặt lại mật khẩu sẽ không có đường nào ra.
 */
export default function StaffChangePasswordPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadCurrentUser()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setChecking(false));
  }, [router]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = String(form.get("new_password") || "");
    if (next !== String(form.get("repeat") || "")) {
      setError("Hai ô mật khẩu mới chưa giống nhau.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await changePassword(String(form.get("current_password") || ""), next);
      router.replace("/admin");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không đổi được mật khẩu.");
    } finally {
      setSubmitting(false);
    }
  };

  if (checking) return <p className="text-sm text-slate-400">Đang kiểm tra tài khoản…</p>;

  return (
    <>
      <PageHeader
        eyebrow="Tài khoản"
        title="Đổi mật khẩu"
        description="Đặt mật khẩu riêng cho tài khoản của bạn."
      />

      <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {user?.must_change_password && (
          <p className="mb-5 rounded-xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
            Mật khẩu hiện tại là dãy mặc định quản trị viên vừa đặt lại, nên có
            hơn một người biết. Bạn phải đặt mật khẩu riêng trước khi dùng tiếp
            hệ thống.
          </p>
        )}

        <form onSubmit={submit} className="space-y-4">
          <label className="block text-sm font-medium text-slate-700">
            Mật khẩu hiện tại
            <input
              required
              type="password"
              name="current_password"
              autoComplete="current-password"
              className={INPUT}
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Mật khẩu mới
            <input
              required
              minLength={MIN_LENGTH}
              type="password"
              name="new_password"
              autoComplete="new-password"
              className={INPUT}
            />
            <span className="mt-1 block text-xs font-normal text-slate-500">
              Ít nhất {MIN_LENGTH} ký tự.
            </span>
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Nhập lại mật khẩu mới
            <input
              required
              type="password"
              name="repeat"
              autoComplete="new-password"
              className={INPUT}
            />
          </label>

          {error && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
          )}

          <button
            disabled={submitting}
            className="w-full rounded-xl bg-[#cb1d1e] px-4 py-3 font-semibold text-white disabled:opacity-60"
          >
            {submitting ? "Đang lưu…" : "Đặt mật khẩu mới"}
          </button>
        </form>
      </div>
    </>
  );
}
