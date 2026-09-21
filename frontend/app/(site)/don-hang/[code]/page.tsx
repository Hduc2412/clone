import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import PhotoBackdrop from "@/components/site/PhotoBackdrop";
import JobOrderCard from "@/components/site/JobOrderCard";
import {
  Badge,
  Button,
  Card,
  Container,
  Section,
  SectionHeading,
} from "@/components/ui/primitives";
import { COMPANY, REFERENCE_NOTE } from "@/content/site";
import {
  ageRangeText,
  daysUntil,
  formatDate,
  formatSalaryRange,
  formatVnd,
  formatYears,
} from "@/lib/format";
import { fetchJobOrder, fetchJobOrders } from "@/lib/publicApi";

export async function generateMetadata({
  params,
}: {
  params: { code: string };
}): Promise<Metadata> {
  const order = await fetchJobOrder(params.code);
  if (!order) return { title: "Không tìm thấy đơn hàng" };
  return {
    title: order.title,
    description: `${order.title} tại ${order.prefecture}. Yêu cầu tiếng Nhật ${order.labels.japanese_required}, hạn nộp ${formatDate(order.deadline)}.`,
  };
}

export default async function JobOrderDetailPage({
  params,
}: {
  params: { code: string };
}) {
  const order = await fetchJobOrder(params.code);
  if (!order) notFound();

  const related = (await fetchJobOrders({ limit: 12 }))
    .filter((item) => item.code !== order.code)
    .filter(
      (item) =>
        item.region_group === order.region_group ||
        item.employer_type === order.employer_type,
    )
    .slice(0, 3);

  const remaining = daysUntil(order.deadline);

  // Hai nhóm thông tin cố ý tách rời nhau. Nhóm trên quyết định ứng viên có bị
  // loại hay không; nhóm dưới chỉ để tham khảo và xếp hạng. Trộn hai nhóm vào
  // một bảng là cách làm người đọc tưởng lương cũng là điều kiện dự tuyển.
  const hardRequirements = [
    { label: "Tiếng Nhật tối thiểu", value: order.labels.japanese_required },
    {
      label: "Bằng cấp tối thiểu",
      value: order.labels.education_required || "Không yêu cầu",
    },
    {
      label: "Kinh nghiệm tối thiểu",
      value: formatYears(order.requirements.experience_min),
    },
    {
      label: "Độ tuổi",
      value: ageRangeText(order.requirements.age_min, order.requirements.age_max),
    },
    { label: "Giới tính", value: order.labels.gender_pref },
    { label: "Hạn nộp hồ sơ", value: formatDate(order.deadline) },
  ];

  const reference = [
    {
      label: "Lương cơ bản",
      value: formatSalaryRange(
        order.reference.salary_min,
        order.reference.salary_max,
      ),
    },
    {
      label: "Chi phí ước tính",
      value: formatVnd(order.reference.cost_total_vnd),
    },
    {
      label: "Phỏng vấn dự kiến",
      value: formatDate(order.reference.interview_date),
    },
    {
      label: "Xuất cảnh dự kiến",
      value: order.reference.departure_expected || "Chưa xác định",
    },
    { label: "Số lượng tuyển", value: `${order.quota} người` },
    {
      label: "Nơi làm việc",
      value: `${order.city ? `${order.city}, ` : ""}${order.prefecture}`,
    },
  ];

  return (
    <>
      <section className="relative overflow-hidden border-b border-slate-100">
        <PhotoBackdrop variant="soft" />
        <Container className="relative py-10 md:py-14">
          <Link
            href="/don-hang"
            className="text-sm font-medium text-slate-500 hover:text-brand-700"
          >
            ← Tất cả đơn hàng
          </Link>

          <div className="mt-5 flex flex-wrap gap-1.5">
            <Badge tone="brand">{order.labels.program}</Badge>
            <Badge tone="neutral">{order.labels.employer_type}</Badge>
            {order.labels.region_group && (
              <Badge tone="info">{order.labels.region_group}</Badge>
            )}
          </div>

          <h1 className="mt-4 max-w-3xl text-2xl font-bold leading-tight tracking-tight text-slate-900 md:text-4xl">
            {order.title}
          </h1>
          <p className="mt-3 text-base text-slate-600">
            {order.employer_name} · {order.prefecture} · Mã đơn {order.code}
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Button href={`/tu-van?don=${order.code}`} size="lg">
              Kiểm tra hồ sơ của tôi với đơn này
            </Button>
            <Button href={COMPANY.hotlineHref} variant="outline" size="lg">
              Gọi {COMPANY.hotline}
            </Button>
            <span
              className={`text-sm ${
                remaining !== null && remaining <= 14
                  ? "font-medium text-amber-700"
                  : "text-slate-500"
              }`}
            >
              {remaining === null
                ? "Đã hết hạn nộp"
                : `Còn ${remaining} ngày nộp hồ sơ`}
            </span>
          </div>
        </Container>
      </section>

      <Section>
        <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          <Card className="border-amber-200 p-6">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900">
                Điều kiện bắt buộc
              </h2>
              <Badge tone="warning">Dùng để xét duyệt</Badge>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Thiếu một trong những mục dưới đây là hồ sơ không được nhận vào đơn
              này. Hệ thống đối chiếu đúng các mục này khi giới thiệu đơn cho bạn.
            </p>
            <dl className="mt-5 divide-y divide-slate-100">
              {hardRequirements.map((item) => (
                <div
                  key={item.label}
                  className="flex items-baseline justify-between gap-4 py-3"
                >
                  <dt className="text-sm text-slate-500">{item.label}</dt>
                  <dd className="text-right text-sm font-semibold text-slate-900">
                    {item.value}
                  </dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900">
                Thông tin tham khảo
              </h2>
              <Badge tone="neutral">Không dùng để loại</Badge>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Dùng để bạn so sánh giữa các đơn. Những mục này không bao giờ là lý
              do khiến hồ sơ bị loại.
            </p>
            <dl className="mt-5 divide-y divide-slate-100">
              {reference.map((item) => (
                <div
                  key={item.label}
                  className="flex items-baseline justify-between gap-4 py-3"
                >
                  <dt className="text-sm text-slate-500">{item.label}</dt>
                  <dd className="text-right text-sm font-semibold text-slate-900">
                    {item.value}
                  </dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>

        {(order.reference.allowances.length > 0 ||
          order.reference.highlights.length > 0 ||
          order.description) && (
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            {order.description && (
              <Card className="p-6">
                <h2 className="text-sm font-semibold text-slate-900">
                  Mô tả công việc
                </h2>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  {order.description}
                </p>
              </Card>
            )}

            <div className="space-y-6">
              {order.reference.highlights.length > 0 && (
                <Card className="p-6">
                  <h2 className="text-sm font-semibold text-slate-900">
                    Điểm nổi bật
                  </h2>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                    {order.reference.highlights.map((item) => (
                      <li key={item} className="flex gap-2.5">
                        <span
                          aria-hidden
                          className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500"
                        />
                        {item}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {order.reference.allowances.length > 0 && (
                <Card className="p-6">
                  <h2 className="text-sm font-semibold text-slate-900">Phụ cấp</h2>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {order.reference.allowances.map((item) => (
                      <Badge key={item} tone="success">
                        {item}
                      </Badge>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          </div>
        )}

        <p className="mt-6 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
          {REFERENCE_NOTE}
        </p>
      </Section>

      {related.length > 0 && (
        <section className="bg-slate-50">
          <Section>
            <SectionHeading
              eyebrow="Có thể bạn quan tâm"
              title="Đơn hàng tương tự"
              lead="Cùng vùng hoặc cùng loại hình cơ sở với đơn bạn đang xem."
            />
            <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {related.map((item) => (
                <JobOrderCard key={item.code} order={item} />
              ))}
            </div>
          </Section>
        </section>
      )}
    </>
  );
}
