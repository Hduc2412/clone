import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DC Kaigo | Hệ thống quản lý",
  description: "Hệ thống quản lý tư vấn và tuyển dụng điều dưỡng Nhật Bản.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
