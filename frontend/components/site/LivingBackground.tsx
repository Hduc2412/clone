"use client";

/**
 * Nền sống động phủ toàn website (22/10/2026).
 *
 * Trước đây chỉ phần đầu trang có ảnh và chuyển động; thân trang là một nền kem
 * phẳng, nên đi xuống dưới là thấy trang "tắt" hẳn. Lớp này nằm cố định sau mọi
 * nội dung và gồm ba thứ, đều vẽ bằng CSS nên không tải thêm ảnh nào:
 *
 * 1. Vầng màu — bốn khối màu lớn làm mờ (đỏ trầm, vàng nắng, xanh rêu, hồng đào)
 *    trôi chậm như ánh sáng qua cửa sổ. Chu kỳ 34–52 giây.
 * 2. Hoa anh đào — mười cánh rơi thưa theo đường lượn, độ đậm thấp để không
 *    tranh chỗ với chữ.
 * 3. Thanh tiến trình cuộn — một vạch màu mảnh trên đầu trang cho biết đã đọc
 *    tới đâu, thứ hữu ích nhất trên các trang dài như Điều kiện hay Hỏi đáp.
 *
 * Kèm hai việc nhỏ chạy theo trang: các khối nội dung hiện dần khi cuộn tới (chỉ
 * những khối đang nằm dưới tầm nhìn, nên không có gì "nhấp nháy" lúc mở trang), và
 * nút tạm dừng nền nhớ lựa chọn của khách trong trình duyệt.
 *
 * Người bật "giảm chuyển động" trong hệ điều hành: không có cánh hoa, vầng màu
 * đứng yên, không hiện dần — xem `globals.css` và nhánh `giamChuyenDong` dưới đây.
 */
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const KHOA_DUNG = "xkld-nen-dung";

/** Rải lệch vị trí, độ trễ, tốc độ để không thấy nhịp lặp. */
const CANH_HOA = [
  { left: "4%", delay: "-3s", duration: "26s", size: 12, opacity: 0.52 },
  { left: "13%", delay: "-17s", duration: "33s", size: 9, opacity: 0.3 },
  { left: "24%", delay: "-9s", duration: "29s", size: 14, opacity: 0.48 },
  { left: "37%", delay: "-24s", duration: "36s", size: 10, opacity: 0.40 },
  { left: "49%", delay: "-5s", duration: "31s", size: 12, opacity: 0.3 },
  { left: "61%", delay: "-20s", duration: "27s", size: 9, opacity: 0.48 },
  { left: "72%", delay: "-12s", duration: "34s", size: 13, opacity: 0.42 },
  { left: "83%", delay: "-28s", duration: "30s", size: 10, opacity: 0.46 },
  { left: "91%", delay: "-7s", duration: "38s", size: 15, opacity: 0.38 },
  { left: "97%", delay: "-15s", duration: "28s", size: 8, opacity: 0.3 },
];

export default function LivingBackground() {
  const pathname = usePathname();
  const [dung, setDung] = useState(false);
  const [tienTrinh, setTienTrinh] = useState(0);

  // Nhớ lựa chọn tạm dừng giữa các lần mở trang.
  useEffect(() => {
    try {
      setDung(window.localStorage.getItem(KHOA_DUNG) === "1");
    } catch {
      /* chế độ riêng tư chặn localStorage: coi như chưa dừng */
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("nen-dung", dung);
    try {
      window.localStorage.setItem(KHOA_DUNG, dung ? "1" : "0");
    } catch {
      /* không lưu được thì chỉ áp dụng cho lần xem này */
    }
  }, [dung]);

  // Thanh tiến trình cuộn. Gộp theo khung hình để không chạy lại hàng trăm lần mỗi giây.
  useEffect(() => {
    let khung = 0;
    const tinh = () => {
      khung = 0;
      const cao = document.documentElement.scrollHeight - window.innerHeight;
      setTienTrinh(cao > 0 ? Math.min(1, window.scrollY / cao) : 0);
    };
    const khiCuon = () => {
      if (!khung) khung = window.requestAnimationFrame(tinh);
    };
    tinh();
    window.addEventListener("scroll", khiCuon, { passive: true });
    window.addEventListener("resize", khiCuon);
    return () => {
      window.removeEventListener("scroll", khiCuon);
      window.removeEventListener("resize", khiCuon);
      if (khung) window.cancelAnimationFrame(khung);
    };
  }, [pathname]);

  // Hiện dần các khối nội dung khi cuộn tới. Chỉ ẩn trước những khối đang nằm dưới
  // tầm nhìn: khối đã thấy ngay lúc mở trang giữ nguyên, không bị nháy mất rồi hiện lại.
  useEffect(() => {
    const giamChuyenDong = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (giamChuyenDong || !("IntersectionObserver" in window)) return;
    let cleanup = () => {};
    const hen = window.setTimeout(() => {
      const khoi = Array.from(
        document.querySelectorAll<HTMLElement>("main section > div > *, main .shadow-card"),
      ).filter((el) => !el.closest("[data-khong-hien-dan]") && el.getBoundingClientRect().top > window.innerHeight);
      const quanSat = new IntersectionObserver(
        (muc) => {
          for (const m of muc) {
            if (m.isIntersecting) {
              m.target.classList.add("da-hien");
              quanSat.unobserve(m.target);
            }
          }
        },
        { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
      );
      for (const el of khoi) {
        el.classList.add("hien-dan");
        quanSat.observe(el);
      }
      cleanup = () => {
        quanSat.disconnect();
        for (const el of khoi) el.classList.remove("hien-dan", "da-hien");
      };
    }, 120);
    return () => {
      window.clearTimeout(hen);
      cleanup();
    };
  }, [pathname]);

  return (
    <>
      <div
        aria-hidden
        className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-[3px] origin-left bg-gradient-to-r from-brand-600 via-[#d9a441] to-reu-600"
        style={{ transform: `scaleX(${tienTrinh})` }}
      />

      <div aria-hidden className="nen-song pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="vang-mau absolute -left-40 -top-40 h-[42rem] w-[42rem] rounded-full bg-[#e8a89a]/60" />
        <div
          className="vang-mau absolute -right-48 top-[18%] h-[38rem] w-[38rem] rounded-full bg-[#f2cf86]/55"
          style={{ animationDuration: "46s", animationDelay: "-14s" }}
        />
        <div
          className="vang-mau absolute bottom-[-12rem] left-[22%] h-[40rem] w-[40rem] rounded-full bg-[#a9cdb9]/55"
          style={{ animationDuration: "52s", animationDelay: "-26s" }}
        />
        <div
          className="vang-mau absolute right-[12%] top-[62%] h-[26rem] w-[26rem] rounded-full bg-[#f0aebb]/50"
          style={{ animationDuration: "40s", animationDelay: "-8s" }}
        />
        {/* Lưới chấm rất nhạt cho mặt nền có chất liệu giấy, thay vì một mảng màu trơn. */}
        <div className="nen-cham absolute inset-0" />

        <div className="canh-hoa-nen absolute inset-0">
          {CANH_HOA.map((c) => (
            <span
              key={c.left}
              className="canh-hoa absolute top-0"
              style={{ left: c.left, animationDelay: c.delay, animationDuration: c.duration, opacity: c.opacity }}
            >
              <svg width={c.size} height={c.size} viewBox="0 0 16 16" fill="none">
                <path
                  d="M8 15c-3 0-5-2.6-5-5.6C3 6.4 5 3.4 8 1c3 2.4 5 5.4 5 8.4 0 3-2 5.6-5 5.6Z
                     M8 15c.7-1.2 1.1-2 1.1-2.9 0-.8-.4-1.5-1.1-2-.7.5-1.1 1.2-1.1 2 0 .9.4 1.7 1.1 2.9Z"
                  fill="#e98a91"
                  fillRule="evenodd"
                />
              </svg>
            </span>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={() => setDung((d) => !d)}
        aria-pressed={dung}
        className="nut-dung-nen fixed bottom-4 left-4 z-40 rounded-full border border-slate-200 bg-white/85 px-3.5 py-2 text-xs font-medium text-slate-600 shadow-card backdrop-blur transition hover:bg-white hover:text-slate-900"
      >
        {dung ? "▶ Bật nền động" : "II Tạm dừng nền"}
      </button>
    </>
  );
}
