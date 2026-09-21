/**
 * Thông tin doanh nghiệp và điều hướng.
 *
 * Lấy từ khảo sát trang thật `xklddieuduong.vn` ngày 14/09/2026, ghi lại trong
 * `docs/design/16_NOI_DUNG_WEBSITE.md`. Để ở một chỗ để đổi số điện thoại hay
 * địa chỉ là đổi toàn trang, không phải đi tìm từng nơi.
 */

export const COMPANY = {
  shortName: "Nhân lực Quốc tế DC",
  legalName: "Công ty Đầu tư Phát triển Nhân lực Quốc tế DC",
  tagline: "Điều dưỡng và hộ lý Nhật Bản",
  hotline: "0971.716.939",
  hotlineHref: "tel:0971716939",
  zalo: "0971716939",
  email: "tuyensinh@xklddieuduong.vn",
  workingHours: "Thứ Hai đến Thứ Bảy, 08:00–11:30 và 13:30–17:00",
} as const;

export const OFFICES = [
  {
    city: "Hà Nội",
    label: "Trụ sở chính",
    address: "Tầng 6, Tòa nhà Hữu Nghị, 188 Lê Quang Đạo, Nam Từ Liêm",
  },
  {
    city: "TP. Hồ Chí Minh",
    label: "Văn phòng phía Nam",
    address: "Khu đô thị Vạn Phúc, TP. Thủ Đức",
  },
  {
    city: "Bến Tre",
    label: "Văn phòng miền Tây",
    address: "201C2 Phan Đình Phùng, TP. Bến Tre",
  },
] as const;

export const NAV = [
  { href: "/gioi-thieu", label: "Giới thiệu" },
  { href: "/he-thong", label: "Hệ thống" },
  { href: "/dieu-kien", label: "Điều kiện" },
  { href: "/chi-phi", label: "Chi phí" },
  { href: "/quy-trinh", label: "Quy trình" },
  { href: "/dao-tao", label: "Đào tạo" },
  { href: "/don-hang", label: "Đơn hàng" },
  { href: "/cau-hoi-thuong-gap", label: "Hỏi đáp" },
  { href: "/lien-he", label: "Liên hệ" },
] as const;

/**
 * Khối uy tín. Trang thật dành phần lớn diện tích cho phần này vì trong ngành
 * xuất khẩu lao động, nỗi sợ lớn nhất của người lao động là bị lừa.
 *
 * Ở đây chỉ để sẵn chỗ. Ảnh giấy phép thật do doanh nghiệp cung cấp; bản demo
 * hiển thị ô giữ chỗ có ghi rõ, **không dựng giấy tờ giả**.
 */
export const TRUST_ITEMS = [
  {
    title: "Giấy phép hoạt động dịch vụ đưa người lao động đi làm việc ở nước ngoài",
    detail: "Do Bộ Lao động, Thương binh và Xã hội cấp",
    pending: true,
  },
  {
    title: "Xác nhận của Sở Nội vụ các tỉnh",
    detail: "Hồ sơ tuyển chọn tại địa phương",
    pending: true,
  },
  {
    title: "Ba văn phòng tại Hà Nội, TP. Hồ Chí Minh và Bến Tre",
    detail: "Tiếp nhận hồ sơ và phỏng vấn trực tiếp",
    pending: false,
  },
  {
    title: "Trung tâm đào tạo tiếng Nhật có ký túc xá",
    detail: "Học viên ở nội trú trong thời gian đào tạo",
    pending: true,
  },
] as const;

export const HERO_STATS = [
  {
    value: "160–240",
    label: "nghìn yên mỗi tháng",
    note: "Lương cơ bản theo đơn hàng, chưa gồm phụ cấp và làm thêm",
  },
  {
    value: "N5–N3",
    label: "trình độ tiếng Nhật",
    note: "Tùy diện chương trình và cơ sở tiếp nhận",
  },
  {
    value: "3",
    label: "diện chương trình",
    note: "EPA, Kỹ năng đặc định và Thực tập sinh kỹ năng",
  },
  {
    value: "24/7",
    label: "tiếp nhận câu hỏi",
    note: "Trả lời ngoài giờ hành chính, có nhân viên gọi lại",
  },
] as const;

/** Ghi chú dùng lại ở mọi nơi có số liệu chưa được doanh nghiệp xác nhận. */
export const REFERENCE_NOTE =
  "Số liệu mang tính tham khảo, thay đổi theo từng đơn hàng và thời điểm. Nhân viên tư vấn sẽ xác nhận con số chính xác cho trường hợp của bạn.";
