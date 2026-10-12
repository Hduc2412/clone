"use client";

import Link from "next/link";
import { useState } from "react";
import BangDoiChieu from "@/components/candidate/BangDoiChieu";
import { Badge, Button, Card } from "@/components/ui/primitives";
import { MatchItem } from "@/lib/candidateApi";
import { daysUntil, formatDate } from "@/lib/format";

/**
 * Một đơn trong danh sách gợi ý.
 *
 * Bảng đối chiếu (✓ ở tiêu chí đạt, xem `BangDoiChieu`) mở được chứ không ẩn đi:
 * ứng viên có quyền biết vì sao đơn này được giới thiệu cho mình. Nhưng mặc định
 * thu gọn, vì mười một dòng tiêu chí hiện cùng lúc cho năm đơn thì không ai đọc —
 * muốn xem kỹ một đơn thì vào phòng tư vấn riêng của đơn đó, ở đấy bảng hiện sẵn.
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
  // "Còn thiếu: Khu vực: khu vực Hyogo, mong muốn Kantō" từng hiện ở đây — nhưng đó
  // là nguyện vọng KHÔNG KHỚP, không phải thông tin còn thiếu (08/10). Thẻ trong danh
  // sách đều đã đạt điều kiện bắt buộc, nên chỗ khác biệt chỉ có thể là nguyện vọng.
  const khacNguyenVong = item.soft_rows
    .filter((r) => r.points === 0 && r.outcome !== undefined && r.outcome !== "unknown")
    .map((r) => `${r.label}: đơn ${r.requirement_text}, bạn ${r.candidate_text}`);
  const khongDat = item.hard_rows.filter((r) => r.result === "KHONG_DAT");

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 p-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {/* Nhãn thứ hạng chỉ hiện khi thứ hạng có nghĩa.
                Chưa nêu nguyện vọng thì mọi đơn đạt đều 0 điểm mềm, nên thứ tự
                chỉ do hạn nộp và mã đơn quyết. Dán "Phù hợp nhất #1" lên một
                thứ tự ngẫu nhiên là biến nó thành một lời khuyên. */}
            {item.rank !== null && item.score_ranked !== false && (
              <Badge tone="brand">Phù hợp nhất #{item.rank}</Badge>
            )}
            {item.rank !== null && item.score_ranked === false && (
              <Badge tone="neutral">Đủ điều kiện nộp</Badge>
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

        {/* Chưa nêu nguyện vọng nào thì KHÔNG hiện số.
            Điểm mềm đo mức khớp với nguyện vọng; chưa có nguyện vọng thì nó
            đo một thứ chưa tồn tại, và "5/100" cạnh "đạt điều kiện bắt buộc"
            đọc thành "chỉ hợp 5%". */}
        <div className="shrink-0 text-right">
          {item.score_ranked === false ? (
            <p className="max-w-[9rem] text-xs leading-5 text-slate-500">
              Chưa xếp hạng được — bạn nêu nguyện vọng để hệ thống so thứ tự.
            </p>
          ) : (
            <>
              <p className="text-3xl font-semibold text-ink-900">{item.score}</p>
              <p className="text-xs text-slate-500">/100 khớp nguyện vọng</p>
            </>
          )}
        </div>
      </div>

      <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-4">
        <p className="text-sm leading-6 text-slate-700">{item.explanation_text}</p>

        {khongDat.length > 0 && (
          <p className="mt-2.5 text-sm text-amber-800">
            <span className="font-medium">Chưa đạt:</span> {khongDat.map((r) => r.label).join(" · ")}
          </p>
        )}
        {khacNguyenVong.length > 0 && (
          <p className="mt-2.5 text-sm text-slate-600">
            <span className="font-medium">Khác nguyện vọng của bạn:</span> {khacNguyenVong.join(" · ")}
          </p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="min-h-[44px] text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            {open ? "Thu gọn bảng đối chiếu" : "Xem bảng đối chiếu"}
          </button>

          <Link
            href={`/tu-van/don/${item.code}`}
            className="flex min-h-[44px] items-center text-sm font-medium text-slate-600 hover:text-brand-700"
          >
            Tư vấn riêng đơn này
          </Link>

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
            {khacNguyenVong.length > 0 && (
              <p className="mt-2 text-sm text-slate-600">
                Đơn này khác nguyện vọng bạn đã nêu ở: {khacNguyenVong.join(" · ")}
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
        <div className="border-t border-slate-100 px-5 py-4">
          <BangDoiChieu
            rows={item.hard_rows}
            softRows={item.soft_rows}
            eligible={item.eligible}
            score={item.score}
            scoreRanked={item.score_ranked}
          />
        </div>
      )}
    </Card>
  );
}
