import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import JobOrderCard from "@/components/site/JobOrderCard";
import { Button, Card, Container, Section } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { fetchJobOrders, type PublicJobOrder } from "@/lib/publicApi";

export const metadata: Metadata = {
  title: "Đơn hàng đang tuyển",
  description:
    "Danh sách đơn hàng điều dưỡng, hộ lý Nhật Bản đang tuyển, lọc theo tỉnh, vùng, loại hình cơ sở, diện chương trình và trình độ tiếng Nhật.",
};

type SearchParams = {
  prefecture?: string;
  region_group?: string;
  employer_type?: string;
  program?: string;
  japanese_required?: string;
};

/**
 * Trang danh sách đơn hàng.
 *
 * Bộ lọc dùng biểu mẫu GET thường chứ không phải JavaScript phía trình duyệt.
 * Nhờ vậy kết quả lọc nằm trên đường dẫn nên chia sẻ được cho người khác, quay
 * lại bằng nút back vẫn đúng, và trang vẫn dùng được khi JavaScript chưa tải xong.
 */
export default async function JobOrdersPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const filters = {
    prefecture: searchParams.prefecture,
    region_group: searchParams.region_group,
    employer_type: searchParams.employer_type,
    program: searchParams.program,
    japanese_required: searchParams.japanese_required,
    limit: 60,
  };

  // Danh sách đầy đủ dùng để dựng các ô chọn: nếu chỉ dựa vào kết quả đã lọc thì
  // chọn một tỉnh xong các tỉnh khác biến mất khỏi ô chọn, không đổi lại được.
  const [orders, allOrders] = await Promise.all([
    fetchJobOrders(filters),
    fetchJobOrders({ limit: 100 }),
  ]);

  const hasFilter = Object.entries(searchParams).some(
    ([, value]) => value !== undefined && value !== "",
  );

  return (
    <>
      <PageHero
        eyebrow="Đơn hàng"
        title="Đơn hàng đang tuyển"
        lead="Mỗi đơn ghi rõ điều kiện bắt buộc và thông tin tham khảo. Đơn hết hạn nộp hoặc tạm dừng tuyển tự động không còn hiển thị ở đây."
      >
        <Button href="/tu-van">Đối chiếu hồ sơ với các đơn này</Button>
      </PageHero>

      <Container className="py-8">
        <form
          method="get"
          className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card"
        >
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
            <Select
              name="prefecture"
              label="Tỉnh tại Nhật"
              value={searchParams.prefecture}
              options={optionsFrom(allOrders, (order) => [
                order.prefecture,
                order.prefecture,
              ])}
            />
            <Select
              name="region_group"
              label="Vùng"
              value={searchParams.region_group}
              options={optionsFrom(allOrders, (order) =>
                order.region_group
                  ? [order.region_group, order.labels.region_group || order.region_group]
                  : null,
              )}
            />
            <Select
              name="employer_type"
              label="Loại hình cơ sở"
              value={searchParams.employer_type}
              options={optionsFrom(allOrders, (order) => [
                order.employer_type,
                order.labels.employer_type || order.employer_type,
              ])}
            />
            <Select
              name="program"
              label="Diện chương trình"
              value={searchParams.program}
              options={optionsFrom(allOrders, (order) => [
                order.program,
                order.labels.program || order.program,
              ])}
            />
            <Select
              name="japanese_required"
              label="Tiếng Nhật tối thiểu"
              value={searchParams.japanese_required}
              options={optionsFrom(allOrders, (order) => [
                order.requirements.japanese_required,
                order.labels.japanese_required ||
                  order.requirements.japanese_required,
              ])}
            />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              className="inline-flex min-h-[44px] items-center rounded-xl bg-brand-600 px-5 text-sm font-medium text-white hover:bg-brand-700"
            >
              Lọc đơn hàng
            </button>
            {hasFilter && (
              <a
                href="/don-hang"
                className="text-sm font-medium text-slate-500 hover:text-slate-800"
              >
                Bỏ lọc
              </a>
            )}
            <p className="ml-auto text-sm text-slate-500">
              {orders.length} đơn phù hợp
              {hasFilter ? ` trên tổng ${allOrders.length}` : ""}
            </p>
          </div>
        </form>
      </Container>

      <Section className="!pt-2">
        {orders.length === 0 ? (
          <Card className="border-dashed px-6 py-16 text-center">
            <p className="font-medium text-slate-700">
              {hasFilter
                ? "Không có đơn nào khớp bộ lọc này"
                : "Hiện chưa có đơn hàng nào được công bố"}
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
              {hasFilter
                ? "Thử bỏ bớt một tiêu chí, hoặc để lại số điện thoại để nhân viên báo khi có đơn phù hợp."
                : `Gọi ${COMPANY.hotline} hoặc để lại số điện thoại, nhân viên sẽ báo ngay khi có đơn mới.`}
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              {hasFilter && (
                <Button href="/don-hang" variant="outline">
                  Xem tất cả đơn
                </Button>
              )}
              <Button href="/lien-he">Để lại số điện thoại</Button>
            </div>
          </Card>
        ) : (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {orders.map((order) => (
              <JobOrderCard key={order.code} order={order} />
            ))}
          </div>
        )}
      </Section>
    </>
  );
}

/** Gom giá trị duy nhất từ danh sách đơn thành các lựa chọn đã sắp xếp. */
function optionsFrom(
  orders: PublicJobOrder[],
  pick: (order: PublicJobOrder) => [string, string] | null,
): { value: string; label: string }[] {
  const map = new Map<string, string>();
  for (const order of orders) {
    const pair = pick(order);
    if (pair && pair[0]) map.set(pair[0], pair[1]);
  }
  return Array.from(map, ([value, label]) => ({ value, label })).sort((a, b) =>
    a.label.localeCompare(b.label, "vi"),
  );
}

function Select({
  name,
  label,
  value,
  options,
}: {
  name: string;
  label: string;
  value?: string;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="block text-sm">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <select
        name={name}
        defaultValue={value ?? ""}
        className="mt-1.5 min-h-[44px] w-full rounded-xl border border-slate-200 px-3 text-sm"
      >
        <option value="">Tất cả</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
