import type { Metadata } from "next";
import "./phong-chu.css";
import "./globals.css";

/**
 * Phông: Be Vietnam Pro (thân chữ) và Gelasio (chữ nhấn nghiêng) — **tự phục vụ** từ
 * `public/fonts`, khai trong `phong-chu.css` (12/10).
 *
 * Trước 12/10 dùng `next/font/google`, tức `next build` tải phông từ Google lúc dựng: máy
 * dựng không có mạng (Docker) là hỏng, và ngày 12/10 đã có một lần hỏng giữa chừng. Vẫn
 * giữ cách Google chia bộ chữ (`unicode-range` tiếng Việt / Latin) để trình duyệt chỉ tải
 * phần cần dùng. Vì sao chọn hai phông này: Geist thiếu dấu tiếng Việt; Georgia trên
 * Windows thiếu chữ hai dấu ("ắ", "ầ") — xem `app/globals.css` và `tests/phongChu.test.cjs`.
 */

export const metadata: Metadata = {
  metadataBase: new URL("https://xklddieuduong.vn"),
  title: {
    default: "Điều dưỡng Nhật Bản | Công ty Nhân lực Quốc tế DC",
    template: "%s | Điều dưỡng Nhật Bản DC",
  },
  description:
    "Tư vấn chương trình điều dưỡng và hộ lý Nhật Bản: điều kiện, chi phí, quy trình và đơn hàng đang tuyển. Đối chiếu hồ sơ với đơn hàng và nhận lý do cụ thể cho từng tiêu chí.",
  keywords: [
    "điều dưỡng Nhật Bản",
    "hộ lý Nhật Bản",
    "xuất khẩu lao động Nhật Bản",
    "kỹ năng đặc định",
    "tokutei ginou",
    "đơn hàng điều dưỡng",
  ],
  openGraph: {
    type: "website",
    locale: "vi_VN",
    siteName: "Điều dưỡng Nhật Bản DC",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="antialiased">{children}</body>
    </html>
  );
}
