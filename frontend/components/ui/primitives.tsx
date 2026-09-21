import Link from "next/link";
import { ReactNode } from "react";

/**
 * Bộ thành phần nền của website khách hàng.
 *
 * Gom vào một file vì chúng nhỏ và luôn được dùng cùng nhau; tách thành mười
 * file mỗi file hai chục dòng chỉ làm việc đọc mã nguồn mất thời gian hơn.
 * Khi một thành phần lớn lên tới mức có trạng thái riêng thì tách ra file riêng.
 */

export function Container({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`mx-auto w-full max-w-container px-4 sm:px-6 ${className}`}>
      {children}
    </div>
  );
}

export function Section({
  children,
  className = "",
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} className={`py-14 md:py-20 ${className}`}>
      <Container>{children}</Container>
    </section>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  lead,
  align = "left",
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
  align?: "left" | "center";
}) {
  const alignment = align === "center" ? "text-center mx-auto" : "";
  return (
    <div className={`max-w-2xl ${alignment}`}>
      {eyebrow && (
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">
          {eyebrow}
        </p>
      )}
      <h2 className="mt-3 text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
        {title}
      </h2>
      {lead && <p className="mt-3 text-base leading-7 text-slate-600">{lead}</p>}
    </div>
  );
}

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-600 text-white shadow-lift hover:bg-brand-700 active:bg-brand-800",
  secondary: "bg-ink-900 text-white hover:bg-ink-800",
  outline:
    "border border-slate-300 bg-white text-slate-700 hover:border-brand-300 hover:text-brand-700",
  ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "px-3.5 py-2 text-sm",
  md: "px-5 py-2.5 text-sm",
  lg: "px-6 py-3.5 text-base",
};

export function Button({
  children,
  href,
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  disabled,
  onClick,
}: {
  children: ReactNode;
  href?: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
}) {
  // Chiều cao tối thiểu 44px: kích thước đầu ngón tay. Phần lớn ứng viên vào
  // bằng điện thoại nên nút nhỏ hơn mức này là bấm trượt.
  const base =
    "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl font-medium transition-colors disabled:opacity-50";
  const classes = `${base} ${VARIANTS[variant]} ${SIZES[size]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }
  return (
    <button type={type} disabled={disabled} onClick={onClick} className={classes}>
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white shadow-card ${
        hover ? "transition-shadow hover:shadow-lift" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

type BadgeTone = "brand" | "neutral" | "success" | "warning" | "info";

const TONES: Record<BadgeTone, string> = {
  brand: "bg-brand-50 text-brand-700 ring-brand-200",
  neutral: "bg-slate-100 text-slate-600 ring-slate-200",
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  warning: "bg-amber-50 text-amber-700 ring-amber-200",
  info: "bg-sky-50 text-sky-700 ring-sky-200",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: BadgeTone;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function Stat({
  value,
  label,
  note,
}: {
  value: string;
  label: string;
  note?: string;
}) {
  return (
    <Card className="p-5">
      <p className="text-3xl font-bold tracking-tight text-brand-600">{value}</p>
      <p className="mt-2 text-sm font-medium text-slate-800">{label}</p>
      {note && <p className="mt-1 text-xs leading-5 text-slate-500">{note}</p>}
    </Card>
  );
}

export function Steps({
  items,
}: {
  items: { title: string; detail: string; duration?: string }[];
}) {
  return (
    <ol className="relative space-y-6 border-l-2 border-brand-100 pl-8">
      {items.map((item, index) => (
        <li key={item.title} className="relative">
          <span className="absolute -left-[41px] flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
            {index + 1}
          </span>
          <div className="flex flex-wrap items-baseline gap-x-3">
            <h3 className="text-base font-semibold text-slate-900">{item.title}</h3>
            {item.duration && (
              <span className="text-xs text-slate-500">{item.duration}</span>
            )}
          </div>
          <p className="mt-1.5 text-sm leading-6 text-slate-600">{item.detail}</p>
        </li>
      ))}
    </ol>
  );
}

export function Accordion({
  items,
}: {
  items: { question: string; answer: string }[];
}) {
  return (
    <div className="divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      {items.map((item) => (
        // Thẻ <details> của trình duyệt: mở đóng được bằng bàn phím và đọc được
        // bằng trình đọc màn hình mà không cần một dòng JavaScript nào.
        <details key={item.question} className="group">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-sm font-medium text-slate-800 hover:bg-slate-50">
            {item.question}
            <span className="shrink-0 text-brand-600 transition-transform group-open:rotate-45">
              +
            </span>
          </summary>
          <p className="px-5 pb-5 text-sm leading-6 text-slate-600">{item.answer}</p>
        </details>
      ))}
    </div>
  );
}

export function Prose({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-4 text-base leading-7 text-slate-600">{children}</div>
  );
}
