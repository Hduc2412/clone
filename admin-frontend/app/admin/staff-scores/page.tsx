"use client";

/**
 * Sổ điểm hiệu suất.
 *
 * Bảng luật hiển thị ngay cạnh bảng điểm, không giấu trong tài liệu. Nhân viên
 * phải đọc được cái luật đang áp lên mình — giấu đi thì điểm số thành một con số
 * trời cho, và người ta sẽ không tin nó.
 *
 * Bấm vào một dòng là mở ra **từng dòng điểm**, không phải một biểu đồ. Câu hỏi
 * thật của người xem là "điểm này ở đâu ra", và câu trả lời đúng là danh sách
 * việc đã làm, kèm ngày giờ.
 */
import { FormEvent, useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { loadCurrentUser } from "@/lib/auth";
import {
  ScoreRule,
  ScoreTotal,
  StaffLedger,
  StaffUser,
  managementApi,
} from "@/lib/managementApi";

export default function StaffScoresPage() {
  const [totals, setTotals] = useState<ScoreTotal[]>([]);
  const [rules, setRules] = useState<ScoreRule[]>([]);
  const [staff, setStaff] = useState<StaffUser[]>([]);
  const [ledger, setLedger] = useState<StaffLedger | null>(null);
  const [openEmail, setOpenEmail] = useState<string | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const range = { dateFrom: dateFrom || undefined, dateTo: dateTo || undefined };

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    managementApi
      .scoreboard({ dateFrom: dateFrom || undefined, dateTo: dateTo || undefined })
      .then((payload) => {
        setTotals(payload.items);
        setRules(payload.rules);
      })
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [dateFrom, dateTo]);

  useEffect(load, [load]);

  useEffect(() => {
    loadCurrentUser()
      .then(async (user) => {
        const allowed = user.role === "admin" || user.role === "manager";
        setCanManage(allowed);
        if (allowed) setStaff(await managementApi.users());
      })
      .catch(() => undefined);
  }, []);

  const nameOf = (email: string) =>
    staff.find((person) => person.email === email)?.full_name ?? email;

  const openLedger = (email: string) => {
    if (openEmail === email) {
      setOpenEmail(null);
      setLedger(null);
      return;
    }
    setOpenEmail(email);
    setLedger(null);
    managementApi
      .staffLedger(email, range)
      .then(setLedger)
      .catch((reason) => setError(reason.message));
  };

  const adjust = async (event: FormEvent<HTMLFormElement>, email: string) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const points = Number(form.get("points"));
    const note = String(form.get("note") ?? "").trim();
    if (!points || note.length < 5) {
      setError("Cần nhập số điểm khác 0 và lý do ít nhất 5 ký tự.");
      return;
    }
    setError("");
    try {
      await managementApi.adjustScore(email, points, note);
      setNotice(`Đã ghi điều chỉnh ${points > 0 ? "+" : ""}${points} cho ${nameOf(email)}.`);
      event.currentTarget.reset();
      load();
      managementApi.staffLedger(email, range).then(setLedger).catch(() => undefined);
    } catch (reason) {
      setError((reason as Error).message);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Nhân sự"
        title="Điểm hiệu suất"
        description="Mỗi điểm trỏ về đúng một việc đã làm, có ngày giờ và mã hồ sơ kèm theo. Không có chỗ nào chứa một con số tổng sửa trực tiếp được — tổng luôn là tổng của các dòng bên dưới."
      />
      {error && <ErrorBanner message={error} />}
      {notice && (
        <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      <section className="mb-6 flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Từ ngày
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Đến ngày
          <input
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700"
          />
        </label>
        <button
          type="button"
          onClick={() => {
            setDateFrom("");
            setDateTo("");
          }}
          className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Toàn bộ thời gian
        </button>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div>
          {loading ? (
            <p className="text-sm text-slate-400">Đang tải…</p>
          ) : totals.length === 0 ? (
            <EmptyState
              title="Chưa có điểm nào"
              description="Điểm sinh ra từ việc đã làm: nhận hồ sơ trong hàng đợi, gọi được cho khách và ghi kết quả, hồ sơ đi tới bước xuất cảnh."
            />
          ) : (
            <ul className="space-y-3">
              {totals.map((row) => (
                <li
                  key={row.staff_email}
                  className="rounded-2xl border border-slate-200 bg-white shadow-sm"
                >
                  <button
                    type="button"
                    onClick={() => openLedger(row.staff_email)}
                    className="flex w-full flex-wrap items-center justify-between gap-4 p-5 text-left hover:bg-slate-50"
                  >
                    <div>
                      <p className="font-semibold text-slate-800">
                        {nameOf(row.staff_email)}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {row.staff_email} · {row.events} lượt ghi nhận
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-semibold text-slate-900">
                        {row.points}
                      </p>
                      <p className="text-xs text-slate-400">điểm</p>
                    </div>
                  </button>

                  {openEmail === row.staff_email && (
                    <div className="border-t border-slate-100 p-5">
                      {!ledger ? (
                        <p className="text-sm text-slate-400">Đang tải sổ điểm…</p>
                      ) : (
                        <>
                          <div className="mb-4 flex flex-wrap gap-2">
                            {ledger.breakdown.map((item) => (
                              <span
                                key={item.action}
                                className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
                              >
                                {item.label}: {item.points} điểm / {item.events} lượt
                              </span>
                            ))}
                          </div>

                          <ul className="space-y-1.5">
                            {ledger.events.map((item) => (
                              <li
                                key={item.code}
                                className="flex flex-wrap items-baseline gap-x-3 border-b border-slate-50 py-1.5 text-sm last:border-0"
                              >
                                <span
                                  className={`w-10 shrink-0 text-right font-medium ${
                                    item.points > 0
                                      ? "text-emerald-700"
                                      : item.points < 0
                                        ? "text-brand-600"
                                        : "text-slate-400"
                                  }`}
                                >
                                  {item.points > 0 ? "+" : ""}
                                  {item.points}
                                </span>
                                <span className="text-slate-700">{item.label}</span>
                                {item.reference_code && (
                                  <span className="text-xs text-slate-400">
                                    {item.reference_code}
                                  </span>
                                )}
                                {item.source === "manual" && (
                                  <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] text-amber-700">
                                    quản lý ghi
                                  </span>
                                )}
                                {item.note && (
                                  <span className="text-xs italic text-slate-500">
                                    {item.note}
                                  </span>
                                )}
                                <span className="ml-auto text-xs text-slate-400">
                                  {new Date(item.occurred_at).toLocaleString("vi-VN")}
                                </span>
                              </li>
                            ))}
                          </ul>

                          {canManage && (
                            <form
                              onSubmit={(event) => adjust(event, row.staff_email)}
                              className="mt-5 flex flex-wrap items-end gap-3 rounded-xl bg-slate-50 p-4"
                            >
                              <label className="flex flex-col gap-1 text-xs text-slate-500">
                                Điều chỉnh
                                <input
                                  name="points"
                                  type="number"
                                  min={-50}
                                  max={50}
                                  placeholder="+5"
                                  className="w-24 rounded-xl border border-slate-200 px-3 py-2 text-sm"
                                />
                              </label>
                              <label className="flex flex-1 flex-col gap-1 text-xs text-slate-500">
                                Lý do (bắt buộc)
                                <input
                                  name="note"
                                  placeholder="Trực hỗ trợ cuối tuần"
                                  className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
                                />
                              </label>
                              <button
                                type="submit"
                                className="rounded-xl bg-[#cb1d1e] px-4 py-2 text-sm font-medium text-white hover:bg-[#a81718]"
                              >
                                Ghi vào sổ
                              </button>
                            </form>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700">Luật tính điểm</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Luật này áp cho tất cả, và hiện ở đây để ai cũng đọc được.
          </p>
          <ul className="mt-4 space-y-2">
            {rules.map((rule) => (
              <li
                key={rule.action}
                className="flex items-baseline justify-between gap-3 text-sm"
              >
                <span className="text-slate-600">{rule.label}</span>
                <span
                  className={`shrink-0 font-medium ${
                    rule.points > 0 ? "text-emerald-700" : "text-slate-400"
                  }`}
                >
                  {rule.points > 0 ? "+" : ""}
                  {rule.points}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">
            Trả hồ sơ về hàng đợi được ghi vào sổ nhưng <strong>không bị trừ điểm</strong>.
            Phạt ở đó chỉ khiến người ta giữ chặt hồ sơ mình không xử lý nổi, và
            người chịu là ứng viên ngồi chờ.
          </p>
        </aside>
      </div>
    </>
  );
}
