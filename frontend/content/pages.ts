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

/**
 * Điều kiện **mức nền của chương trình** — không phải điều kiện của một đơn cụ thể.
 *
 * Sửa ngày 24/09/2026 cho khớp trang điều kiện chính thức của công ty
 * (`xklddieuduong.vn/?product=dieu-kien-di-nhat-o-don-hang-dieu-duong`). Bản cũ
 * lấy yêu cầu của một đơn diện kỹ năng đặc định rồi trình bày như mức chung, và
 * hai dòng sai theo hướng nguy hiểm nhất: **loại oan người đủ điều kiện**.
 *
 * Dòng bằng cấp ghi "Trung cấp Điều dưỡng trở lên" trong khi công ty không yêu
 * cầu bằng cấp. Một người không có bằng đọc trang này sẽ tự loại mình rồi bỏ đi
 * — mất khách vì chính trang giới thiệu của mình.
 *
 * Dòng sức khỏe ghi "13 nhóm bệnh theo Bộ Y tế" thì không có nguồn nào: công ty
 * nêu ba bệnh truyền nhiễm cụ thể, không nhắc tới danh mục nào của Bộ Y tế.
 *
 * Mỗi đơn vẫn có điều kiện riêng chặt hơn mức nền này, và trang chi tiết đơn
 * hiện đúng điều kiện của đơn đó.
 */
export const CONDITIONS = [
  {
    criterion: "Độ tuổi",
    requirement: "18 đến 40 tuổi, cả nam và nữ",
    note: "Từng đơn hàng có khoảng tuổi riêng hẹp hơn, xem điều kiện từng đơn",
  },
  {
    criterion: "Bằng cấp",
    requirement: "Không yêu cầu bằng cấp",
    note: "Có bằng y, điều dưỡng hoặc dược là một lợi thế. Một số đơn hàng yêu cầu bằng cụ thể",
  },
  {
    criterion: "Tiếng Nhật",
    requirement: "Chưa biết tiếng vẫn đăng ký được",
    note: "Học tại trung tâm trước khi bay. Từng đơn yêu cầu N5 đến N3 tùy diện chương trình",
  },
  {
    criterion: "Sức khỏe",
    requirement: "Khỏe mạnh, không nhiễm bệnh truyền nhiễm",
    note: "Viêm gan B, HIV, bệnh lao là những bệnh không đủ điều kiện. Khám tại bệnh viện được chỉ định mới có kết luận",
  },
  {
    criterion: "Ngoại hình",
    requirement: "Không yêu cầu chiều cao, cân nặng",
    note: "Mắt cận đeo kính vẫn đi được",
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
    requirement: "Không yêu cầu kinh nghiệm",
    note: "Một số đơn lương cao yêu cầu từ một đến hai năm chăm sóc",
  },
] as const;

/**
 * Chi phí — ba chặng đóng tiền, tổng 90 triệu.
 *
 * Viết lại ngày 28/09/2026 theo đúng trang chi phí chính thức của công ty
 * (`xklddieuduong.vn/?product=chi-phi-di-don-dieu-duong-tron-goi-la-90-trieu`).
 *
 * Bản cũ toàn chữ chung chung — "Theo hợp đồng", "Theo khóa học" — trong khi
 * công ty nói thẳng từng con số. Người đọc rời trang mà vẫn không biết mình phải
 * chuẩn bị bao nhiêu, đúng câu hỏi họ vào đây để tìm.
 *
 * Bản cũ còn có một dòng sai hẳn: "Khám sức khỏe · Khoảng 1 triệu đồng · Đóng
 * trực tiếp cho bệnh viện". Công ty ghi rõ *"công ty sẽ đưa đi khám không mất
 * tiền"*. Con số 1 triệu ấy không có nguồn nào, và nó sai theo hướng tệ nhất:
 * dọa người ta bằng một khoản họ không phải trả.
 */
export const COSTS = [
  {
    item: "1. Khi đăng ký — đặt cọc",
    amount: "10 triệu đồng",
    when: "Lúc nộp hồ sơ đăng ký đơn",
    note: "Phỏng vấn không đỗ thì công ty trả lại luôn. Đỗ thì tính vào chi phí đã đóng",
  },
  {
    item: "2. Khi nhập học tiếng Nhật",
    amount: "35 triệu đồng",
    when: "Lúc bắt đầu khóa học tại trung tâm",
    note: "Khóa học kéo dài 6–7 tháng, học hết 50 bài",
  },
  {
    item: "3. Trước khi xuất cảnh",
    amount: "45 triệu đồng",
    when: "Sau khi có visa, trước ngày bay",
    note: "Được nợ lại và sang Nhật làm trả sau, trong 8 tháng",
  },
  {
    item: "Tổng cộng",
    amount: "90 triệu đồng",
    when: "Chia làm ba chặng như trên",
    note: "Công ty cấp hồ sơ vay vốn, vay dưới 100 triệu từ Ngân hàng chính sách địa phương",
  },
  {
    item: "Khám sức khỏe",
    amount: "Không mất tiền",
    when: "Trước khi phỏng vấn",
    note: "Công ty đưa đi khám tại bệnh viện được chỉ định",
  },
  {
    item: "Hộ chiếu, visa, lý lịch tư pháp",
    amount: "Theo mức phí nhà nước",
    when: "Sau khi có kết quả trúng tuyển",
    note: "Đóng theo biên lai của cơ quan cấp",
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
      "Công ty đưa đi khám tại bệnh viện được chỉ định, không mất tiền. Có kết quả mới nộp hồ sơ vào đơn hàng.",
  },
  {
    title: "Nhập học tiếng Nhật",
    // Công ty ghi "học hết 50 bài tiếng Nhật mất 6-7 tháng". Bản cũ ghi "4 đến 8
    // tháng" — một khoảng tôi tự đặt, rộng hơn thực tế ở cả hai đầu.
    duration: "6 đến 7 tháng",
    detail:
      "Học tập trung tại trung tâm, sáng và chiều, tối tự ôn. Học từ thứ Hai đến thứ Bảy, cuối tháng nghỉ 3–4 ngày. Có ký túc xá.",
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
