import type { Config } from "tailwindcss";

/**
 * Màu thương hiệu đỏ #cb1d1e trước đây được viết cứng ở hơn hai chục chỗ trong
 * mã nguồn. Đưa vào đây để đổi một lần là đổi cả trang, và để dải màu có đủ sắc
 * độ dùng cho nền nhạt, viền và chữ thay vì chỉ một màu duy nhất.
 */
const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./content/**/*.{js,ts}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fef2f2",
          100: "#fde3e3",
          200: "#fbcbcb",
          300: "#f7a6a6",
          400: "#ef7172",
          500: "#e14344",
          600: "#cb1d1e",
          700: "#a81718",
          800: "#8b1718",
          900: "#741a1a",
        },
        // Xanh chàm dùng cho khối thông tin và nền tối, để trang không chỉ có
        // đỏ và trắng. Đỏ chỉ dành cho nút hành động và điểm nhấn.
        ink: {
          50: "#f6f7f9",
          700: "#2a3442",
          800: "#1f2733",
          900: "#171b22",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "Segoe UI", "sans-serif"],
      },
      maxWidth: {
        container: "72rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,.04), 0 8px 24px -12px rgba(15,23,42,.18)",
        lift: "0 2px 4px rgba(15,23,42,.04), 0 18px 40px -16px rgba(203,29,30,.35)",
      },
      keyframes: {
        // Nền động: các khối màu trôi rất chậm. Biên độ nhỏ và thời gian dài để
        // chuyển động gần như không nhận ra khi đọc chữ, chỉ thấy trang "có thở".
        drift: {
          "0%,100%": { transform: "translate3d(0,0,0) scale(1)" },
          "33%": { transform: "translate3d(3%,-4%,0) scale(1.06)" },
          "66%": { transform: "translate3d(-3%,3%,0) scale(0.96)" },
        },
        fall: {
          "0%": { transform: "translate3d(0,-10%,0) rotate(0deg)", opacity: "0" },
          "10%": { opacity: "1" },
          "90%": { opacity: "1" },
          "100%": { transform: "translate3d(2rem,110vh,0) rotate(240deg)", opacity: "0" },
        },
        // Cánh hoa vừa rơi vừa dạt ngang, thay vì rơi thẳng như hòn sỏi.
        // Đường đi hình sin làm nó giống lá rơi trong gió hơn.
        petal: {
          '0%':   { transform: 'translate3d(0,-8%,0) rotate(0deg)', opacity: '0' },
          '8%':   { opacity: '1' },
          '25%':  { transform: 'translate3d(2.5rem,25vh,0) rotate(90deg)' },
          '50%':  { transform: 'translate3d(-1.5rem,50vh,0) rotate(180deg)' },
          '75%':  { transform: 'translate3d(3rem,75vh,0) rotate(270deg)' },
          '92%':  { opacity: '1' },
          '100%': { transform: 'translate3d(0,108vh,0) rotate(360deg)', opacity: '0' },
        },
        // Mặt trời thở rất khẽ. Biên độ 3 phần trăm, chu kỳ gần một phút.
        breathe: {
          '0%,100%': { transform: 'scale(1)', opacity: '0.9' },
          '50%':     { transform: 'scale(1.03)', opacity: '1' },
        },
        // Dải mây trôi ngang, mô típ kasumi trong tranh khắc gỗ.
        glide: {
          '0%':   { transform: 'translate3d(-8%,0,0)' },
          '100%': { transform: 'translate3d(8%,0,0)' },
        },
        rise: {
          "0%": { opacity: "0", transform: "translate3d(0,12px,0)" },
          "100%": { opacity: "1", transform: "translate3d(0,0,0)" },
        },
        sheen: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "200% 50%" },
        },
      },
      animation: {
        drift: "drift 38s ease-in-out infinite",
        "drift-slow": "drift 56s ease-in-out infinite",
        fall: "fall linear infinite",
        petal: "petal linear infinite",
        breathe: "breathe 52s ease-in-out infinite",
        glide: "glide 70s ease-in-out infinite alternate",
        "glide-slow": "glide 104s ease-in-out infinite alternate",
        rise: "rise .5s ease-out both",
        sheen: "sheen 6s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
