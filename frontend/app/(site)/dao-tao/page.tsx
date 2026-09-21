import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import { Button, Card, Section, SectionHeading } from "@/components/ui/primitives";
import { TRAINING } from "@/content/pages";

export const metadata: Metadata = {
  title: "Đào tạo và ký túc xá",
  description:
    "Lớp học tiếng Nhật, ký túc xá và sinh hoạt của học viên trong thời gian đào tạo trước khi xuất cảnh.",
};

export default function TrainingPage() {
  return (
    <>
      <PageHero
        eyebrow="Đào tạo"
        title="Học tiếng Nhật và ở nội trú trước khi bay"
        lead={TRAINING.intro}
      >
        <Button href="/lien-he">Đăng ký tìm hiểu lớp học</Button>
      </PageHero>

      <Section>
        <div className="grid gap-5 lg:grid-cols-2">
          <Card className="p-6">
            <h2 className="text-lg font-bold text-slate-900">Lớp học</h2>
            <ul className="mt-5 space-y-3 text-sm leading-6 text-slate-600">
              {TRAINING.classroom.map((item) => (
                <li key={item} className="flex gap-3">
                  <span
                    aria-hidden
                    className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-bold text-slate-900">Ký túc xá</h2>
            <ul className="mt-5 space-y-3 text-sm leading-6 text-slate-600">
              {TRAINING.dormitory.map((item) => (
                <li key={item} className="flex gap-3">
                  <span
                    aria-hidden
                    className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </Section>

      <section className="bg-slate-50">
        <Section>
          <SectionHeading
            eyebrow="Vì sao ở nội trú"
            title="Kỷ luật giờ giấc là thứ nhà tuyển dụng Nhật nhìn vào"
            lead="Cơ sở chăm sóc vận hành theo ca và theo giờ rất chặt, vì liên quan tới bữa ăn, thuốc và giấc ngủ của người cao tuổi. Thời gian ở ký túc xá là lúc làm quen với nếp đó, trước khi sang tới nơi mới phải học."
          />
          <div className="mt-8">
            <Button href="/quy-trinh" variant="outline">
              Xem đào tạo nằm ở bước nào
            </Button>
          </div>
        </Section>
      </section>
    </>
  );
}
