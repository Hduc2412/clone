import type { Metadata } from "next";
import PageHero from "@/components/site/PageHero";
import { Accordion, Button, Card, Section } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { FAQ, FAQ_TOPIC_LABELS, type FaqTopic } from "@/content/faq";

export const metadata: Metadata = {
  title: "Câu hỏi thường gặp",
  description:
    "Giải đáp về điều kiện, chi phí, lương, công việc, thời gian và học tiếng Nhật của chương trình điều dưỡng Nhật Bản.",
};

export default function FaqPage() {
  const topics = Object.keys(FAQ_TOPIC_LABELS) as FaqTopic[];
  const grouped = topics
    .map((topic) => ({
      topic,
      label: FAQ_TOPIC_LABELS[topic],
      items: FAQ.filter((item) => item.topic === topic),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <>
      <PageHero
        eyebrow="Hỏi đáp"
        title="Câu hỏi thường gặp"
        lead="Những câu ứng viên hỏi nhiều nhất, nhóm theo chủ đề. Câu nào chưa có ở đây thì mở khung chat ở góc phải, hệ thống trả lời bất cứ lúc nào, kể cả ngoài giờ hành chính."
      />

      <Section>
        <div className="grid gap-8 lg:grid-cols-[220px_1fr] lg:items-start">
          <nav className="lg:sticky lg:top-24">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              Chủ đề
            </p>
            <ul className="mt-4 space-y-1">
              {grouped.map((group) => (
                <li key={group.topic}>
                  <a
                    href={`#${group.topic}`}
                    className="block rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  >
                    {group.label}
                    <span className="ml-1.5 text-xs text-slate-400">
                      {group.items.length}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <div className="space-y-10">
            {grouped.map((group) => (
              <section key={group.topic} id={group.topic}>
                <h2 className="mb-4 text-lg font-bold text-slate-900">
                  {group.label}
                </h2>
                <Accordion
                  items={group.items.map((item) => ({
                    question: item.question,
                    answer: item.answer,
                  }))}
                />
              </section>
            ))}

            <Card className="bg-slate-50 p-6">
              <h2 className="text-base font-bold text-slate-900">
                Không thấy câu trả lời mình cần?
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Hệ thống chỉ trả lời dựa trên tài liệu chính thức của công ty. Khi
                không đủ căn cứ, nó nói thẳng là chưa có thông tin và mời bạn gặp
                nhân viên, thay vì đoán bừa.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Button href="/lien-he">Đặt lịch gọi lại</Button>
                <Button href={COMPANY.hotlineHref} variant="outline">
                  Gọi {COMPANY.hotline}
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </Section>
    </>
  );
}
