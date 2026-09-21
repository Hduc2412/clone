/**
 * Phông nền bằng ảnh thật, ba tấm nối nhau.
 *
 * Trước đây nền vẽ hoàn toàn bằng CSS để không phải tải ảnh. Nay dùng ảnh thật
 * cho bắt mắt hơn, nhưng lý do cũ vẫn còn nguyên giá trị nên phải bù lại:
 *
 * - Ảnh đã cắt sẵn 16:9, nén WebP chất lượng 72. Bản cho điện thoại 960px chỉ
 *   45–93 KB, bản màn hình lớn 1920px là 181–297 KB. Trình duyệt tự chọn bản
 *   phù hợp qua `srcset`, nên máy điện thoại không phải tải bản to.
 * - Chỉ tấm đầu tải ngay; hai tấm sau `loading="lazy"`.
 * - Không có ảnh nào thì phần dải màu bên dưới vẫn giữ trang tử tế.
 *
 * ## Chữ vẫn phải đọc được
 *
 * Lớp phủ không đổ đều. Nó đậm ở bên trái — nơi có tiêu đề và đoạn dẫn — rồi
 * nhạt dần sang phải để tấm ảnh lộ ra. Nhờ vậy giữ được chữ màu đậm như cũ mà
 * không phải đổi sang chữ trắng, và ảnh vẫn nhìn thấy rõ. Trên điện thoại cột
 * chữ chiếm gần trọn bề ngang nên lớp phủ đậm đều hơn.
 *
 * ## Nguồn ảnh
 *
 * Xem `public/nen/NGUON.md`. Cả ba đều có giấy phép cho phép dùng lại; hai tấm
 * đòi ghi công và phần ghi công nằm ở chân trang.
 */

type Variant = "hero" | "soft" | "dark";

const ANH = [
  {
    ten: "fuji-binh-minh",
    mo_ta: "Núi Phú Sĩ lúc bình minh",
    delay: "0s",
  },
  {
    ten: "fuji-hoa-anh-dao",
    mo_ta: "Núi Phú Sĩ mùa hoa anh đào",
    delay: "-10s",
  },
  {
    ten: "ho-kawaguchi",
    mo_ta: "Hồ Kawaguchi nhìn về núi Phú Sĩ",
    delay: "-20s",
  },
];

export default function PhotoBackdrop({ variant = "hero" }: { variant?: Variant }) {
  const isDark = variant === "dark";
  const isSoft = variant === "soft";

  return (
    <div aria-hidden className="absolute inset-0 overflow-hidden">
      {/* Dải màu nằm dưới cùng: ảnh chưa tải xong hay tải hỏng thì trang vẫn tử tế. */}
      <div
        className={
          isDark
            ? "absolute inset-0 bg-ink-900"
            : "absolute inset-0 bg-gradient-to-b from-[#ffeef0] via-[#fff7f4] to-white"
        }
      />

      {ANH.map((anh, i) => (
        // Dùng `<img>` chứ không `next/image`. Việc `next/image` làm hộ — chọn
        // kích thước theo màn hình, hoãn tải, nén — thì ba tấm này đã làm sẵn
        // lúc chuẩn bị: cắt đúng tỷ lệ, xuất hai cỡ, nén WebP. Đưa qua bộ tối ưu
        // lúc chạy chỉ là nén lại thứ đã nén, thêm việc cho máy chủ mà không
        // được gì. Xem `public/nen/NGUON.md`.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={anh.ten}
          src={`/nen/${anh.ten}.webp`}
          srcSet={`/nen/${anh.ten}-nho.webp 960w, /nen/${anh.ten}.webp 1920w`}
          sizes="100vw"
          alt=""
          // Tấm đầu là thứ người dùng thấy ngay, tải ngay. Hai tấm sau chỉ xuất
          // hiện sau mười giây nên để trình duyệt tải lúc rảnh.
          loading={i === 0 ? "eager" : "lazy"}
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
          // Hai chuyển động chạy cùng lúc trên chính tấm ảnh: chồng mờ lo phần
          // chuyển tiếp, phóng chậm lo phần "ảnh không đứng yên". Viết bằng
          // style thay vì hai lớp Tailwind vì hai lớp đó cùng đặt thuộc tính
          // `animation` nên lớp sau xoá lớp trước.
          //
          // `animationDelay` phải nằm SAU `animation`: dạng viết tắt đặt lại độ
          // trễ về 0, nên để trước thì độ trễ bị xoá và ba tấm chồng lên nhau.
          style={{
            animation:
              "crossfade 30s linear infinite, kenburns 30s ease-out infinite",
            animationDelay: anh.delay,
          }}
        />
      ))}

      {/* Lớp phủ giữ chữ đọc được. Đậm trái, nhạt phải. */}
      <div
        className={
          isDark
            ? "absolute inset-0 bg-ink-900/70"
            : "absolute inset-0 bg-gradient-to-r from-white/95 via-white/82 to-white/40 md:from-white/94 md:via-white/78 md:to-white/12"
        }
      />
      {/* Chuyển mềm xuống phần nội dung bên dưới, tránh đường cắt ngang gắt.
          Thấp hơn hẳn ở đầu trang con: khối đó chỉ cao chừng 290px, nên dải mờ
          112px như ở trang chủ sẽ nuốt hơn một phần ba tấm ảnh và đẩy dải sóng
          ra nằm lửng lơ trên nền trắng. */}
      <div
        className={`absolute inset-x-0 bottom-0 ${isSoft ? "h-10" : "h-28"} ${
          isDark ? "bg-gradient-to-t from-ink-900" : "bg-gradient-to-t from-white"
        }`}
      />

      {/* Sóng seigaiha giữ lại từ bản cũ: một nét Nhật Bản do mình vẽ, đặt trên
          ảnh thì thành viền trang trí chứ không tranh chỗ. */}
      <div
        className={`pattern-seigaiha absolute inset-x-0 bottom-0 ${
          isSoft ? "h-10" : "h-16"
        } ${isDark ? "text-white/10" : "text-brand-500/20"}`}
      />
    </div>
  );
}
