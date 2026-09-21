import Link from "next/link";
import { Badge, Card } from "@/components/ui/primitives";
import { ageRangeText, daysUntil, formatDate, formatSalaryRange } from "@/lib/format";
import type { PublicJobOrder } from "@/lib/publicApi";

/**
 * Thẻ đơn hàng.
 *
 * Khác biệt lớn nhất so với trang thật của doanh nghiệp: ở đó mỗi đơn chỉ hiện
 * tên và dòng "Giá: liên hệ". Ở đây hiện đủ điều kiện bắt buộc ngay trên thẻ,
 * để ứng viên tự loại được đơn không hợp mà không phải mở ra đọc từng cái.
 */
export default function JobOrderCard({ order }: { order: PublicJobOrder }) {
  const remaining = daysUntil(order.deadline);
  const urgent = remaining !== null && remaining <= 14;

  return (
    <Card hover className="flex h-full flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          <Badge tone="brand">{order.labels.program}</Badge>
          <Badge tone="neutral">{order.labels.employer_type}</Badge>
        </div>
        <span className="shrink-0 text-xs font-medium text-slate-400">
          {order.code}
        </span>
      </div>

      <h3 className="mt-3 text-base font-semibold leading-6 text-slate-900">
        <Link href={`/don-hang/${order.code}`} className="hover:text-brand-700">
          {order.title}
        </Link>
      </h3>
      <p className="mt-1 text-sm text-slate-500">
        {order.employer_name} · {order.prefecture}
        {order.labels.region_group ? ` (${order.labels.region_group})` : ""}
      </p>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <Row label="Lương cơ bản">
          <span className="font-semibold text-brand-700">
            {formatSalaryRange(order.reference.salary_min, order.reference.salary_max)}
          </span>
        </Row>
        <Row label="Số lượng">{order.quota} người</Row>
        <Row label="Tiếng Nhật">{order.labels.japanese_required}</Row>
        <Row label="Độ tuổi">
          {ageRangeText(order.requirements.age_min, order.requirements.age_max)}
        </Row>
      </dl>

      <div className="mt-auto flex items-center justify-between gap-3 pt-5">
        <span className={`text-xs ${urgent ? "font-medium text-amber-700" : "text-slate-500"}`}>
          {remaining === null
            ? "Đã hết hạn nộp"
            : remaining === 0
              ? "Hạn nộp hôm nay"
              : `Còn ${remaining} ngày · hạn ${formatDate(order.deadline)}`}
        </span>
        <Link
          href={`/don-hang/${order.code}`}
          className="text-sm font-semibold text-brand-600 hover:text-brand-700"
        >
          Xem chi tiết →
        </Link>
      </div>
    </Card>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-slate-800">{children}</dd>
    </div>
  );
}
