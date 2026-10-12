/** @type {import('next').NextConfig} */
const nextConfig = {
  // Thư mục build tách được qua `NEXT_DIST_DIR` — để dựng và chạy bản production
  // kiểm thử mà không đụng `.next` của máy chủ dev (dùng khi kiểm lỗi font 08/10).
  // Không đặt biến thì vẫn là `.next` như cũ.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Gói riêng những gì thật sự chạy được. Ảnh production nhờ đó không phải mang
  // theo cả `node_modules` — khác nhau khoảng vài trăm MB mỗi ảnh.
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "xklddieuduong.vn",
        pathname: "/wp-content/uploads/**",
      },
    ],
  },
};

export default nextConfig;
