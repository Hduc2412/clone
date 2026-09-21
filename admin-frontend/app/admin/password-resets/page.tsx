"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { AuthUser, loadCurrentUser } from "@/lib/auth";
import { PasswordResetRequest, managementApi } from "@/lib/managementApi";

const SUBJECT_LABELS: Record<string, string> = {
  candidate: "Ứng viên",
  staff: "Nhân viên",
};

function formatMoment(iso: string): string {
  const moment = new Date(iso);
  if (Number.isNaN(moment.getTime())) return "";
  return moment.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Hàng đợi yêu cầu đặt lại mật khẩu.
 *
 * Hệ thống chưa có cổng SMS hay email nên không gửi mã tự động được. Người thật
 * xác minh người thật: nhân viên gọi cho ứng viên, quản trị viên hỏi lại nhân
 * viên. Màn hình này là chỗ họ làm việc đó.
 *
 * Tư vấn viên chỉ thấy yêu cầu của ứng viên — máy chủ lọc sẵn theo vai trò, nên
 * giao diện không cần (và không được) dựa vào việc tự ẩn đi.
 */
export default function PasswordResetsPage() {
  const [items, setItems] = useState<PasswordResetRequest[]>([]);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    managementApi
      .passwordResetRequests()
      .then((data) => setItems(data.items))
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  useEffect(() => {
    loadCurrentUser().then(setUser).catch(() => setUser(null));
  }, []);

  const handle = (item: PasswordResetRequest) => {
    const who = item.full_name ? `${item.full_name} (${item.subject_id})` : item.subject_id;
    if (!window.confirm(`Đặt lại mật khẩu cho ${who} về mặc định?`)) return;
    setBusy(item.code);
    setError("");
    managementApi
      .handlePasswordReset(item.code)
      .then((result) => {
        // Hiện bằng hộp thoại vì nhân viên phải đọc dãy này cho người kia ngay
        // trong cuộc gọi. Một dòng nhỏ trong bảng rất dễ bị cuộn qua.
        window.alert(
          `Đã đặt lại mật khẩu cho ${result.full_name || result.subject_id}.\n\n` +
            `Mật khẩu mặc định: ${result.default_password}\n\n` +
            "Đọc cho họ ngay. Hệ thống sẽ bắt họ đổi mật khẩu ngay sau khi đăng nhập.",
        );
      })
      .catch((reason) => setError(reason.message))
      .finally(() => {
        setBusy(null);
        load();
      });
  };

  const canHandleStaff = user?.role === "admin" || user?.role === "manager";

  return (
    <>
      <PageHeader
        eyebrow="Mật khẩu"
        title="Yêu cầu đặt lại mật khẩu"
        description="Ứng viên quên mật khẩu thì nhân viên đặt lại. Nhân viên quên thì Quản lý hoặc Quản trị viên đặt lại. Đặt xong, người đó buộc phải đổi mật khẩu ngay lần đăng nhập tới."
      />

      {error && <ErrorBanner message={error} />}

      {loading ? (
        <p className="text-sm text-slate-400">Đang tải…</p>
      ) : items.length === 0 ? (
        <EmptyState
          title="Không có yêu cầu nào đang chờ"
          description="Khi ứng viên hoặc nhân viên bấm quên mật khẩu, yêu cầu của họ hiện ở đây."
        />
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const isStaff = item.subject_type === "staff";
            const blocked = isStaff && !canHandleStaff;
            return (
              <article
                key={item.code}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${
                          isStaff
                            ? "bg-violet-50 text-violet-700 ring-violet-200"
                            : "bg-sky-50 text-sky-700 ring-sky-200"
                        }`}
                      >
                        {SUBJECT_LABELS[item.subject_type] || item.subject_type}
                      </span>
                      <p className="font-semibold text-slate-900">
                        {item.full_name || item.subject_id}
                      </p>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {item.subject_id} · {item.code} · gửi {formatMoment(item.created_at)}
                    </p>
                    {item.note && (
                      <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
                        “{item.note}”
                      </p>
                    )}
                  </div>

                  <button
                    type="button"
                    disabled={busy === item.code || blocked}
                    onClick={() => handle(item)}
                    title={
                      blocked
                        ? "Chỉ Quản lý và Quản trị viên đặt lại mật khẩu cho nhân viên"
                        : undefined
                    }
                    className="rounded-xl bg-[#cb1d1e] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {busy === item.code ? "Đang đặt lại…" : "Đặt lại mật khẩu"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}
