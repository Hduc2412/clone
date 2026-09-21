"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import {
  CriterionRow,
  MatchItem,
  RecommendationLog,
  SoftRow,
  managementApi,
} from "@/lib/managementApi";

const RESULT_STYLE: Record<string, string> = {
  DAT: "bg-emerald-50 text-emerald-700",
  KHONG_DAT: "bg-rose-50 text-rose-700",
  CHUA_RO: "bg-amber-50 text-amber-700",
};

const RESULT_LABEL: Record<string, string> = {
  DAT: "ĐẠT",
  KHONG_DAT: "KHÔNG ĐẠT",
  CHUA_RO: "CHƯA RÕ",
};

export default function RecommendationLogDetailPage() {
  const params = useParams<{ code: string }>();
  const code = params.code;

  const [log, setLog] = useState<RecommendationLog | null>(null);
  const [error, setError] = useState("");
  const [rerunning, setRerunning] = useState(false);
  const [showRejected, setShowRejected] = useState(true);

  const load = useCallback(() => {
    setError("");
    managementApi
      .recommendationLog(code)
      .then(setLog)
      .catch((reason) => setError(reason.message));
  }, [code]);

  useEffect(load, [load]);

  const rerun = async () => {
    if (!log) return;
    setRerunning(true);
    setError("");
    try {
      const fresh = await managementApi.rerunMatching(log.profile_code);
      window.location.href = `/admin/recommendation-logs/${fresh.code}`;
    } catch (reason) {
      setError((reason as Error).message);
      setRerunning(false);
    }
  };

  if (error && !log) return <ErrorBanner message={error} />;
  if (!log) return <p className="text-sm text-slate-500">Đang tải…</p>;

  const eligible = log.items.filter((item) => item.eligible);
  const rejected = log.items.filter((item) => !item.eligible);

  return (
    <>
      <PageHeader
        eyebrow={`Nhật ký ${log.code}`}
        title={`Đối chiếu hồ sơ ${log.profile_code}`}
        description={`Bản hồ sơ ${log.profile_version}, đối chiếu theo ngày ${log.as_of}. Kết quả dưới đây là bản đã lưu lúc đó, không phải bản tính lại hôm nay.`}
        action={
          <div className="flex flex-wrap gap-2">
            <Link
              href="/admin/recommendation-logs"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700"
            >
              Về danh sách
            </Link>
            <button
              type="button"
              onClick={rerun}
              disabled={rerunning}
              className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
            >
              {rerunning ? "Đang chạy…" : "Chạy lại trên dữ liệu hôm nay"}
            </button>
          </div>
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Đơn đã xét" value={String(log.total_considered)} />
        <Stat label="Đơn đạt điều kiện" value={String(log.eligible_count)} tone="emerald" />
        <Stat label="Đơn bị loại" value={String(rejected.length)} tone="rose" />
        <Stat label="Nguồn chạy" value={log.trigger} hint={log.actor_email ?? undefined} />
      </section>

      <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Điều kiện tái lập kết quả</h2>
        <p className="mt-1 text-xs text-slate-500">
          Cùng bốn dấu vân tay này thì chạy lại chắc chắn ra cùng một kết quả. Khác một cái là kết
          quả có quyền khác, và đó là cách để biết vì sao nó khác.
        </p>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Meta label="Bộ đối chiếu" value={log.engine_version} />
          <Meta label="Bộ trọng số" value={`${log.weights_version} · ${log.weights_fingerprint}`} />
          <Meta label="Danh mục đơn" value={log.orders_fingerprint} />
          <Meta label="Kho đơn đem xét" value={JSON.stringify(log.pool_query)} />
        </dl>
      </section>

      {log.missing_info.length > 0 && (
        <section className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="text-sm font-semibold text-amber-900">Hồ sơ còn thiếu</h2>
          <p className="mt-1 text-xs text-amber-800">
            Những thông tin này chưa có nên một số tiêu chí phải để CHƯA RÕ. Thiếu dữ liệu không
            loại đơn nào — nhưng hỏi được thì kết quả sẽ chắc hơn.
          </p>
          <ul className="mt-3 list-inside list-disc text-sm text-amber-900">
            {log.missing_info.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </section>
      )}

      <h2 className="mb-3 text-sm font-semibold text-slate-900">
        Đơn đạt điều kiện ({eligible.length})
      </h2>
      <div className="mb-8 space-y-4">
        {eligible.map((item) => (
          <MatchCard key={item.code} item={item} />
        ))}
        {eligible.length === 0 && (
          <p className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">
            Không đơn nào đạt điều kiện trong lần đối chiếu này.
          </p>
        )}
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Đơn bị loại ({rejected.length})</h2>
        <button
          type="button"
          onClick={() => setShowRejected((value) => !value)}
          className="text-xs font-medium text-slate-500 hover:text-[#cb1d1e]"
        >
          {showRejected ? "Thu gọn" : "Xem lý do từng đơn"}
        </button>
      </div>
      {showRejected && (
        <div className="space-y-4">
          {rejected.map((item) => (
            <MatchCard key={item.code} item={item} />
          ))}
        </div>
      )}
    </>
  );
}

function MatchCard({ item }: { item: MatchItem }) {
  return (
    <article
      className={`overflow-hidden rounded-2xl border bg-white shadow-sm ${
        item.eligible ? "border-slate-200" : "border-rose-100"
      }`}
    >
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <p className="font-medium text-slate-900">{item.title}</p>
          <p className="mt-1 text-xs text-slate-400">
            {item.code} · {item.employer_name} · {item.prefecture} · hạn {item.deadline}
          </p>
        </div>
        <div className="text-right">
          {item.eligible ? (
            <>
              <p className="text-lg font-semibold text-slate-900">{item.score}/100</p>
              <p className="text-xs text-slate-400">hạng {item.rank}</p>
            </>
          ) : (
            // Đơn bị loại không hiện điểm. Ghi "45/100 · KHÔNG ĐẠT" cạnh nhau là
            // mời người đọc đem so sánh hai thứ không so sánh được.
            <span className="rounded-lg bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700">
              Bị loại
            </span>
          )}
        </div>
      </header>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-2.5">Tiêu chí</th>
              <th className="px-5 py-2.5">Đơn yêu cầu</th>
              <th className="px-5 py-2.5">Ứng viên</th>
              <th className="px-5 py-2.5">Kết quả</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {item.hard_rows.map((row) => (
              <HardRow key={row.key} row={row} />
            ))}
            {item.soft_rows.map((row) => (
              <SoftRowCells key={row.key} row={row} />
            ))}
          </tbody>
        </table>
      </div>

      {item.gaps.length > 0 && (
        <footer className="border-t border-slate-100 bg-slate-50 px-5 py-3 text-xs text-slate-600">
          {item.gaps.join(" · ")}
        </footer>
      )}
    </article>
  );
}

function HardRow({ row }: { row: CriterionRow }) {
  return (
    <tr>
      <td className="px-5 py-2.5 text-slate-500">
        <span className="mr-1.5 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-500">
          cứng
        </span>
        {row.label}
      </td>
      <td className="px-5 py-2.5 text-slate-600">{row.requirement_text}</td>
      <td className="px-5 py-2.5 text-slate-600">{row.candidate_text}</td>
      <td className="px-5 py-2.5">
        <span
          className={`rounded-lg px-2 py-0.5 text-xs font-medium ${RESULT_STYLE[row.result] ?? ""}`}
        >
          {RESULT_LABEL[row.result] ?? row.result}
        </span>
      </td>
    </tr>
  );
}

function SoftRowCells({ row }: { row: SoftRow }) {
  return (
    <tr className="bg-slate-50/40">
      <td className="px-5 py-2.5 text-slate-500">
        <span className="mr-1.5 rounded bg-sky-50 px-1.5 py-0.5 text-[10px] uppercase text-sky-600">
          mềm
        </span>
        {row.label}
      </td>
      <td className="px-5 py-2.5 text-slate-600">{row.requirement_text}</td>
      <td className="px-5 py-2.5 text-slate-600">{row.candidate_text}</td>
      <td className="px-5 py-2.5 text-slate-600">
        +{row.points}
        <span className="text-xs text-slate-400"> / {row.max_points}</span>
      </td>
    </tr>
  );
}

function Stat({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: string;
  tone?: "emerald" | "rose";
  hint?: string;
}) {
  const toneClass =
    tone === "emerald" ? "text-emerald-700" : tone === "rose" ? "text-rose-700" : "text-slate-900";
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 break-all font-mono text-xs text-slate-700">{value}</dd>
    </div>
  );
}
