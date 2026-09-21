import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import {
  Badge,
  Button,
  Card,
  Section,
  SectionHeading,
} from "@/components/ui/primitives";
import { COMPANY, OFFICES, TRUST_ITEMS } from "@/content/site";
import { PROGRAMS } from "@/content/pages";

export const metadata: Metadata = {
  title: "Giới thiệu",
  description:
    "Về Công ty Đầu tư Phát triển Nhân lực Quốc tế DC và ba diện chương trình điều dưỡng, hộ lý tại Nhật Bản.",
};

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="Giới thiệu"
        title="Đưa điều dưỡng và hộ lý Việt Nam sang làm việc tại Nhật Bản"
        lead="Nhật Bản đang già hóa nhanh và thiếu người chăm sóc. Đó là lý do ngành này tuyển liên tục, và cũng là lý do điều kiện tham gia dễ thở hơn nhiều ngành khác."
      >
        <div className="flex flex-wrap gap-3">
          <Button href="/don-hang">Xem đơn hàng đang tuyển</Button>
          <Button href="/lien-he" variant="outline">
            Liên hệ tư vấn
          </Button>
        </div>
      </PageHero>

      <Section>
        <div className="grid gap-10 lg:grid-cols-[1.2fr_1fr]">
          <div className="space-y-4 text-base leading-7 text-slate-600">
            <SectionHeading eyebrow="Về công ty" title={COMPANY.legalName} />
            <p className="pt-2">
              Công ty hoạt động trong lĩnh vực đưa người lao động Việt Nam đi làm
              việc ở nước ngoài, tập trung vào ngành chăm sóc và điều dưỡng tại
              Nhật Bản. Học viên được đào tạo tiếng Nhật tập trung tại trung tâm
              của công ty trước khi xuất cảnh.
            </p>
            <p>
              Ba văn phòng đặt tại Hà Nội, Thành phố Hồ Chí Minh và Bến Tre, tiếp
              nhận hồ sơ và tổ chức phỏng vấn trực tiếp với cơ sở tiếp nhận phía
              Nhật Bản.
            </p>
            <p>
              Website này là một phần của hệ thống tư vấn tự động: ứng viên có thể
              tự đối chiếu hồ sơ của mình với danh mục đơn hàng và biết ngay mình
              đạt hay chưa đạt ở tiêu chí nào, thay vì phải chờ gọi điện.
            </p>
          </div>

          <Card className="h-fit p-6">
            <h3 className="text-sm font-semibold text-slate-900">Liên hệ nhanh</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-xs text-slate-500">Hotline</dt>
                <dd className="mt-0.5">
                  <a
                    href={COMPANY.hotlineHref}
                    className="text-base font-semibold text-brand-700 hover:underline"
                  >
                    {COMPANY.hotline}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Thư điện tử</dt>
                <dd className="mt-0.5 text-slate-700">{COMPANY.email}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Giờ làm việc</dt>
                <dd className="mt-0.5 leading-6 text-slate-700">
                  {COMPANY.workingHours}
                </dd>
              </div>
            </dl>
          </Card>
        </div>
      </Section>

      <section className="bg-slate-50">
        <Section>
          <SectionHeading
            eyebrow="Chương trình"
            title="Ba diện đưa người sang Nhật ngành chăm sóc"
            lead="Khác nhau ở yêu cầu tiếng Nhật, chi phí, thời gian hợp đồng và khả năng ở lại lâu dài."
          />
          <div className="mt-10 space-y-5">
            {PROGRAMS.map((program) => (
              <Card key={program.code} className="p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">
                      {program.name}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500">{program.japanese}</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge tone="info">{program.japaneseLevel}</Badge>
                    <Badge tone="neutral">{program.duration}</Badge>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-600">
                  {program.summary}
                </p>
                <ul className="mt-4 grid gap-2 text-sm text-slate-600 md:grid-cols-3">
                  {program.points.map((point) => (
                    <li key={point} className="flex gap-2.5">
                      <span
                        aria-hidden
                        className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500"
                      />
                      {point}
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        </Section>
      </section>

      <Section>
        <SectionHeading
          eyebrow="Cơ sở và pháp lý"
          title="Những gì bạn nên yêu cầu được xem tận mắt"
          lead="Áp dụng cho mọi công ty phái cử, không riêng ở đây. Đừng nộp tiền trước khi nhìn thấy giấy phép còn hiệu lực và hợp đồng ghi rõ từng khoản."
        />
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {TRUST_ITEMS.map((item) => (
            <Card key={item.title} className="p-5">
              <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-1.5 text-sm leading-6 text-slate-600">
                {item.detail}
              </p>
              {item.pending && (
                <p className="mt-2 text-xs text-slate-400">
                  Ảnh giấy tờ do doanh nghiệp cung cấp, chưa đưa vào bản demo
                </p>
              )}
            </Card>
          ))}
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {OFFICES.map((office) => (
            <Card key={office.city} className="p-5">
              <p className="text-sm font-semibold text-slate-900">{office.city}</p>
              <p className="mt-0.5 text-xs text-brand-600">{office.label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {office.address}
              </p>
            </Card>
          ))}
        </div>
      </Section>
    </>
  );
}
