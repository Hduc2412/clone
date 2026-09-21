"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button, Card } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { currentAccount, login } from "@/lib/portalApi";

const INPUT =
  "mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-base outline-none focus:border-brand-400";

/**
 * Đăng nhập hệ khách hàng bằng số điện thoại.
 *
 * Không có nút "đăng ký tài khoản", và đó là chủ ý: tài khoản chỉ do nhân viên
 * cấp sau khi hồ sơ được tiếp nhận. Mở cho tự đăng ký thì bảng khách hàng đầy
 * tài khoản không gắn với hồ sơ nào, và cũng không có gì để xem sau khi vào.
 *
 * Ô nhập số điện thoại để `inputMode="tel"` — phần lớn ứng viên vào bằng điện
 * thoại, và bàn phím số đỡ được một thao tác lẫn một loại lỗi gõ.
 */
export default function LoginForm() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Đã đăng nhập rồi mà mở lại trang này thì đi thẳng vào trong, đỡ bắt người ta
  // gõ lại số máy.
  useEffect(() => {
    currentAccount()
      .then((account) => {
        if (account) {
          router.replace(account.must_change_password ? "/tai-khoan/doi-mat-khau" : "/tai-khoan");
        }
      })
      .catch(() => undefined);
  }, [router]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    login(phone, password)
      .then((account) => {
        router.replace(account.must_change_password ? "/tai-khoan/doi-mat-khau" : "/tai-khoan");
      })
      .catch((reason) => setError(reason.message))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="mx-auto w-full max-w-md">
      <Card className="p-6 sm:p-8">
        <h1 className="text-xl font-bold text-slate-900">Đăng nhập</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Dành cho ứng viên đã được nhân viên cấp tài khoản. Đăng nhập bằng chính
          số điện thoại bạn để lại khi đăng ký.
        </p>

        <form onSubmit={submit} className="mt-6">
          <label className="block text-sm font-medium text-slate-700">
            Số điện thoại
            <input
              name="phone"
              inputMode="tel"
              autoComplete="tel"
              required
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="09xx xxx xxx"
              className={INPUT}
            />
          </label>

          <label className="mt-5 block text-sm font-medium text-slate-700">
            Mật khẩu
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={INPUT}
            />
          </label>

          {error && (
            <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <Button type="submit" className="mt-6 w-full" disabled={submitting}>
            {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
          </Button>
        </form>

        <p className="mt-5 text-center text-sm">
          <a
            href="/tai-khoan/quen-mat-khau"
            className="font-semibold text-brand-700 hover:underline"
          >
            Quên mật khẩu?
          </a>
        </p>

        <p className="mt-5 border-t border-slate-100 pt-5 text-sm leading-6 text-slate-600">
          Chưa có tài khoản? Tài khoản được nhân viên cấp sau khi hồ sơ của bạn
          đã được tiếp nhận. Cần hỗ trợ thì gọi{" "}
          <a href={COMPANY.hotlineHref} className="font-semibold text-brand-700">
            {COMPANY.hotline}
          </a>
          .
        </p>
      </Card>

      <p className="mt-6 text-center text-sm text-slate-500">
        Chưa nộp hồ sơ bao giờ?{" "}
        <a href="/tu-van" className="font-semibold text-brand-700 hover:underline">
          Đối chiếu hồ sơ miễn phí
        </a>
      </p>
    </div>
  );
}
