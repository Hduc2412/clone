"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { loadCurrentUser } from "@/lib/auth";
import {
  ConsultationReport,
  QueuedRegistration,
  StaffUser,
  managementApi,
} from "@/lib/managementApi";

type Tab = "queue" | "mine";

function waitedFor(createdAt: string): string {
  const minutes = Math.floor((Date.now() - new Date(createdAt).getTime()) / 60000);
  if (minutes < 1) return "vừa xong";
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return `${Math.floor(hours / 24)} ngày trước`;
}

export default function QueuePage() {
  const [tab, setTab] = useState<Tab>("queue");
  const [items, setItems] = useState<QueuedRegistration[]>([]);
  const [report, setReport] = useState<ConsultationReport | null>(null);
  const [openCode, setOpenCode] = useState<string | null>(null);
  const [staff, setStaff] = useState<StaffUser[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const fetching =
      tab === "queue"
        ? managementApi.registrationQueue().then((payload) => payload.items)
        : managementApi.myRegistrations();
    fetching
      .then(setItems)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [tab]);

  useEffect(load, [load]);

  useEffect(() => {
    loadCurrentUser()
      .then(async (user) => {
        const allowed = user.role === "admin" || user.role === "manager";
        setCanManage(allowed);
        if (!allowed) return;
        const rows = await managementApi.users();
        setStaff(rows.filter((person) => person.status === "active"));
      })
      .catch(() => undefined);
  }, []);

  const openReport = (code: string) => {
    if (openCode === code) {
      setOpenCode(null);
      setReport(null);
      return;
    }
    setOpenCode(code);
    setReport(null);
    managementApi
      .registrationReport(code)
      .then(setReport)
      .catch((reason) => setError(reason.message));
  };

  // Mọi thao tác đổi người phụ trách đều có thể va nhau, nên kết thúc bằng một
  // lần tải lại — kể cả khi hỏng. Để người dùng nhìn danh sách cũ rồi bấm tiếp
  // là cách chắc chắn nhất để hỏng lần nữa.
  const run = (code: string, action: Promise<unknown>, success: string) => {
    setBusy(code);
    setError("");
    setNotice("");
    action
      .then(() => setNotice(success))
      .catch((reason) => setError(reason.message))
      .finally(() => {
        setBusy(null);
        load();
      });
  };

  const accept = (code: string) =>
    run(
      code,
      managementApi.acceptRegistration(code),
      `Bạn đã nhận xử lý hồ sơ ${code}.`,
    );

  const release = (code: string) => {
    const note = window.prompt("Lý do trả hồ sơ về hàng đợi?");
    if (!note) return;
    run(
      code,
      managementApi.releaseRegistration(code, note),
      `Đã trả hồ sơ ${code} về hàng đợi.`,
    );
  };

  const handover = (code: string, assignedTo: string) => {
    if (!assignedTo) return;
    const note = window.prompt(`Lý do chuyển hồ sơ cho ${assignedTo}?`);
    if (!note) return;
    run(
      code,
      managementApi.handoverRegistration(code, assignedTo, note),
      `Đã chuyển hồ sơ ${code} cho ${assignedTo}.`,
    );
  };

  return (
    <>
      <PageHeader
        eyebrow="Bàn giao"
        title="Hàng đợi hồ sơ đăng ký"
        description="Ứng viên đã tự xác nhận chọn đơn và đang chờ nhân viên liên hệ. Mỗi hồ sơ kèm sẵn Phiếu tóm tắt tư vấn — đọc phiếu là đủ bối cảnh để gọi điện, không phải mở lại từng màn hình."
        action={
          <button
            type="button"
            onClick={load}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            Tải lại
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}
      {notice && (
        <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      <div className="mb-6 inline-flex rounded-xl border border-slate-200 bg-white p-1">
        {(
          [
            ["queue", "Chưa ai nhận"],
            ["mine", "Tôi đang phụ trách"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              tab === key ? "bg-[#cb1d1e] text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Đang tải…</p>
      ) : items.length === 0 ? (
        <EmptyState
          title={tab === "queue" ? "Hàng đợi trống" : "Bạn chưa phụ trách hồ sơ nào"}
          description={
            tab === "queue"
              ? "Chưa có ứng viên nào đăng ký chờ xử lý. Hồ sơ mới sẽ xuất hiện ở đây ngay khi ứng viên xác nhận chọn đơn."
              : "Hồ sơ bạn nhận từ hàng đợi sẽ nằm ở đây, kèm phiếu tóm tắt và các thao tác bàn giao."
          }
        />
      ) : (
        <ul className="space-y-4">
          {items.map((item) => (
            <li
              key={item.application_code}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-base font-semibold text-slate-800">
                    {item.customer_name}{" "}
                    <span className="text-sm font-normal text-slate-400">
                      · {item.phone}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    Chọn đơn <span className="font-medium">{item.job_order_code}</span>
                    {item.job_order_title ? ` · ${item.job_order_title}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    {item.application_code} · hồ sơ{" "}
                    <Link
                      href={`/admin/profiles/${item.profile_code}`}
                      className="text-[#cb1d1e] hover:underline"
                    >
                      {item.profile_code}
                    </Link>
                    {item.japanese_level ? ` · ${item.japanese_level}` : ""} · đăng ký{" "}
                    {waitedFor(item.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => openReport(item.application_code)}
                    className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
                  >
                    {openCode === item.application_code ? "Đóng phiếu" : "Xem phiếu"}
                  </button>

                  {tab === "queue" ? (
                    <button
                      type="button"
                      disabled={busy === item.application_code}
                      onClick={() => accept(item.application_code)}
                      className="rounded-xl bg-[#cb1d1e] px-4 py-2 text-sm font-medium text-white hover:bg-[#a81718] disabled:opacity-60"
                    >
                      {busy === item.application_code ? "Đang nhận…" : "Nhận xử lý"}
                    </button>
                  ) : (
                    <>
                      {canManage && (
                        <select
                          defaultValue=""
                          disabled={busy === item.application_code}
                          onChange={(event) =>
                            handover(item.application_code, event.target.value)
                          }
                          className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600"
                        >
                          <option value="">Chuyển cho…</option>
                          {staff
                            .filter((person) => person.email !== item.assigned_to)
                            .map((person) => (
                              <option key={person.email} value={person.email}>
                                {person.full_name} ({person.email})
                              </option>
                            ))}
                        </select>
                      )}
                      <button
                        type="button"
                        disabled={busy === item.application_code}
                        onClick={() => release(item.application_code)}
                        className="rounded-xl border border-amber-300 px-4 py-2 text-sm font-medium text-amber-700 hover:bg-amber-50 disabled:opacity-60"
                      >
                        Trả về hàng đợi
                      </button>
                    </>
                  )}
                </div>
              </div>

              {openCode === item.application_code && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  {report ? (
                    <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-xs leading-5 text-slate-700">
                      {report.text}
                    </pre>
                  ) : (
                    <p className="text-sm text-slate-400">Đang tải phiếu…</p>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
