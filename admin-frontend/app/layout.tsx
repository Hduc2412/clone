import type { Metadata } from "next";
import "./phong-chu.css";
import "./globals.css";

// Cùng hai phông với website, tự phục vụ từ `public/fonts` (`phong-chu.css`) — build không
// cần mạng tới Google (12/10).

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
