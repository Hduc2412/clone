/** @type {import('next').NextConfig} */
const nextConfig = {
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
