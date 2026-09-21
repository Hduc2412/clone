import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import { Button, Card, Section, SectionHeading, Steps } from "@/components/ui/primitives";
import { PROCESS } from "@/content/pages";

export const metadata: Metadata = {
  title: "Quy trình",
  description:
    "Bảy bước từ lúc đăng ký đến khi xuất cảnh sang Nhật Bản làm điều dưỡng, hộ lý, kèm thời lượng từng bước.",
};

export default function ProcessPage() {
  return (
    <>
      <PageHero
        eyebrow="Quy trình"
        title="Bảy bước từ lúc đăng ký đến khi lên máy bay"
        lead="Thông thường mất từ tám đến mười bốn tháng. Phần lớn thời gian dành cho học tiếng Nhật, nên ai đã có chứng chỉ thì rút ngắn được đáng kể."
      >
        <Button href="/tu-van">Bắt đầu từ bước một</Button>
      </PageHero>

      <Section>
        <div className="grid gap-10 lg:grid-cols-[1.3fr_1fr]">
          <Steps items={PROCESS.map((step) => ({ ...step }))} />

          <div className="space-y-5">
            <Card className="p-6">
              <h3 className="text-sm font-semibold text-slate-900">
                Bước nào lâu nhất
              </h3>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Học tiếng Nhật, chiếm bốn tới tám tháng trong tổng thời gian. Đây
                cũng là bước quyết định nhiều nhất tới việc bạn có đỗ phỏng vấn hay
                không, và tới mức độ thoải mái trong vài tháng đầu làm việc.
              </p>
            </Card>

            <Card className="p-6">
              <h3 className="text-sm font-semibold text-slate-900">
                Bước nào có thể trượt
              </h3>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Khám sức khỏe và phỏng vấn. Khám sức khỏe nên làm sớm, trước khi
                đầu tư thời gian học tiếng, vì có mười ba nhóm bệnh không đủ điều
                kiện xuất cảnh. Trượt phỏng vấn thì được giới thiệu sang đơn khác
                mà không phải bắt đầu lại từ đầu.
              </p>
            </Card>

            <Card className="p-6">
              <h3 className="text-sm font-semibold text-slate-900">
                Bước nào cần chuẩn bị tiền
              </h3>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Chi phí rải theo giai đoạn chứ không dồn vào một lúc. Khoản lớn
                nhất là phí dịch vụ và chỉ thu sau khi trúng tuyển đơn hàng.
              </p>
              <div className="mt-4">
                <Button href="/chi-phi" variant="outline" size="sm">
                  Xem bảng chi phí
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </Section>

      <section className="bg-slate-50">
        <Section>
          <SectionHeading
            eyebrow="Sau khi sang Nhật"
            title="Công ty vẫn theo dõi trong suốt hợp đồng"
            lead="Có người đón tại sân bay, hỗ trợ ổn định chỗ ở và làm thủ tục cư trú ban đầu. Trong thời gian làm việc, nếu phát sinh vướng mắc với cơ sở tiếp nhận thì liên hệ về công ty để được hỗ trợ."
          />
        </Section>
      </section>
    </>
  );
}
