import type { Metadata } from "next";
import { Be_Vietnam_Pro, Gelasio } from "next/font/google";
import "./globals.css";

// Cùng hai phông với website (12/10). Trước đó màn quản trị dùng phông hệ thống;
// Gelasio cho dòng nhấn nghiêng vì Georgia trên Windows thiếu chữ hai dấu ("ắ", "ầ").
const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});
const gelasio = Gelasio({
  subsets: ["vietnamese", "latin"],
  weight: ["400", "600"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DC Kaigo | Hệ thống quản lý",
  description: "Hệ thống quản lý tư vấn và tuyển dụng điều dưỡng Nhật Bản.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" className={`${beVietnamPro.variable} ${gelasio.variable}`}>
      <body>{children}</body>
    </html>
  );
}
