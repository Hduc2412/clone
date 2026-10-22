import Link from "next/link";
import AnimatedBackground from "@/components/site/AnimatedBackground";
import HomeHero from "@/components/site/HomeHero";
import JobOrderCard from "@/components/site/JobOrderCard";
import {
  Accordion,
  Badge,
  Button,
  Card,
  Container,
  Section,
  SectionHeading,
  Stat,
} from "@/components/ui/primitives";
import { COMPANY, HERO_STATS, OFFICES, REFERENCE_NOTE, TRUST_ITEMS } from "@/content/site";
import { CONDITIONS, PROCESS, PROGRAMS } from "@/content/pages";
import { FEATURED_FAQ } from "@/content/faq";
import { fetchJobOrders } from "@/lib/publicApi";

export default async function HomePage() {
  const orders = await fetchJobOrders({ limit: 3 });

  return (
    <>
      {/* --- Mở đầu: theo bản thiết kế "Hành trình Nhật Bản" (08/10) --- */}
      <HomeHero />

      {/* --- Ba bước --- */}
      <Container className="border-b border-slate-200">
        <ol className="grid gap-6 py-8 md:grid-cols-3 md:gap-0">
          {[
            ["01", "Chia sẻ hồ sơ", "Gửi CV hoặc tự điền thông tin"],
            ["02", "Hiểu mức độ phù hợp", "Đối chiếu từng tiêu chí của đơn"],
            ["03", "Chọn bước tiếp theo", "Tư vấn, chuẩn bị hoặc gặp nhân viên"],
          ].map(([so, ten, mo_ta], i) => (
            <li key={so} className={`flex gap-5 md:px-8 ${i ? "md:border-l md:border-slate-200" : "md:pl-0"}`}>
              <span aria-hidden className="chu-nhan text-4xl text-[#9b7a52]">{so}</span>
              <span>
                <span className="block font-medium text-slate-900">{ten}</span>
                <span className="block text-sm text-slate-500">{mo_ta}</span>
              </span>
            </li>
          ))}
        </ol>
      </Container>

      {/* --- Số liệu tham khảo --- */}
      <Container className="py-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HERO_STATS.map((stat) => (
            <Stat key={stat.label} {...stat} />
          ))}
        </div>
        <p className="mt-4 max-w-3xl text-xs leading-5 text-slate-600">{REFERENCE_NOTE}</p>
      </Container>

      {/* --- Ba diện chương trình --- */}
      <Section>
        <SectionHeading
          eyebrow="Ba lối đi"
          title="Chọn diện chương trình phù hợp với mình"
          lead="Ba diện khác nhau về yêu cầu đầu vào, chi phí và thời gian. Không có diện nào tốt hơn hẳn, chỉ có diện hợp với hoàn cảnh của bạn hơn."
        />
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {PROGRAMS.map((program) => (
            <Card key={program.code} hover className="flex h-full flex-col p-6">
              <h3 className="text-lg font-bold text-slate-900">{program.name}</h3>
              <p className="mt-1 text-xs text-slate-500">{program.japanese}</p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                <Badge tone="info">{program.japaneseLevel}</Badge>
                <Badge tone="neutral">{program.duration}</Badge>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-600">
                {program.summary}
              </p>
              <ul className="mt-4 space-y-2 text-sm text-slate-600">
                {program.points.map((point) => (
                  <li key={point} className="flex gap-2.5">
                    <span aria-hidden className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                    {point}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </Section>

      {/* --- Điều kiện rút gọn --- */}
      <section className="dai-nen relative overflow-hidden">
        <div aria-hidden className="pattern-grid absolute inset-0 opacity-60" />
        <Container className="relative py-14 md:py-20">
          <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-center">
            <div>
              <SectionHeading
                eyebrow="Điều kiện tham gia"
                title="Kiểm tra nhanh xem bạn có đủ điều kiện"
                lead="Đây là điều kiện chung. Mỗi đơn hàng có yêu cầu riêng, và hệ thống sẽ đối chiếu hồ sơ của bạn với từng đơn để nói rõ đạt hay chưa đạt ở tiêu chí nào."
              />
              <div className="mt-7 flex flex-wrap gap-3">
                <Button href="/tu-van">Đối chiếu hồ sơ</Button>
                <Button href="/dieu-kien" variant="outline">
                  Xem đầy đủ điều kiện
                </Button>
              </div>
            </div>
            <Card className="divide-y divide-slate-100">
              {CONDITIONS.slice(0, 5).map((condition) => (
                <div key={condition.criterion} className="flex gap-4 px-5 py-4">
                  <span
                    aria-hidden
                    className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-[11px] font-bold text-emerald-700"
                  >
                    ✓
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {condition.criterion}
                      <span className="ml-2 font-normal text-slate-600">
                        {condition.requirement}
                      </span>
                    </p>
                    <p className="mt-0.5 text-xs leading-5 text-slate-500">
                      {condition.note}
                    </p>
                  </div>
                </div>
              ))}
            </Card>
          </div>
        </Container>
      </section>

      {/* --- Đơn hàng nổi bật --- */}
      <Section>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            eyebrow="Đang tuyển"
            title="Đơn hàng sắp hết hạn nộp"
            lead="Danh sách cập nhật theo danh mục nội bộ. Đơn hết hạn hoặc tạm dừng tự động không còn hiển thị."
          />
          <Button href="/don-hang" variant="outline">
            Xem tất cả đơn hàng
          </Button>
        </div>

        {orders.length === 0 ? (
          <Card className="mt-10 border-dashed px-6 py-14 text-center">
            <p className="font-medium text-slate-700">
              Hiện chưa có đơn hàng nào được công bố
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              Để lại số điện thoại hoặc gọi {COMPANY.hotline}, nhân viên sẽ báo
              ngay khi có đơn phù hợp với nguyện vọng của bạn.
            </p>
          </Card>
        ) : (
          <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {orders.map((order) => (
              <JobOrderCard key={order.code} order={order} />
            ))}
          </div>
        )}
      </Section>

      {/* --- Quy trình --- */}
      <section className="relative overflow-hidden bg-ink-900 text-slate-300">
        <AnimatedBackground variant="dark" petals={false} />
        <Container className="relative py-14 md:py-20">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-400">
              Quy trình
            </p>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-white md:text-3xl">
              Bảy bước từ lúc đăng ký đến lúc lên máy bay
            </h2>
            <p className="mt-3 text-base leading-7 text-slate-400">
              Thông thường mất từ tám đến mười bốn tháng, phần lớn thời gian dành
              cho học tiếng Nhật. Có chứng chỉ sẵn thì rút ngắn đáng kể.
            </p>
          </div>

          <ol className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {PROCESS.slice(0, 4).map((step, index) => (
              <li
                key={step.title}
                className="rounded-2xl border border-white/10 bg-white/5 p-5"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                  {index + 1}
                </span>
                <h3 className="mt-4 text-sm font-semibold text-white">
                  {step.title}
                </h3>
                <p className="mt-1 text-xs text-brand-300">{step.duration}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {step.detail}
                </p>
              </li>
            ))}
          </ol>

          <div className="mt-8">
            <Button href="/quy-trinh" variant="outline">
              Xem đủ bảy bước
            </Button>
          </div>
        </Container>
      </section>

      {/* --- Uy tín --- */}
      <Section>
        <SectionHeading
          eyebrow="Vì sao tin được"
          title="Giấy tờ pháp lý và cơ sở thật"
          lead="Trong ngành này nỗi lo lớn nhất là bị lừa. Dưới đây là những thứ bạn nên yêu cầu được xem tận mắt trước khi nộp bất kỳ khoản tiền nào, ở đây hay ở bất cứ công ty nào khác."
        />
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {TRUST_ITEMS.map((item) => (
            <Card key={item.title} className="flex gap-4 p-5">
              <span
                aria-hidden
                className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700"
              >
                ⛨
              </span>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  {item.title}
                </h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {item.detail}
                </p>
                {item.pending && (
                  <p className="mt-2 text-xs text-slate-400">
                    Ảnh giấy tờ do doanh nghiệp cung cấp, chưa đưa vào bản demo
                  </p>
                )}
              </div>
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

      {/* --- Hỏi đáp --- */}
      <section className="dai-nen">
        <Container className="py-14 md:py-20">
          <SectionHeading
            eyebrow="Hỏi đáp"
            title="Những câu được hỏi nhiều nhất"
            lead="Còn thắc mắc khác, bạn mở khung chat ở góc phải để hỏi bất cứ lúc nào, kể cả ngoài giờ hành chính."
          />
          <div className="mt-8">
            <Accordion
              items={FEATURED_FAQ.map((item) => ({
                question: item.question,
                answer: item.answer,
              }))}
            />
          </div>
          <div className="mt-6">
            <Link
              href="/cau-hoi-thuong-gap"
              className="text-sm font-semibold text-brand-600 hover:text-brand-700"
            >
              Xem tất cả câu hỏi →
            </Link>
          </div>
        </Container>
      </section>

      {/* --- Kêu gọi cuối trang --- */}
      <section className="relative overflow-hidden">
        <AnimatedBackground variant="soft" />
        <Container className="relative py-16 text-center md:py-20">
          <h2 className="mx-auto max-w-2xl text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
            Chưa chắc mình đủ điều kiện? Cứ thử đối chiếu
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-slate-600">
            Mất khoảng hai phút, không cần tài khoản. Hệ thống nói rõ bạn đạt và
            chưa đạt ở tiêu chí nào của từng đơn hàng.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button href="/tu-van" size="lg">
              Bắt đầu đối chiếu
            </Button>
            <Button href="/lien-he" variant="outline" size="lg">
              Đặt lịch gọi lại
            </Button>
          </div>
        </Container>
      </section>
    </>
  );
}
