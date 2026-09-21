import Link from "next/link";
import { COMPANY, NAV, OFFICES } from "@/content/site";
import { Container } from "@/components/ui/primitives";

export default function SiteFooter() {
  return (
    <footer className="relative mt-16 overflow-hidden bg-ink-900 text-slate-300">
      <div
        aria-hidden
        className="pattern-seigaiha absolute inset-x-0 top-0 h-20 text-white/10"
      />
      <Container className="relative py-12">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1.4fr]">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-sm font-bold text-white">
                DC
              </span>
              <span className="text-sm font-bold text-white">
                {COMPANY.shortName}
              </span>
            </div>
            <p className="mt-4 text-sm leading-6">{COMPANY.legalName}</p>
            <p className="mt-4 text-sm">
              Hotline{" "}
              <a
                href={COMPANY.hotlineHref}
                className="font-semibold text-white hover:text-brand-300"
              >
                {COMPANY.hotline}
              </a>
            </p>
            <p className="mt-1 text-sm">{COMPANY.email}</p>
            <p className="mt-4 text-xs leading-5 text-slate-400">
              Giờ làm việc: {COMPANY.workingHours}
            </p>
          </div>

          <nav>
            <h3 className="text-sm font-semibold text-white">Nội dung</h3>
            <ul className="mt-4 space-y-2.5 text-sm">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="hover:text-white">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <div>
            <h3 className="text-sm font-semibold text-white">Văn phòng</h3>
            <ul className="mt-4 space-y-4 text-sm leading-6">
              {OFFICES.map((office) => (
                <li key={office.city}>
                  <p className="font-medium text-white">
                    {office.city}
                    <span className="ml-2 text-xs font-normal text-slate-400">
                      {office.label}
                    </span>
                  </p>
                  <p className="text-slate-400">{office.address}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-10 border-t border-white/10 pt-6 text-xs leading-5 text-slate-400">
          <p>
            Website thuộc đồ án tốt nghiệp: hệ thống AI hỗ trợ tư vấn và quản trị
            tuyển dụng điều dưỡng Nhật Bản. Thông tin về chi phí, lương và thời
            gian trên trang mang tính tham khảo và được nhân viên tư vấn xác nhận
            lại theo từng trường hợp.
          </p>
          {/* Hai trong ba ảnh nền dùng giấy phép bắt buộc ghi công. Dùng mà
              không ghi là vi phạm, nên dòng này không được bỏ. Chi tiết đầy đủ
              ở `public/nen/NGUON.md`. */}
          <p className="mt-3">
            Ảnh nền núi Phú Sĩ:{" "}
            <a
              href="https://commons.wikimedia.org/wiki/File:Mount_Fuji_April_Cherry_Blossom.jpg"
              className="underline decoration-slate-600 underline-offset-2 hover:text-slate-200"
              rel="noopener noreferrer"
              target="_blank"
            >
              SRP1998
            </a>{" "}
            (CC BY-SA 4.0),{" "}
            <a
              href="https://commons.wikimedia.org/wiki/File:Lake_Kawaguchiko_Sakura_Mount_Fuji_4.JPG"
              className="underline decoration-slate-600 underline-offset-2 hover:text-slate-200"
              rel="noopener noreferrer"
              target="_blank"
            >
              Midori
            </a>{" "}
            (CC BY 3.0), Romain Guy (CC0) — qua Wikimedia Commons.
          </p>
          <p className="mt-3">
            © {new Date().getFullYear()} {COMPANY.legalName}
          </p>
        </div>
      </Container>
    </footer>
  );
}
