import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import {
  Button,
  Card,
  Section,
  SectionHeading,
} from "@/components/ui/primitives";
import { COMPANY, REFERENCE_NOTE } from "@/content/site";
import { COSTS } from "@/content/pages";

export const metadata: Metadata = {
  title: "Chi phí",
  description:
    "Các khoản chi phí khi tham gia chương trình điều dưỡng Nhật Bản và thời điểm đóng từng khoản.",
};

export default function CostsPage() {
  return (
    <>
      <PageHero
        eyebrow="Chi phí"
        title="Các khoản phải đóng và đóng vào lúc nào"
        lead="Chi phí chia theo giai đoạn, không phải đóng toàn bộ ngay từ đầu. Mức cụ thể khác nhau theo từng diện chương trình và từng đơn hàng."
      >
        <div className="flex flex-wrap gap-3">
          <Button href="/tu-van">Xem đơn phù hợp và chi phí từng đơn</Button>
          <Button href={COMPANY.hotlineHref} variant="outline">
            Gọi {COMPANY.hotline}
          </Button>
        </div>
      </PageHero>

      <Section>
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3.5">Khoản</th>
                  <th className="px-5 py-3.5">Mức</th>
                  <th className="px-5 py-3.5">Đóng khi nào</th>
                  <th className="px-5 py-3.5">Ghi chú</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {COSTS.map((cost) => (
                  <tr key={cost.item}>
                    <td className="px-5 py-4 font-medium text-slate-900">
                      {cost.item}
                    </td>
                    <td className="px-5 py-4 text-slate-700">{cost.amount}</td>
                    <td className="px-5 py-4 text-slate-700">{cost.when}</td>
                    <td className="px-5 py-4 leading-6 text-slate-500">
                      {cost.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
          {REFERENCE_NOTE} Con số cuối cùng luôn được ghi trong hợp đồng trước khi
          bạn đóng bất kỳ khoản nào.
        </p>
      </Section>

      <section className="bg-slate-50">
        <Section>
          <div className="grid gap-8 lg:grid-cols-2">
            <div>
              <SectionHeading
                eyebrow="Tự bảo vệ mình"
                title="Bốn điều nên làm trước khi đóng tiền"
                lead="Áp dụng với mọi công ty phái cử, không riêng ở đây."
              />
              <ol className="mt-6 space-y-4 text-sm leading-6 text-slate-600">
                {[
                  "Yêu cầu xem giấy phép hoạt động dịch vụ đưa người lao động đi làm việc ở nước ngoài, kiểm tra còn hiệu lực.",
                  "Đọc hợp đồng và đối chiếu từng khoản với bảng trên. Khoản nào không có trong hợp đồng thì không đóng.",
                  "Lấy phiếu thu cho mọi khoản đã nộp, kể cả khoản nhỏ. Không chuyển tiền vào tài khoản cá nhân.",
                  "Hỏi rõ điều gì xảy ra nếu phỏng vấn không đỗ: khoản nào hoàn, khoản nào không, và được chuyển sang đơn khác hay không.",
                ].map((tip, index) => (
                  <li key={index} className="flex gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
                      {index + 1}
                    </span>
                    {tip}
                  </li>
                ))}
              </ol>
            </div>

            <Card className="h-fit p-6">
              <h3 className="text-sm font-semibold text-slate-900">
                Vì sao trang này không ghi một con số tổng
              </h3>
              <div className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
                <p>
                  Vì không có con số nào đúng cho tất cả mọi người. Diện EPA rẻ hơn
                  hẳn hai diện còn lại do có hỗ trợ từ chương trình hợp tác hai
                  chính phủ. Trong cùng một diện, chi phí còn khác nhau theo cơ sở
                  tiếp nhận và theo việc bạn học tiếng bao lâu.
                </p>
                <p>
                  Một con số tổng đưa ra bừa sẽ hoặc làm bạn hụt hẫng lúc ký hợp
                  đồng, hoặc làm bạn bỏ qua một cơ hội rẻ hơn thực tế. Nên ở đây
                  liệt kê đủ các khoản và thời điểm đóng, còn con số cụ thể thì
                  gắn với từng đơn hàng.
                </p>
              </div>
              <div className="mt-5">
                <Button href="/don-hang" variant="outline" size="sm">
                  Xem chi phí ước tính theo đơn
                </Button>
              </div>
            </Card>
          </div>
        </Section>
      </section>
    </>
  );
}
