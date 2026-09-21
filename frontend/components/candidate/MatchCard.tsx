"use client";

import { useState } from "react";
import { Badge, Button, Card } from "@/components/ui/primitives";
import { MatchItem } from "@/lib/candidateApi";
import { daysUntil, formatDate } from "@/lib/format";

const RESULT_STYLE: Record<string, string> = {
  DAT: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  KHONG_DAT: "bg-brand-50 text-brand-700 ring-brand-200",
  CHUA_RO: "bg-amber-50 text-amber-700 ring-amber-200",
};

const RESULT_LABEL: Record<string, string> = {
  DAT: "Đạt",
  KHONG_DAT: "Chưa đạt",
  CHUA_RO: "Chưa rõ",
};

/**
 * Một đơn trong danh sách gợi ý.
 *
 * Bảng tiêu chí mở được chứ không ẩn đi: ứng viên có quyền biết vì sao đơn này
 * được giới thiệu cho mình. Nhưng mặc định thu gọn, vì mười một dòng tiêu chí
 * hiện cùng lúc cho năm đơn thì không ai đọc.
 *
 * ## Đăng ký phải qua hai lần bấm
 *
 * Bấm "Đăng ký đơn này" chưa gửi gì cả — nó mở ra một khung nói rõ chuyện sắp
 * xảy ra: hồ sơ sẽ chuyển cho nhân viên và họ sẽ gọi điện. Chỉ lần bấm thứ hai
 * mới gửi thật.
 *
 * Một lần bấm là đủ về mặt kỹ thuật, nhưng đây là lúc ứng viên giao số điện
 * thoại và hồ sơ của mình cho người lạ gọi tới. Bấm nhầm vào thứ đó thì không
 * rút lại được bằng nút "hoàn tác" nào.
 */
export default function MatchCard({
  item,
  onRegister,
  registering = false,
  registered = false,
  disabled = false,
}: {
  item: MatchItem;
  onRegister?: (code: string) => void;
  registering?: boolean;
  registered?: boolean;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const remaining = daysUntil(item.deadline);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 p-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {item.rank !== null && (
              <Badge tone="brand">Phù hợp nhất #{item.rank}</Badge>
            )}
            <Badge tone="neutral">{item.labels.program ?? item.program}</Badge>
            <Badge tone="neutral">
              {item.labels.employer_type ?? item.employer_type}
            </Badge>
          </div>
          <h3 className="mt-2.5 text-lg font-semibold text-ink-900">{item.title}</h3>
          <p className="mt-1 text-sm text-slate-600">
            {item.employer_name} · {item.prefecture}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Mã {item.code} · hạn nộp {formatDate(item.deadline)}
            {remaining !== null && remaining >= 0 && (
              <span className={remaining <= 14 ? " text-brand-600" : ""}>
                {" "}
                · còn {remaining} ngày
              </span>
            )}
          </p>
        </div>

        <div className="shrink-0 text-right">
          <p className="text-3xl font-semibold text-ink-900">{item.score}</p>
          <p className="text-xs text-slate-500">trên 100 điểm phù hợp</p>
        </div>
      </div>

      <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-4">
        <p className="text-sm leading-6 text-slate-700">{item.explanation_text}</p>

        {item.gaps.length > 0 && (
          <p className="mt-2.5 text-sm text-amber-800">
            <span className="font-medium">Còn thiếu:</span> {item.gaps.join(" · ")}
          </p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="min-h-[44px] text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            {open ? "Thu gọn bảng tiêu chí" : "Xem từng tiêu chí đạt hay chưa"}
          </button>

          {onRegister && item.eligible && !registered && !confirming && (
            <Button
              size="sm"
              variant="secondary"
              disabled={disabled}
              onClick={() => setConfirming(true)}
            >
              Đăng ký đơn này
            </Button>
          )}

          {registered && <Badge tone="success">Đã đăng ký</Badge>}
        </div>

        {onRegister && confirming && !registered && (
          <div className="mt-4 rounded-xl border border-brand-200 bg-white p-4">
            <p className="text-sm font-medium text-ink-900">
              Đăng ký đơn {item.code} — {item.title}?
            </p>
            <p className="mt-1.5 text-sm leading-6 text-slate-600">
              Hồ sơ của bạn sẽ được chuyển cho nhân viên tư vấn kèm kết quả đối
              chiếu này. Nhân viên gọi lại trong giờ làm việc để trao đổi các bước
              tiếp theo. Đây chưa phải là ký hợp đồng hay đóng bất kỳ khoản nào.
            </p>
            {item.gaps.length > 0 && (
              <p className="mt-2 text-sm text-amber-800">
                Nhân viên sẽ hỏi thêm về: {item.gaps.join(" · ")}
              </p>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                size="sm"
                disabled={registering}
                onClick={() => onRegister(item.code)}
              >
                {registering ? "Đang gửi…" : "Xác nhận đăng ký"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={registering}
                onClick={() => setConfirming(false)}
              >
                Để sau
              </Button>
            </div>
          </div>
        )}
      </div>

      {open && (
        <div className="overflow-x-auto border-t border-slate-100">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-2.5 font-medium">Tiêu chí</th>
                <th className="px-5 py-2.5 font-medium">Đơn yêu cầu</th>
                <th className="px-5 py-2.5 font-medium">Hồ sơ của bạn</th>
                <th className="px-5 py-2.5 font-medium">Kết quả</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {item.hard_rows.map((row) => (
                <tr key={row.key}>
                  <td className="px-5 py-2.5 text-slate-500">
                    <span className="mr-1.5 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase">
                      bắt buộc
                    </span>
                    {row.label}
                  </td>
                  <td className="px-5 py-2.5 text-slate-700">{row.requirement_text}</td>
                  <td className="px-5 py-2.5 text-slate-700">{row.candidate_text}</td>
                  <td className="px-5 py-2.5">
                    <span
                      className={`rounded-lg px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
                        RESULT_STYLE[row.result] ?? ""
                      }`}
                    >
                      {RESULT_LABEL[row.result] ?? row.result}
                    </span>
                  </td>
                </tr>
              ))}
              {item.soft_rows.map((row) => (
                <tr key={row.key} className="bg-slate-50/50">
                  <td className="px-5 py-2.5 text-slate-500">
                    <span className="mr-1.5 rounded bg-sky-50 px-1.5 py-0.5 text-[10px] uppercase text-sky-600">
                      nguyện vọng
                    </span>
                    {row.label}
                  </td>
                  <td className="px-5 py-2.5 text-slate-700">{row.requirement_text}</td>
                  <td className="px-5 py-2.5 text-slate-700">{row.candidate_text}</td>
                  <td className="px-5 py-2.5 text-slate-600">
                    +{row.points}
                    <span className="text-xs text-slate-400"> / {row.max_points}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
