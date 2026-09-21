"use client";

import { FormEvent, useState } from "react";
import { Button, Card } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { requestPasswordReset } from "@/lib/portalApi";

const INPUT =
  "mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-base outline-none focus:border-brand-400";

/**
 * Quên mật khẩu: gửi yêu cầu cho nhân viên thay vì tự phục hồi.
 *
 * Chưa có cổng SMS hay email nên không gửi mã tự động được. Thay vào đó, yêu cầu
 * vào hàng đợi của nhân viên — người vốn đã gọi điện cho ứng viên — và họ đặt
 * mật khẩu về dãy mặc định.
 *
 * Màn hình sau khi gửi **không** nói số này có tài khoản hay không. Máy chủ cũng
 * trả cùng một câu cho cả hai trường hợp: tách ra là biến ô này thành công cụ dò
 * xem số nào đã đăng ký.
 */
export default function ForgotPasswordForm() {
  const [phone, setPhone] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!phone.trim()) {
      setError("Bạn nhập số điện thoại đã đăng ký nhé.");
      return;
    }
    setSubmitting(true);
    setError("");
    requestPasswordReset(phone, note)
      .then(() => setSent(true))
      .catch((reason) => setError(reason.message))
      .finally(() => setSubmitting(false));
  };

  if (sent) {
    return (
      <div className="mx-auto w-full max-w-md">
        <Card className="p-6 sm:p-8">
          <h1 className="text-xl font-bold text-slate-900">Đã gửi yêu cầu</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Nhân viên sẽ đặt lại mật khẩu của bạn về mật khẩu mặc định và gọi báo
            cho bạn trong giờ làm việc. Sau đó bạn đăng nhập lại và đặt mật khẩu
            riêng ngay.
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Cần gấp thì gọi{" "}
            <a href={COMPANY.hotlineHref} className="font-semibold text-brand-700">
              {COMPANY.hotline}
            </a>
            .
          </p>
          <div className="mt-6">
            <Button href="/tai-khoan/dang-nhap" className="w-full">
              Về trang đăng nhập
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-md">
      <Card className="p-6 sm:p-8">
        <h1 className="text-xl font-bold text-slate-900">Quên mật khẩu</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Gửi yêu cầu cho nhân viên đặt lại mật khẩu. Hệ thống chưa gửi mã tự động
          qua tin nhắn, nên nhân viên sẽ gọi cho bạn để xác nhận.
        </p>

        <form onSubmit={submit} className="mt-6">
          <label className="block text-sm font-medium text-slate-700">
            Số điện thoại đã đăng ký
            <input
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
            Lời nhắn cho nhân viên
            <span className="ml-1 text-xs font-normal text-slate-400">(không bắt buộc)</span>
            <textarea
              rows={3}
              maxLength={300}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Ví dụ: chiều nay sau 5 giờ gọi em được ạ."
              className={INPUT}
            />
          </label>

          {error && (
            <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <Button type="submit" className="mt-6 w-full" disabled={submitting}>
            {submitting ? "Đang gửi…" : "Gửi yêu cầu"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Nhớ ra mật khẩu rồi?{" "}
          <a
            href="/tai-khoan/dang-nhap"
            className="font-semibold text-brand-700 hover:underline"
          >
            Đăng nhập
          </a>
        </p>
      </Card>
    </div>
  );
}
