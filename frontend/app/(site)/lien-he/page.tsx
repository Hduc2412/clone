import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import { Button, Card, Section } from "@/components/ui/primitives";
import { COMPANY, OFFICES } from "@/content/site";

export const metadata: Metadata = {
  title: "Liên hệ",
  description:
    "Ba văn phòng tại Hà Nội, TP. Hồ Chí Minh và Bến Tre. Hotline 0971.716.939, tiếp nhận hồ sơ và tư vấn chương trình điều dưỡng Nhật Bản.",
};

export default function ContactPage() {
  return (
    <>
      <PageHero
        eyebrow="Liên hệ"
        title="Gọi, nhắn tin, hoặc tới trực tiếp văn phòng"
        lead={`Giờ làm việc ${COMPANY.workingHours}. Ngoài giờ bạn vẫn nhắn được cho khung chat ở góc phải, nhân viên sẽ gọi lại vào buổi làm việc kế tiếp.`}
      >
        <div className="flex flex-wrap gap-3">
          <Button href={COMPANY.hotlineHref} size="lg">
            Gọi {COMPANY.hotline}
          </Button>
          <Button
            href={`https://zalo.me/${COMPANY.zalo}`}
            variant="outline"
            size="lg"
          >
            Nhắn Zalo
          </Button>
        </div>
      </PageHero>

      <Section>
        <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
          <div className="space-y-5">
            {OFFICES.map((office) => (
              <Card key={office.city} className="p-6">
                <div className="flex items-baseline justify-between gap-3">
                  <h2 className="text-base font-bold text-slate-900">
                    {office.city}
                  </h2>
                  <span className="text-xs text-brand-600">{office.label}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {office.address}
                </p>
                <a
                  href={`https://www.google.com/maps/search/${encodeURIComponent(
                    `${office.address}, ${office.city}`,
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-block text-sm font-semibold text-brand-600 hover:text-brand-700"
                >
                  Xem trên bản đồ →
                </a>
              </Card>
            ))}
          </div>

          <Card className="h-fit p-6">
            <h2 className="text-lg font-bold text-slate-900">
              Để lại số, nhân viên gọi lại
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Bạn chọn khung giờ tiện nhất. Nhân viên đọc trước hồ sơ và nguyện
              vọng của bạn rồi mới gọi, nên không phải kể lại từ đầu.
            </p>

            {/* Biểu mẫu nối vào API đăng ký ở giai đoạn sau. Hiện dẫn sang luồng
                tư vấn để không có nút bấm vào rồi không xảy ra chuyện gì. */}
            <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5">
              <p className="text-sm leading-6 text-slate-600">
                Biểu mẫu đặt lịch đang được hoàn thiện cùng phần đối chiếu hồ sơ.
                Trong lúc chờ, bạn gọi hotline hoặc nhắn vào khung chat ở góc phải,
                cả hai đều tới cùng một nhân viên phụ trách.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button href="/tu-van" size="sm">
                  Đối chiếu hồ sơ trước
                </Button>
                <Button href={COMPANY.hotlineHref} variant="outline" size="sm">
                  Gọi ngay
                </Button>
              </div>
            </div>

            <dl className="mt-6 space-y-3 border-t border-slate-100 pt-5 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Hotline</dt>
                <dd className="font-semibold text-slate-900">{COMPANY.hotline}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Thư điện tử</dt>
                <dd className="text-slate-900">{COMPANY.email}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Giờ làm việc</dt>
                <dd className="text-right text-slate-900">
                  {COMPANY.workingHours}
                </dd>
              </div>
            </dl>
          </Card>
        </div>
      </Section>
    </>
  );
}
