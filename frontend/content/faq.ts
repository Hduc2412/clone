/**
 * Câu hỏi thường gặp.
 *
 * Trường `topic` dùng đúng bộ chủ đề mà phần chatbot đang phân loại, để sau này
 * nút "hỏi thêm về mục này" mở khung chat đúng ngữ cảnh, và để nội dung trên
 * web với nội dung chatbot trả lời không nói hai kiểu khác nhau.
 */

export type FaqTopic =
  | "chi_phi"
  | "dieu_kien"
  | "quy_trinh"
  | "luong_thuong"
  | "hoc_tap"
  | "cong_viec"
  | "thoi_gian"
  | "ky_tuc_xa";

export const FAQ_TOPIC_LABELS: Record<FaqTopic, string> = {
  dieu_kien: "Điều kiện tham gia",
  chi_phi: "Chi phí",
  quy_trinh: "Quy trình và hồ sơ",
  luong_thuong: "Lương và thu nhập",
  cong_viec: "Công việc thực tế",
  hoc_tap: "Học tiếng Nhật",
  thoi_gian: "Thời gian",
  ky_tuc_xa: "Ăn ở và sinh hoạt",
};

export interface FaqItem {
  topic: FaqTopic;
  question: string;
  answer: string;
  /** Hiện trên trang chủ hay không. Trang chủ chỉ lấy năm câu. */
  featured?: boolean;
}

export const FAQ: FaqItem[] = [
  {
    topic: "dieu_kien",
    question: "Chưa biết tiếng Nhật thì có đăng ký được không?",
    answer:
      "Được. Phần lớn học viên bắt đầu từ con số không và học tại trung tâm trước khi xuất cảnh. Trình độ tiếng Nhật là điều kiện tại thời điểm nộp hồ sơ vào đơn hàng, không phải điều kiện lúc đăng ký ban đầu.",
    featured: true,
  },
  {
    topic: "dieu_kien",
    question: "Không học ngành điều dưỡng thì có đi được không?",
    answer:
      "Tùy đơn hàng. Diện thực tập sinh có những đơn nhận người tốt nghiệp trung học phổ thông. Diện kỹ năng đặc định và EPA thường yêu cầu bằng trung cấp điều dưỡng trở lên. Bạn có thể xem điều kiện bắt buộc của từng đơn trong mục Đơn hàng.",
    featured: true,
  },
  {
    topic: "dieu_kien",
    question: "Có hình xăm thì sao?",
    answer:
      "Cơ sở chăm sóc người cao tuổi tại Nhật thường yêu cầu chặt điểm này vì tiếp xúc trực tiếp với người bệnh và gia đình họ. Hình xăm ở vị trí quần áo che kín vẫn có cơ hội, nhưng cần thông báo trước để tư vấn viên chọn đơn phù hợp.",
  },
  {
    topic: "chi_phi",
    question: "Tổng chi phí hết bao nhiêu?",
    answer:
      // 13/10: thống nhất với kho tri thức và trang Chi phí (`pages.ts` COSTS, theo trang chi
      // phí chính thức của công ty). Bản cũ không nêu con số nào —
      // trong khi khung chat và trợ lý trả lời "90 triệu trọn gói".
      "Trọn gói 90 triệu đồng, chia ba chặng: 10 triệu khi đăng ký, 35 triệu khi nhập học tiếng Nhật, 45 triệu trước khi xuất cảnh (được nợ lại, sang Nhật làm trả trong 8 tháng). Công ty cấp hồ sơ vay vốn dưới 100 triệu từ Ngân hàng chính sách địa phương. Hộ chiếu, visa, lý lịch tư pháp đóng theo mức phí nhà nước. Nhân viên tư vấn xác nhận lại cho trường hợp của bạn.",
    featured: true,
  },
  {
    topic: "chi_phi",
    question: "Có được đóng chi phí theo từng đợt không?",
    answer:
      "Có. Ba chặng: 10 triệu khi đăng ký, 35 triệu khi nhập học tiếng Nhật, 45 triệu trước khi xuất cảnh. Không phải đóng toàn bộ ngay từ đầu. Khám sức khỏe không mất tiền — công ty đưa đi khám tại bệnh viện được chỉ định.",
  },
  {
    topic: "chi_phi",
    question: "Nếu phỏng vấn không đỗ thì có mất tiền không?",
    answer:
      "Khoản 10 triệu đặt cọc lúc đăng ký: phỏng vấn không đỗ thì công ty trả lại luôn, đỗ thì tính vào chi phí đã đóng. Khám sức khỏe không mất tiền. Trượt đơn này vẫn được giới thiệu sang đơn khác mà không phải bắt đầu lại từ đầu.",
  },
  {
    topic: "luong_thuong",
    question: "Lương điều dưỡng tại Nhật khoảng bao nhiêu?",
    answer:
      "Công ty công bố mức 30 đến 35 triệu đồng mỗi tháng, chưa tính phụ cấp ca đêm và làm thêm giờ. Mức cụ thể của từng đơn ghi bằng yên trong mục Đơn hàng. Đây là lương trước thuế và bảo hiểm.",
    featured: true,
  },
  {
    topic: "luong_thuong",
    question: "Tiền lương có bị trừ những khoản gì?",
    answer:
      "Thuế thu nhập, bảo hiểm y tế, bảo hiểm hưu trí và tiền nhà nếu ở ký túc xá của cơ sở. Đây là các khoản bắt buộc theo luật Nhật Bản, áp dụng như với người lao động bản địa.",
  },
  {
    topic: "cong_viec",
    question: "Công việc hằng ngày gồm những gì?",
    answer:
      "Hỗ trợ sinh hoạt cho người cao tuổi: ăn uống, vệ sinh cá nhân, di chuyển, tắm rửa, và trò chuyện. Ghi chép tình trạng hằng ngày. Làm việc theo ca cùng nhân viên người Nhật, không làm một mình trong thời gian đầu.",
    featured: true,
  },
  {
    topic: "cong_viec",
    question: "Công việc có vất vả không?",
    answer:
      "Có phần nặng về thể lực, nhất là khi hỗ trợ di chuyển người bệnh. Cơ sở hiện đại có thiết bị nâng đỡ. Nhiều học viên cho biết phần khó hơn cả là giao tiếp trong vài tháng đầu, nên trình độ tiếng Nhật ảnh hưởng trực tiếp tới mức độ thoải mái khi làm việc.",
  },
  {
    topic: "quy_trinh",
    question: "Từ lúc đăng ký đến lúc bay mất bao lâu?",
    answer:
      "Cộng các bước ở mục Quy trình: học tiếng Nhật 6–7 tháng, hoàn thiện hồ sơ và xin tư cách lưu trú 2–4 tháng, đào tạo trước xuất cảnh 1 tháng — khoảng 9 đến 12 tháng. Nếu đã có chứng chỉ tiếng Nhật thì rút ngắn đáng kể.",
    featured: true,
  },
  {
    topic: "quy_trinh",
    question: "Hồ sơ cần chuẩn bị những gì?",
    answer:
      "Căn cước công dân, bằng tốt nghiệp và bảng điểm, sơ yếu lý lịch có xác nhận, giấy khám sức khỏe, ảnh thẻ, hộ chiếu. Chứng chỉ tiếng Nhật nếu có. Nhân viên hướng dẫn chi tiết từng loại sau khi tiếp nhận.",
  },
  {
    topic: "thoi_gian",
    question: "Hợp đồng kéo dài bao lâu và có được gia hạn không?",
    answer:
      "Thực tập sinh ba năm, gia hạn được lên năm năm. Kỹ năng đặc định tối đa năm năm, thi lên bậc hai thì được ở lại lâu dài. EPA ba tới bốn năm, đỗ chứng chỉ quốc gia Nhật Bản thì gia hạn không giới hạn số lần.",
  },
  {
    topic: "hoc_tap",
    question: "Học tiếng Nhật ở đâu và học bao lâu?",
    answer:
      "Học tập trung tại trung tâm của công ty, ở nội trú trong ký túc xá. Học hết 50 bài mất 6–7 tháng; học phí 35 triệu là một chặng trong tổng 90 triệu.",
  },
  {
    topic: "ky_tuc_xa",
    question: "Sang Nhật ở đâu?",
    answer:
      "Phần lớn cơ sở tiếp nhận bố trí ký túc xá hoặc hỗ trợ thuê nhà gần nơi làm việc. Chi phí và mức hỗ trợ ghi trong phần thông tin tham khảo của từng đơn hàng.",
  },
];

export const FEATURED_FAQ = FAQ.filter((item) => item.featured);
