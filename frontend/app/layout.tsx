import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";

/**
 * Be Vietnam Pro thay cho Geist. Geist không có bộ dấu tiếng Việt đầy đủ nên
 * những chữ như "ữ", "ặ", "ỡ" bị trình duyệt thay bằng phông dự phòng, làm dòng
 * chữ cao thấp không đều. Ngoài ra Geist trước đây cũng đang bị `globals.css`
 * ghi đè nên thực tế chưa bao giờ có tác dụng.
 */
const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

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
    <html lang="vi" className={beVietnamPro.variable}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
