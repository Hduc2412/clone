/**
 * Thông tin doanh nghiệp và điều hướng.
 *
 * Lấy từ khảo sát trang thật `xklddieuduong.vn` ngày 14/09/2026, ghi lại trong
 * `docs/design/16_NOI_DUNG_WEBSITE.md`. Để ở một chỗ để đổi số điện thoại hay
 * địa chỉ là đổi toàn trang, không phải đi tìm từng nơi.
 *
 * ## Số hotline và địa chỉ đường phố không nằm trong tệp này
 *
 * Kho mã công khai, và hai thứ đó là thông tin liên lạc của người thật. Commit
 * vào lịch sử git thì xóa đi rất khó, mà crawler thu số điện thoại đọc GitHub
 * trước cả website.
 *
 * Khai trong `frontend/.env.local` — tệp ấy không vào kho:
 *
 *     NEXT_PUBLIC_HOTLINE=...
 *     NEXT_PUBLIC_OFFICE_HANOI_ADDRESS=...
 *     NEXT_PUBLIC_OFFICE_HCM_ADDRESS=...
 *     NEXT_PUBLIC_OFFICE_BENTRE_ADDRESS=...
 *
 * Chưa khai thì trang hiện số giả và câu "Liên hệ hotline để biết địa chỉ". Có
 * chủ ý: thà hiện rõ là chưa cấu hình, hơn là để trống rồi không ai nhận ra.
 *
 * Next thay `NEXT_PUBLIC_*` vào lúc dựng, nên các giá trị này dùng được cả ở
 * component chạy trên trình duyệt.
 */

/** Số giả, dùng khi chưa khai cấu hình. Nhìn là biết ngay chưa cấu hình. */
const HOTLINE_CHUA_KHAI = "0000.000.000";
const DIA_CHI_CHUA_KHAI = "Liên hệ hotline để biết địa chỉ";

const HOTLINE = process.env.NEXT_PUBLIC_HOTLINE || HOTLINE_CHUA_KHAI;

/** Bỏ mọi ký tự không phải chữ số, để dựng `tel:` và mã Zalo. */
const chiSo = (so: string) => so.replace(/\D/g, "");

/** Địa chỉ có thật hay đang là chỗ trống — chỗ nào cần thì tự quyết cách hiện. */
export const coDiaChiThat = (diaChi: string) => diaChi !== DIA_CHI_CHUA_KHAI;

export const COMPANY = {
  shortName: "Nhân lực Quốc tế DC",
  legalName: "Công ty Đầu tư Phát triển Nhân lực Quốc tế DC",
  tagline: "Điều dưỡng và hộ lý Nhật Bản",
  hotline: HOTLINE,
  hotlineHref: `tel:${chiSo(HOTLINE)}`,
  zalo: chiSo(HOTLINE),
  email: "tuyensinh@xklddieuduong.vn",
  workingHours: "Thứ Hai đến Thứ Bảy, 08:00–11:30 và 13:30–17:00",
  /**
   * Khung giờ nói với khách khi mời họ liên hệ — cố ý gọn hơn `workingHours`.
   *
   * `workingHours` là giờ làm việc chính thức, có nghỉ trưa, và nó cần chi tiết
   * vì phần đặt lịch hẹn chặn đúng khoảng nghỉ đó. Còn khi chỉ mời người ta nhắn
   * tin hay gọi điện thì "8h đến 17h" là đủ: bắt khách nhớ hai khoảng giờ rời
   * nhau để gửi một câu hỏi là đặt một rào cản không cần thiết.
   */
  contactHours: "8h đến 17h",
} as const;

// Tên thành phố vẫn để trong kho: nó có trên mọi giấy tờ giới thiệu của công ty
// và không chỉ tới một địa điểm cụ thể nào. Chỉ số nhà và tên đường là phần rút
// ra ngoài.
export const OFFICES = [
  {
    city: "Hà Nội",
    label: "Trụ sở chính",
    address: process.env.NEXT_PUBLIC_OFFICE_HANOI_ADDRESS || DIA_CHI_CHUA_KHAI,
  },
  {
    city: "TP. Hồ Chí Minh",
    label: "Văn phòng phía Nam",
    address: process.env.NEXT_PUBLIC_OFFICE_HCM_ADDRESS || DIA_CHI_CHUA_KHAI,
  },
  {
    city: "Bến Tre",
    label: "Văn phòng miền Tây",
    address: process.env.NEXT_PUBLIC_OFFICE_BENTRE_ADDRESS || DIA_CHI_CHUA_KHAI,
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
  { href: "/tai-khoan", label: "Hồ sơ của tôi" },
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
    // Con số công ty công bố. Bản cũ ghi "160–240 nghìn yên" — một khoảng tôi
    // suy từ lương của mấy đơn mẫu tự đặt, không có trang nào đỡ lưng. Đây là
    // dòng đầu tiên khách đọc trên trang chủ, nên nó phải là con số của công ty
    // chứ không phải con số của dữ liệu demo.
    value: "30–35",
    label: "triệu đồng mỗi tháng",
    note: "Mức công ty công bố, chưa gồm phụ cấp và làm thêm. Từng đơn ghi mức riêng bằng yên",
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
