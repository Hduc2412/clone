/**
 * Nội dung các trang giới thiệu.
 *
 * Viết lại bằng lời của dự án, không chép chữ từ trang doanh nghiệp. Cấu trúc
 * thông tin thì bám theo tám chuyên mục của trang thật, vì thứ tự đó phản ánh
 * đúng thứ tự câu hỏi mà ứng viên thường hỏi.
 *
 * Chỗ nào có con số mà doanh nghiệp chưa xác nhận thì phải kèm ghi chú tham
 * khảo. Nguyên tắc giống hệt phần chatbot: không có căn cứ thì nói là chưa có.
 */

export const PROGRAMS = [
  {
    code: "tokutei_ginou",
    name: "Kỹ năng đặc định",
    japanese: "特定技能 · Tokutei Ginou",
    duration: "Tối đa 5 năm",
    japaneseLevel: "N4 trở lên",
    summary:
      "Diện phổ biến nhất hiện nay cho ngành chăm sóc. Làm việc như nhân viên chính thức, lương và chế độ tương đương người Nhật cùng vị trí.",
    points: [
      "Được chuyển đổi nơi làm việc trong cùng ngành",
      "Có thể thi lên Kỹ năng đặc định số 2 để gia hạn lâu dài",
      "Yêu cầu đỗ kỳ thi kỹ năng và kỳ thi tiếng Nhật",
    ],
  },
  {
    code: "epa",
    name: "EPA",
    japanese: "Hiệp định đối tác kinh tế Việt – Nhật",
    duration: "3 đến 4 năm, gia hạn nếu đỗ chứng chỉ quốc gia",
    japaneseLevel: "N3 trở lên",
    summary:
      "Chương trình theo hiệp định giữa hai chính phủ. Chi phí thấp nhất trong ba diện, nhưng yêu cầu đầu vào cao và chỉ tiêu ít.",
    points: [
      "Chi phí tham gia thấp do có hỗ trợ từ chương trình",
      "Được đào tạo tiếng Nhật miễn phí trước khi xuất cảnh",
      "Hướng tới thi chứng chỉ điều dưỡng quốc gia Nhật Bản",
    ],
  },
  {
    code: "thuc_tap_sinh",
    name: "Thực tập sinh kỹ năng",
    japanese: "技能実習 · Ginou Jisshuu",
    duration: "3 năm, có thể gia hạn lên 5 năm",
    japaneseLevel: "N5 trở lên",
    summary:
      "Yêu cầu đầu vào thấp nhất, phù hợp với người mới bắt đầu học tiếng Nhật. Vừa làm vừa học nghề tại cơ sở tiếp nhận.",
    points: [
      "Nhận cả ứng viên chưa có kinh nghiệm chăm sóc",
      "Được đào tạo tiếng Nhật tập trung trước khi bay",
      "Sau khi hoàn thành có thể chuyển sang Kỹ năng đặc định",
    ],
  },
] as const;

export const CONDITIONS = [
  {
    criterion: "Độ tuổi",
    requirement: "18 đến 35 tuổi",
    note: "Một số đơn hàng nhận tới 40 tuổi, xem điều kiện từng đơn",
  },
  {
    criterion: "Bằng cấp",
    requirement: "Trung cấp Điều dưỡng trở lên",
    note: "Một số đơn thực tập sinh nhận tốt nghiệp trung học phổ thông",
  },
  {
    criterion: "Tiếng Nhật",
    requirement: "N5 đến N3 tùy diện chương trình",
    note: "Chưa biết tiếng vẫn đăng ký được, học trước khi xuất cảnh",
  },
  {
    criterion: "Sức khỏe",
    requirement: "Đủ điều kiện theo danh mục của Bộ Y tế",
    note: "Khám tại bệnh viện được chỉ định, có 13 nhóm bệnh không đủ điều kiện",
  },
  {
    criterion: "Hình xăm",
    requirement: "Không có hình xăm ở vị trí dễ nhìn thấy",
    note: "Cơ sở chăm sóc người cao tuổi ở Nhật thường yêu cầu chặt điểm này",
  },
  {
    criterion: "Lý lịch",
    requirement: "Không có tiền án, tiền sự",
    note: "Không thuộc diện cấm xuất cảnh",
  },
  {
    criterion: "Kinh nghiệm",
    requirement: "Không bắt buộc với phần lớn đơn hàng",
    note: "Một số đơn lương cao yêu cầu từ một đến hai năm chăm sóc",
  },
] as const;

export const COSTS = [
  {
    item: "Phí dịch vụ",
    amount: "Theo hợp đồng",
    when: "Sau khi trúng tuyển đơn hàng",
    note: "Mức trần do pháp luật quy định, ghi rõ trong hợp đồng",
  },
  {
    item: "Đào tạo tiếng Nhật",
    amount: "Theo khóa học",
    when: "Đóng theo từng giai đoạn học",
    note: "Diện EPA được hỗ trợ phần lớn chi phí này",
  },
  {
    item: "Khám sức khỏe",
    amount: "Khoảng 1 triệu đồng",
    when: "Trước khi phỏng vấn",
    note: "Đóng trực tiếp cho bệnh viện, không qua công ty",
  },
  {
    item: "Hộ chiếu, visa, lý lịch tư pháp",
    amount: "Theo mức phí nhà nước",
    when: "Sau khi có kết quả trúng tuyển",
    note: "Đóng theo biên lai của cơ quan cấp",
  },
  {
    item: "Vé máy bay một chiều",
    amount: "Theo giá vé thời điểm bay",
    when: "Trước khi xuất cảnh",
    note: "Một số đơn hàng do cơ sở tiếp nhận chi trả",
  },
  {
    item: "Ký túc xá trong thời gian học",
    amount: "Theo tháng",
    when: "Hằng tháng trong thời gian đào tạo",
    note: "Bao gồm chỗ ở, điện nước và ăn ca",
  },
] as const;

export const PROCESS = [
  {
    title: "Đăng ký và tư vấn sơ bộ",
    duration: "1 đến 3 ngày",
    detail:
      "Gửi hồ sơ hoặc trò chuyện với hệ thống tư vấn để biết mình phù hợp với những đơn hàng nào. Nhân viên gọi lại xác nhận nguyện vọng.",
  },
  {
    title: "Khám sức khỏe",
    duration: "1 ngày",
    detail:
      "Khám tại bệnh viện được chỉ định theo danh mục của Bộ Y tế. Có kết quả mới nộp hồ sơ vào đơn hàng.",
  },
  {
    title: "Nhập học tiếng Nhật",
    duration: "4 đến 8 tháng",
    detail:
      "Học tập trung tại trung tâm, ở ký túc xá. Học đến trình độ mà đơn hàng yêu cầu, thường là N4 với diện kỹ năng đặc định.",
  },
  {
    title: "Phỏng vấn với cơ sở tiếp nhận",
    duration: "Nửa ngày",
    detail:
      "Cơ sở tiếp nhận bên Nhật phỏng vấn trực tiếp hoặc trực tuyến. Có buổi luyện phỏng vấn trước đó.",
  },
  {
    title: "Hoàn thiện hồ sơ và xin tư cách lưu trú",
    duration: "2 đến 4 tháng",
    detail:
      "Công ty làm hồ sơ xin tư cách lưu trú tại Cục Xuất nhập cảnh Nhật Bản, sau đó xin visa.",
  },
  {
    title: "Đào tạo trước xuất cảnh",
    duration: "1 tháng",
    detail:
      "Học nếp sống, tác phong làm việc và kiến thức chăm sóc cơ bản. Hoàn tất thủ tục xuất cảnh.",
  },
  {
    title: "Xuất cảnh và làm việc",
    duration: "Theo hợp đồng",
    detail:
      "Có người đón tại sân bay và hỗ trợ ổn định chỗ ở. Công ty theo dõi và hỗ trợ trong suốt thời gian làm việc.",
  },
] as const;

export const TRAINING = {
  intro:
    "Học viên học tập trung tại trung tâm và ở nội trú trong ký túc xá. Mục tiêu là đạt trình độ tiếng Nhật mà đơn hàng yêu cầu, đồng thời làm quen với nếp sinh hoạt và tác phong làm việc tại Nhật Bản.",
  classroom: [
    "Lớp học theo trình độ, sĩ số nhỏ để giáo viên theo sát từng người",
    "Giáo viên người Việt dạy nền tảng, giáo viên người Nhật luyện giao tiếp",
    "Học cả kiến thức chăm sóc cơ bản và từ vựng chuyên ngành điều dưỡng",
    "Luyện phỏng vấn với cơ sở tiếp nhận trước mỗi kỳ tuyển",
  ],
  dormitory: [
    "Ký túc xá trong khuôn viên trung tâm, đi bộ tới lớp",
    "Phòng ở nhiều người, có bếp ăn chung và khu sinh hoạt",
    "Có nội quy giờ giấc giống môi trường làm việc tại Nhật",
    "Hoạt động ngoại khóa theo mùa: lễ hội, ngắm hoa, thư pháp",
  ],
} as const;
