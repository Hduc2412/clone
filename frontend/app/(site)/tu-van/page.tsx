import type { Metadata } from "next";
import ConsultationFlow from "@/components/candidate/ConsultationFlow";
import PageHero from "@/components/site/PageHero";
import { Button, Card, Section, SectionHeading } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { fetchJobOrder } from "@/lib/publicApi";

export const metadata: Metadata = {
  title: "Tư vấn theo CV",
  description:
    "Nhập hồ sơ của bạn và xem mình đạt hay chưa đạt ở tiêu chí nào của từng đơn hàng điều dưỡng Nhật Bản.",
};

const STEPS = [
  {
    title: "Gửi và đọc CV",
    detail:
      "Gửi CV để hệ thống đọc năng lực và kinh nghiệm. Chưa có CV thì có thể khai nhanh bằng biểu mẫu thu gọn.",
  },
  {
    title: "Trao đổi với trợ lý",
    detail:
      "Trợ lý hỏi thêm thông tin thiếu, tư vấn hướng chuẩn bị và nguyện vọng. Bạn kiểm tra, xác nhận hồ sơ trước khi đối chiếu.",
  },
  {
    title: "Xem kết quả đối chiếu",
    detail:
      "Mỗi đơn hiện rõ từng tiêu chí đạt, chưa đạt hay chưa rõ, kèm điểm phù hợp với nguyện vọng của bạn.",
  },
  {
    title: "Chọn đơn và xác nhận đăng ký",
    detail:
      "Bạn tự chọn đơn muốn đăng ký. Khi xác nhận đăng ký hoặc yêu cầu hỗ trợ, hệ thống chuyển thông tin cho nhân viên tiếp nhận.",
  },
];

export default async function ConsultPage({
  searchParams,
}: {
  searchParams: { don?: string };
}) {
  const order = searchParams.don ? await fetchJobOrder(searchParams.don) : null;

  return (
    <>
      <PageHero
        eyebrow="Tư vấn theo CV"
        title="Biết mình hợp đơn nào, và vì sao"
        lead="Gửi CV, kiểm tra thông tin đã đọc rồi trò chuyện với trợ lý tư vấn. Khi bạn xác nhận hồ sơ, hệ thống đối chiếu từng đơn đang tuyển và giải thích kết quả."
      />

      <Section>
        {order && (
          <Card className="mb-8 border-brand-200 bg-brand-50/50 p-5">
            <p className="text-sm text-slate-600">
              Bạn vừa xem đơn{" "}
              <span className="font-semibold text-slate-900">{order.title}</span>{" "}
              ({order.code}). Sau khi nhập hồ sơ, đơn này sẽ được đánh dấu trong
              kết quả đối chiếu.
            </p>
          </Card>
        )}

        <ConsultationFlow />
      </Section>

      <section className="bg-slate-50">
        <Section>
          <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
            <div>
              <SectionHeading
                eyebrow="Bốn bước"
                title="Từ CV đến tư vấn và chọn đơn"
                lead="Bạn dừng ở bước nào cũng được, thông tin đã nhập được giữ lại cho phiên của bạn."
              />
              <ol className="mt-8 space-y-5">
                {STEPS.map((step, index) => (
                  <li key={step.title} className="flex gap-4">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                      {index + 1}
                    </span>
                    <div>
                      <h3 className="text-base font-semibold text-slate-900">
                        {step.title}
                      </h3>
                      <p className="mt-1 text-sm leading-6 text-slate-600">
                        {step.detail}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>

            <Card className="h-fit p-6">
              <h2 className="text-base font-bold text-slate-900">
                Muốn nói chuyện với người thật?
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Trợ lý giúp bạn hiểu hồ sơ và hướng chuẩn bị. Nếu cần hỗ trợ thêm,
                bạn có thể liên hệ nhân viên để được trao đổi trực tiếp.
              </p>

              <div className="mt-6 space-y-3">
                <Button href={COMPANY.hotlineHref} className="w-full">
                  Gọi {COMPANY.hotline}
                </Button>
                <Button href="/don-hang" variant="outline" className="w-full">
                  Xem toàn bộ đơn đang tuyển
                </Button>
                <Button href="/dieu-kien" variant="outline" className="w-full">
                  Đọc điều kiện tham gia
                </Button>
              </div>

              <p className="mt-5 text-xs leading-5 text-slate-500">
                Hoặc mở khung chat ở góc phải màn hình để hỏi bất cứ điều gì, kể cả
                ngoài giờ hành chính.
              </p>
            </Card>
          </div>
        </Section>
      </section>

      <section className="bg-slate-50">
        <Section>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                title: "Chỉ loại khi chắc chắn",
                detail:
                  "Bạn chưa khai năm sinh thì hệ thống hỏi thêm, chứ không coi bạn là quá tuổi rồi loại đơn.",
              },
              {
                title: "Nói rõ lý do từng tiêu chí",
                detail:
                  "Mỗi đơn kèm bảng đạt hay chưa đạt cho từng điều kiện bắt buộc, không chỉ một con số phần trăm.",
              },
              {
                title: "Bạn là người chọn đơn",
                detail:
                  "Hệ thống gợi ý và giải thích. Chọn đơn nào để đăng ký là quyết định của bạn, và luôn có bước xác nhận.",
              },
            ].map((item) => (
              <Card key={item.title} className="p-6">
                <h3 className="text-sm font-semibold text-slate-900">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {item.detail}
                </p>
              </Card>
            ))}
          </div>
        </Section>
      </section>
    </>
  );
}
