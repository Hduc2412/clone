"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { COMPANY, NAV } from "@/content/site";

export default function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Đóng menu khi chuyển trang, nếu không thì bấm một mục xong menu vẫn che
  // nguyên trang mới.
  useEffect(() => setOpen(false), [pathname]);

  return (
    <header
      className={`sticky top-0 z-40 border-b transition-colors ${
        scrolled
          ? "border-slate-200 bg-white/90 backdrop-blur"
          : "border-transparent bg-white/70 backdrop-blur"
      }`}
    >
      <div className="mx-auto flex h-[72px] w-full max-w-container items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-sm font-bold text-white">
            DC
          </span>
          <span className="leading-tight">
            <span className="block whitespace-nowrap text-sm font-bold text-slate-900">
              {COMPANY.shortName}
            </span>
            <span className="block whitespace-nowrap text-[11px] text-slate-500">
              {COMPANY.tagline}
            </span>
          </span>
        </Link>

        <nav className="ml-auto hidden items-center gap-1 xl:flex">
          {NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-lg px-2.5 py-2 text-sm transition-colors ${
                  active
                    ? "font-semibold text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <a
          href={COMPANY.hotlineHref}
          className="ml-auto hidden rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lift transition-colors hover:bg-brand-700 xl:ml-0 xl:inline-flex"
        >
          {COMPANY.hotline}
        </a>

        <button
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-label={open ? "Đóng menu" : "Mở menu"}
          className="ml-auto flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 text-slate-700 xl:hidden"
        >
          <span className="text-lg">{open ? "✕" : "☰"}</span>
        </button>
      </div>

      {open && (
        <div className="border-t border-slate-200 bg-white xl:hidden">
          <nav className="mx-auto grid w-full max-w-container gap-1 px-4 py-3 sm:px-6">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-3 py-3 text-sm ${
                  pathname.startsWith(item.href)
                    ? "bg-brand-50 font-semibold text-brand-700"
                    : "text-slate-700"
                }`}
              >
                {item.label}
              </Link>
            ))}
            <a
              href={COMPANY.hotlineHref}
              className="mt-2 rounded-xl bg-brand-600 px-4 py-3 text-center text-sm font-semibold text-white"
            >
              Gọi {COMPANY.hotline}
            </a>
          </nav>
        </div>
      )}
    </header>
  );
}
