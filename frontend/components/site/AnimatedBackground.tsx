/**
 * Nền động phía sau nội dung.
 *
 * Vẽ hoàn toàn bằng CSS và SVG, không tải một tấm ảnh nào. Lý do: phần lớn ứng
 * viên vào bằng điện thoại và bằng mạng di động, một ảnh nền vài trăm KB làm
 * trang trắng thêm vài giây — đúng lúc người ta dễ bỏ đi nhất. Cách này nặng
 * gần bằng không và không bao giờ vỡ khi phóng to.
 *
 * ## Bố cục theo lớp, từ xa tới gần
 *
 * 1. Trời hửng sáng — dải màu chuyển từ hồng đào sang trắng.
 * 2. Mặt trời — đĩa tròn thở rất khẽ, mô típ trên quốc kỳ.
 * 3. Mây kasumi — hai dải mây trôi ngang, lấy từ tranh khắc gỗ.
 * 4. Núi Phú Sĩ — hai rặng núi chồng nhau, rặng sau nhạt hơn để có chiều sâu.
 * 5. Sóng seigaiha — hai hàng sóng ở mép dưới.
 * 6. Cánh hoa anh đào — rơi theo đường sin, không rơi thẳng.
 *
 * Mỗi lớp chuyển động một tốc độ khác nhau, tạo cảm giác xa gần mà không cần
 * thư viện nào. Biên độ cố ý nhỏ và chu kỳ dài — từ 52 tới 104 giây — để mắt
 * thấy trang "có thở" mà không bị kéo sự chú ý khỏi chữ. `globals.css` đã có
 * khối `prefers-reduced-motion` tắt sạch mọi chuyển động cho người cần.
 */

type Variant = "hero" | "soft" | "dark";

/** Vị trí, độ trễ và tốc độ từng cánh hoa. Rải lệch nhau để không thấy nhịp lặp. */
const PETALS = [
  { left: "6%", delay: "-7s", duration: "19s", size: 11, opacity: 0.55 },
  { left: "18%", delay: "-5s", duration: "26s", size: 8, opacity: 0.4 },
  { left: "29%", delay: "-11s", duration: "22s", size: 13, opacity: 0.45 },
  { left: "43%", delay: "-3s", duration: "29s", size: 9, opacity: 0.5 },
  { left: "56%", delay: "-16s", duration: "21s", size: 12, opacity: 0.35 },
  { left: "67%", delay: "-8s", duration: "27s", size: 10, opacity: 0.45 },
  { left: "79%", delay: "-20s", duration: "24s", size: 8, opacity: 0.4 },
  { left: "88%", delay: "-13s", duration: "31s", size: 14, opacity: 0.3 },
  { left: "96%", delay: "-6s", duration: "23s", size: 9, opacity: 0.45 },
];

export default function AnimatedBackground({
  variant = "hero",
  petals = true,
}: {
  variant?: Variant;
  petals?: boolean;
}) {
  const isDark = variant === "dark";
  const isSoft = variant === "soft";

  return (
    // aria-hidden: đây thuần là trang trí, trình đọc màn hình không cần biết.
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* 1 · Trời hửng sáng */}
      <div
        className={
          isDark
            ? "absolute inset-0 bg-gradient-to-b from-ink-900 via-ink-800 to-ink-900"
            : "absolute inset-0 bg-gradient-to-b from-[#ffeef0] via-[#fff7f4] to-white"
        }
      />

      {/* Khối màu mờ trôi chậm, giữ cho nền không phẳng lì. */}
      <div
        className={`absolute -left-28 -top-36 h-[30rem] w-[30rem] rounded-full blur-3xl animate-drift ${
          isDark ? "bg-brand-700/25" : "bg-brand-200/45"
        }`}
      />
      <div
        className={`absolute -right-36 top-6 h-[34rem] w-[34rem] rounded-full blur-3xl animate-drift-slow ${
          isDark ? "bg-sky-500/10" : "bg-sky-200/35"
        }`}
        style={{ animationDelay: "-12s" }}
      />

      {/* 2 · Mặt trời. Đĩa đặc có viền quầng, thay cho vòng tròn kẻ mảnh trước
          đây — vòng kẻ mảnh gần như không thấy trên nền sáng. */}
      {!isSoft && (
        // Trên điện thoại, cột chữ chiếm gần trọn bề ngang nên mặt trời đặt ở
        // giữa mép phải sẽ đè lên tiêu đề. Đẩy nó ra khỏi mép và thu nhỏ lại để
        // chỉ còn ló một phần ở góc.
        <div
          className="absolute -right-10 top-[3%] animate-breathe md:right-[7%] md:top-[9%]"
          style={{ animationDelay: "-6s" }}
        >
          <div
            className={`h-28 w-28 rounded-full md:h-52 md:w-52 ${
              isDark
                ? "bg-brand-600/30 shadow-[0_0_90px_36px_rgba(203,29,30,0.18)]"
                : "bg-gradient-to-br from-[#ffb3ab] to-[#f8837c] opacity-70 shadow-[0_0_80px_30px_rgba(248,131,124,0.28)]"
            }`}
          />
        </div>
      )}

      {/* 3 · Mây kasumi. Hai dải trôi ngược chiều nhau ở hai tốc độ. */}
      {!isSoft && (
        <>
          <CloudBand
            className="top-[6%] animate-glide"
            opacity={isDark ? 0.06 : 0.5}
            dark={isDark}
          />
          <CloudBand
            className="top-[20%] animate-glide-slow"
            opacity={isDark ? 0.04 : 0.32}
            dark={isDark}
            flip
          />
        </>
      )}

      {/* 4 · Núi Phú Sĩ. Rặng sau nhạt và cao hơn, rặng trước đậm và thấp hơn —
          chênh lệch đó làm mắt tự hiểu là có chiều sâu. */}
      {!isSoft && (
        // Núi neo vào đáy khối chứa. Khối hero thường cao hơn màn hình, nên nếu
        // để chiều cao núi phụ thuộc bề rộng thì đỉnh rơi xuống dưới tầm nhìn.
        // Đặt chiều cao cố định để đỉnh luôn nằm trong khung nhìn đầu tiên.
        <div className="absolute inset-x-0 bottom-0">
          <Fuji
            className="absolute inset-x-0 bottom-0 h-[19rem] md:h-[25rem] animate-glide-slow"
            fill={isDark ? "#2a3442" : "#f3c9c4"}
            opacity={isDark ? 0.55 : 0.5}
            snow={isDark ? "#3b4757" : "#ffffff"}
          />
          <Fuji
            className="absolute inset-x-0 bottom-0 h-[14rem] translate-y-[6%] scale-x-110 md:h-[18rem] animate-glide"
            fill={isDark ? "#1f2733" : "#e79b96"}
            opacity={isDark ? 0.8 : 0.42}
            snow={isDark ? "#2a3442" : "#fff5f3"}
          />
        </div>
      )}

      {/* 5 · Sóng seigaiha. Hai hàng chồng nhau, hàng trên nhạt hơn. */}
      <div
        className={`pattern-seigaiha absolute inset-x-0 bottom-6 ${
          isSoft ? "h-8" : "h-16"
        } ${
          isDark
            ? "text-white/[0.07]"
            : isSoft
              ? "text-brand-400/[0.08]"
              : "text-brand-400/15"
        }`}
      />
      <div
        className={`pattern-seigaiha absolute inset-x-0 bottom-0 ${
          isSoft ? "h-10" : "h-20"
        } ${
          isDark
            ? "text-white/10"
            : isSoft
              ? "text-brand-400/[0.14]"
              : "text-brand-400/25"
        }`}
      />

      {/* 6 · Cánh hoa anh đào */}
      {petals && (
        <div className="absolute inset-0">
          {PETALS.map((petal) => (
            <span
              key={petal.left}
              className="absolute top-0 animate-petal"
              style={{
                left: petal.left,
                animationDelay: petal.delay,
                animationDuration: petal.duration,
                opacity: petal.opacity,
              }}
            >
              <Petal size={petal.size} dark={isDark} />
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Một dải mây. Ba hình bầu dục chồng lên nhau rồi làm mờ — rẻ hơn nhiều so với
 * bộ lọc nhiễu, mà ở độ mờ này mắt không phân biệt được.
 */
function CloudBand({
  className,
  opacity,
  dark,
  flip = false,
}: {
  className: string;
  opacity: number;
  dark: boolean;
  flip?: boolean;
}) {
  const mau = dark ? "#ffffff" : "#ffffff";
  return (
    <div
      className={`absolute inset-x-[-10%] ${className}`}
      style={{ opacity, transform: flip ? "scaleX(-1)" : undefined }}
    >
      <svg viewBox="0 0 1200 90" className="h-20 w-full blur-2xl md:h-32" preserveAspectRatio="none">
        <g fill={mau}>
          <ellipse cx="180" cy="52" rx="220" ry="20" />
          <ellipse cx="520" cy="38" rx="280" ry="16" />
          <ellipse cx="930" cy="56" rx="240" ry="22" />
        </g>
      </svg>
    </div>
  );
}

/** Rặng núi có chóp tuyết. Đường gãy ở hai bên chóp là nét đặc trưng của Phú Sĩ. */
function Fuji({
  className,
  fill,
  opacity,
  snow,
}: {
  className: string;
  fill: string;
  opacity: number;
  snow: string;
}) {
  return (
    <svg
      viewBox="0 0 1200 260"
      className={`w-full ${className}`}
      preserveAspectRatio="none"
      style={{ opacity }}
    >
      {/* Sườn núi: dốc thoải hai bên, thắt lại gần đỉnh. */}
      <path
        d="M0 260 L300 120 Q360 74 420 58 L470 36 Q520 14 560 36 L610 58 Q672 76 730 122 L1200 260 Z"
        fill={fill}
      />
      {/* Chóp tuyết, viền dưới lượn sóng như tuyết tan không đều. */}
      <path
        d="M470 36 Q520 14 560 36 L610 58 Q590 70 566 60 Q540 76 512 62 Q488 72 470 58 Z"
        fill={snow}
      />
    </svg>
  );
}

/** Một cánh hoa anh đào. Đầu cánh có khía chữ V, nét nhận ra ngay của hoa anh đào. */
function Petal({ size, dark }: { size: number; dark: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path
        d="M8 15c-3 0-5-2.6-5-5.6C3 6.4 5 3.4 8 1c3 2.4 5 5.4 5 8.4 0 3-2 5.6-5 5.6Z
           M8 15c.7-1.2 1.1-2 1.1-2.9 0-.8-.4-1.5-1.1-2-.7.5-1.1 1.2-1.1 2 0 .9.4 1.7 1.1 2.9Z"
        fill={dark ? "#f7a6a6" : "#f0888a"}
        fillRule="evenodd"
      />
    </svg>
  );
}
