import PhotoBackdrop from "@/components/site/PhotoBackdrop";
import { Container } from "@/components/ui/primitives";

/** Đầu trang dùng chung cho các trang nội dung, để chúng trông cùng một bộ. */
export default function PageHero({
  eyebrow,
  title,
  lead,
  children,
}: {
  eyebrow: string;
  title: string;
  lead?: string;
  children?: React.ReactNode;
}) {
  return (
    <section className="relative overflow-hidden border-b border-slate-100">
      <PhotoBackdrop variant="soft" />
      <Container className="relative py-12 md:py-16">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">
          {eyebrow}
        </p>
        <h1 className="mt-3 max-w-3xl text-3xl font-bold leading-tight tracking-tight text-slate-900 md:text-4xl">
          {title}
        </h1>
        {lead && (
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
            {lead}
          </p>
        )}
        {children && <div className="mt-7">{children}</div>}
      </Container>
    </section>
  );
}
