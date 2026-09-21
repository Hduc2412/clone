"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button, Card } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { PortalAccount, changePassword, currentAccount } from "@/lib/portalApi";

const INPUT =
  "mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-base outline-none focus:border-brand-400";

const MIN_LENGTH = 8;

/**
 * Đổi mật khẩu — bắt buộc ở lần đăng nhập đầu.
 *
 * Mật khẩu ban đầu do nhân viên đọc qua điện thoại, nghĩa là ít nhất hai người
 * biết nó. Để nguyên mà dùng tiếp thì tài khoản không thật sự là của riêng ứng
 * viên, nên máy chủ chặn mọi trang khác cho tới khi bước này xong.
 */
export default function ChangePasswordForm() {
  const router = useRouter();
  const [account, setAccount] = useState<PortalAccount | null>(null);
  const [checking, setChecking] = useState(true);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    currentAccount()
      .then((loaded) => {
        if (!loaded) {
          router.replace("/tai-khoan/dang-nhap");
          return;
        }
        setAccount(loaded);
      })
      .catch(() => router.replace("/tai-khoan/dang-nhap"))
      .finally(() => setChecking(false));
  }, [router]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Kiểm hai ô khớp nhau ở đây chứ không gửi lên máy chủ: máy chủ không biết
    // ô "nhập lại" tồn tại, và đây là lỗi gõ chứ không phải lỗi dữ liệu.
    if (next !== repeat) {
      setError("Hai ô mật khẩu mới chưa giống nhau.");
      return;
    }
    setSubmitting(true);
    setError("");
    changePassword(current, next)
      .then(() => router.replace("/tai-khoan"))
      .catch((reason) => setError(reason.message))
      .finally(() => setSubmitting(false));
  };

  if (checking) {
    return <p className="text-sm text-slate-500">Đang kiểm tra tài khoản…</p>;
  }

  return (
    <div className="mx-auto w-full max-w-md">
      <Card className="p-6 sm:p-8">
        <h1 className="text-xl font-bold text-slate-900">Đổi mật khẩu</h1>

        {account?.must_change_password ? (
          <p className="mt-3 rounded-xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
            Mật khẩu hiện tại là mật khẩu nhân viên đọc cho bạn qua điện thoại, nên
            có hơn một người biết. Bạn đặt mật khẩu riêng trước khi xem hồ sơ nhé.
          </p>
        ) : (
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Đặt mật khẩu mới cho tài khoản {account?.phone}.
          </p>
        )}

        <form onSubmit={submit} className="mt-6">
          <label className="block text-sm font-medium text-slate-700">
            Mật khẩu hiện tại
            <input
              type="password"
              autoComplete="current-password"
              required
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              className={INPUT}
            />
          </label>

          <label className="mt-5 block text-sm font-medium text-slate-700">
            Mật khẩu mới
            <input
              type="password"
              autoComplete="new-password"
              required
              minLength={MIN_LENGTH}
              value={next}
              onChange={(event) => setNext(event.target.value)}
              className={INPUT}
            />
            <span className="mt-1 block text-xs font-normal text-slate-500">
              Ít nhất {MIN_LENGTH} ký tự, và không phải một ký tự gõ lặp lại.
            </span>
          </label>

          <label className="mt-5 block text-sm font-medium text-slate-700">
            Nhập lại mật khẩu mới
            <input
              type="password"
              autoComplete="new-password"
              required
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
              className={INPUT}
            />
          </label>

          {error && (
            <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <Button type="submit" className="mt-6 w-full" disabled={submitting}>
            {submitting ? "Đang lưu…" : "Đặt mật khẩu mới"}
          </Button>
        </form>

        <p className="mt-6 text-xs leading-5 text-slate-500">
          Quên mật khẩu hiện tại thì gọi {COMPANY.hotline}, nhân viên cấp lại cho
          bạn một mật khẩu mới.
        </p>
      </Card>
    </div>
  );
}
