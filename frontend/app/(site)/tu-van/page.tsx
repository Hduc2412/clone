import type { Metadata } from "next";
import ConsultationFlow from "@/components/candidate/ConsultationFlow";
import PageHero from "@/components/site/PageHero";
import { Button, Card, Section, SectionHeading } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { fetchJobOrder } from "@/lib/publicApi";

export const metadata: Metadata = {
  title: "Đối chiếu hồ sơ",
  description:
    "Nhập hồ sơ của bạn và xem mình đạt hay chưa đạt ở tiêu chí nào của từng đơn hàng điều dưỡng Nhật Bản.",
};

const STEPS = [
  {
    title: "Nhập năng lực",
    detail:
      "Năm sinh, bằng cấp, trình độ tiếng Nhật, kinh nghiệm chăm sóc. Mục nào chưa rõ thì bỏ trống, hệ thống sẽ hỏi lại chứ không loại đơn.",
  },
  {
    title: "Nêu nguyện vọng",
    detail:
      "Khu vực mong muốn, loại hình cơ sở, mức lương kỳ vọng. Nguyện vọng chỉ dùng để xếp thứ tự, không bao giờ khiến đơn nào bị loại.",
  },
  {
    title: "Xem kết quả đối chiếu",
    detail:
      "Mỗi đơn hiện rõ từng tiêu chí đạt, chưa đạt hay chưa rõ, kèm điểm phù hợp với nguyện vọng của bạn.",
  },
  {
    title: "Chọn đơn và đặt lịch",
    detail:
      "Bạn tự chọn đơn muốn đăng ký. Hệ thống gửi hồ sơ kèm lịch hẹn cho nhân viên, họ gọi lại đúng khung giờ bạn chọn.",
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
        eyebrow="Đối chiếu hồ sơ"
        title="Biết mình hợp đơn nào, và vì sao"
        lead="Không cần tài khoản, không cần gọi điện. Hệ thống đối chiếu hồ sơ của bạn với từng đơn đang tuyển rồi nói rõ lý do cho từng tiêu chí."
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
                title="Mất khoảng hai phút"
                lead="Bạn dừng ở bước nào cũng được, thông tin đã nhập vẫn giữ nguyên trên máy của bạn."
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
                Biểu mẫu trên trả lời được câu “tôi hợp đơn nào”. Còn những câu
                riêng của hoàn cảnh bạn thì gọi vẫn nhanh hơn.
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
