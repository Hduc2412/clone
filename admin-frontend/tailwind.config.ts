import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        // 12/10: cùng bộ màu với website (bản thiết kế "Hành trình Nhật Bản" 08/10) — đỏ
        // trầm cho hành động, xanh rêu–ngà cho chữ và nền. Đỏ của LỖI vẫn là `red-*` của
        // Tailwind, không dùng `brand`: màu báo lỗi không được trùng màu nút bấm.
        brand: {
          50: "#fbf1ef",
          100: "#f6e0dc",
          200: "#ecc2bb",
          300: "#dd9a8f",
          400: "#c86e62",
          500: "#b6544a",
          600: "#aa4339",
          700: "#90372f",
          800: "#762e28",
          900: "#5f2722",
        },
        slate: {
          50: "#f4f3ec",
          100: "#ecebe3",
          200: "#e2e6df",
          300: "#c9d0c8",
          400: "#8e9a95",
          500: "#657570",
          600: "#4f625d",
          700: "#3c514c",
          800: "#2b4440",
          900: "#203c39",
          950: "#142a27",
        },
        reu: { 50: "#eaf0e8", 100: "#dce6da", 600: "#347361", 700: "#2a5d4f" },
        kem: { DEFAULT: "#f7f6f0", dam: "#efeee6" },
        ink: { 700: "#2b4440", 800: "#203c39", 900: "#18302d" },
      },
    },
  },
  plugins: [],
};
export default config;
