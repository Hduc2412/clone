"use client";

import { Badge, Card } from "@/components/ui/primitives";
import {
  CLOSED_STATES,
  STAGES,
  formatDate,
  stageIndex,
} from "@/lib/applicationStages";
import { PortalApplication } from "@/lib/portalApi";

/** Thanh tiến trình năm chặng. Dùng chung bảng chặng với trang công khai. */
export function ProgressTrack({ status }: { status: string }) {
  const current = stageIndex(status);
  return (
    <ol className="mt-4 space-y-4">
      {STAGES.map((stage, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <li key={stage.key} className="flex gap-3">
            <span
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                active
                  ? "bg-brand-600 text-white"
                  : done
                    ? "bg-brand-100 text-brand-700"
                    : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? "✓" : index + 1}
            </span>
            <div className="min-w-0">
              <p
                className={`text-sm font-medium ${
                  active ? "text-slate-900" : done ? "text-slate-600" : "text-slate-400"
                }`}
              >
                {stage.label}
                {active && (
                  <span className="ml-2 align-middle">
                    <Badge tone="brand">Bước hiện tại</Badge>
                  </span>
                )}
              </p>
              {active && (
                <p className="mt-1 text-xs leading-5 text-slate-500">{stage.note}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function ApplicationCard({ item }: { item: PortalApplication }) {
  const closed = CLOSED_STATES[item.status];
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-base font-semibold text-slate-900">
            {item.job_order_title || item.job_order_code || "Đơn tuyển dụng"}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {item.job_order_code && `Mã đơn ${item.job_order_code} · `}
            Mã hồ sơ {item.application_code}
            {item.created_at && ` · Đăng ký ${formatDate(item.created_at)}`}
          </p>
        </div>
        {closed && <Badge tone={closed.tone}>{closed.label}</Badge>}
      </div>

      {closed ? (
        <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
          {closed.note}
        </p>
      ) : (
        <ProgressTrack status={item.status} />
      )}
    </Card>
  );
}
