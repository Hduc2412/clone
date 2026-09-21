"""Sáu hồ sơ ứng viên mẫu dùng để kiểm thử phần đọc CV.

Doanh nghiệp chưa cung cấp CV thật, và CV thật thì chứa thông tin cá nhân nên
không đưa vào repo được. Bộ mẫu này viết ra để **kiểm thử bộ đọc hồ sơ và bộ đối
chiếu**, nên từng hồ sơ được chọn để rơi vào một tình huống khác nhau chứ không
phải sáu hồ sơ na ná nhau:

| Hồ sơ | Tình huống cần kiểm |
|---|---|
| Mai | Trường hợp thuận: đủ mọi điều kiện, đúng nguyện vọng Tokyo |
| Hùng | Trình độ cao, hợp diện EPA; kiểm bậc tiếng Nhật và bằng đại học |
| Hoa | Chưa học tiếng Nhật, chỉ hợp đơn N5; kiểm `chua_hoc` thấp hơn N5 |
| Tuấn | Ba mươi tám tuổi, kiểm việc loại theo khoảng tuổi |
| Lan | **Thiếu năm sinh**, kiểm nhánh CHƯA RÕ không được loại đơn |
| Ngọc | Ghi "N4 trở lên, đang ôn N3", kiểm chuỗi nhiều mức không bị đọc thành N3 |

Mỗi hồ sơ còn đi kèm `expected` — những gì bộ đọc phải rút ra đúng. Đó là đáp án
để chấm, không phải dữ liệu đầu vào.
"""

SAMPLE_CVS: list[dict] = [
    {
        "slug": "01_nguyen_thi_mai",
        "format": "pdf",
        "layout": "chuan",
        "note": "CV một cột, bố cục sạch. Trường hợp dễ nhất.",
        "content": {
            "full_name": "NGUYỄN THỊ MAI",
            "title": "Điều dưỡng viên",
            "contact": [
                "Ngày sinh: 12/03/2003",
                "Giới tính: Nữ",
                "Điện thoại: 0912 345 678",
                "Email: mai.nguyen03@gmail.com",
                "Địa chỉ: Xã Đông Hưng, huyện Đông Hưng, tỉnh Thái Bình",
            ],
            "sections": [
                (
                    "MỤC TIÊU NGHỀ NGHIỆP",
                    [
                        "Mong muốn sang Nhật Bản làm việc trong lĩnh vực chăm sóc người cao tuổi.",
                        "Nguyện vọng làm tại viện dưỡng lão khu vực Tokyo vì có người thân sinh sống tại đó.",
                    ],
                ),
                (
                    "HỌC VẤN",
                    [
                        "2021 - 2024: Cao đẳng Y tế Thái Bình",
                        "Chuyên ngành: Điều dưỡng. Xếp loại: Khá",
                    ],
                ),
                (
                    "TRÌNH ĐỘ TIẾNG NHẬT",
                    [
                        "Chứng chỉ JLPT N4, cấp tháng 07/2025",
                        "Đang tiếp tục học tại trung tâm tiếng Nhật",
                    ],
                ),
                (
                    "KINH NGHIỆM LÀM VIỆC",
                    [
                        "Chưa có kinh nghiệm làm việc chính thức.",
                        "08/2023 - 11/2023: Thực tập tại Bệnh viện Đa khoa tỉnh Thái Bình, khoa Nội.",
                    ],
                ),
                (
                    "KỸ NĂNG",
                    [
                        "Đo huyết áp, nhiệt độ, mạch cho người bệnh",
                        "Hỗ trợ vệ sinh cá nhân và cho người bệnh ăn uống",
                        "Sử dụng máy tính văn phòng cơ bản",
                    ],
                ),
            ],
        },
        "expected": {
            "full_name": "Nguyễn Thị Mai",
            "birth_year": 2003,
            "gender": "nu",
            "education_level": "cao_dang",
            "major": "Điều dưỡng",
            "japanese_level": "N4",
            "experience_years": 0,
            "care_experience": False,
            "phone": "0912345678",
            "desired_prefecture": "Tokyo",
            "desired_employer_type": "vien_duong_lao",
        },
    },
    {
        "slug": "02_tran_van_hung",
        "format": "pdf",
        "layout": "chuan",
        "note": "Trình độ cao, có kinh nghiệm lâm sàng. Hợp diện EPA.",
        "content": {
            "full_name": "TRẦN VĂN HÙNG",
            "title": "Cử nhân Điều dưỡng",
            "contact": [
                "Sinh ngày 05 tháng 09 năm 1999",
                "Giới tính: Nam",
                "SĐT: 0987.654.321",
                "Email: hungtran99@gmail.com",
                "Quê quán: Thành phố Nam Định",
            ],
            "sections": [
                (
                    "HỌC VẤN",
                    [
                        "2017 - 2021: Đại học Điều dưỡng Nam Định",
                        "Chuyên ngành Điều dưỡng đa khoa, tốt nghiệp loại Giỏi",
                    ],
                ),
                (
                    "NGOẠI NGỮ",
                    [
                        "Tiếng Nhật: chứng chỉ JLPT N3 (12/2024)",
                        "Tiếng Anh: giao tiếp cơ bản",
                    ],
                ),
                (
                    "KINH NGHIỆM",
                    [
                        "10/2021 - 09/2023: Điều dưỡng viên, Bệnh viện Đa khoa tỉnh Nam Định",
                        "Làm việc tại khoa Hồi sức tích cực, theo dõi và chăm sóc người bệnh nặng.",
                        "10/2023 - nay: Điều dưỡng viên, Trung tâm chăm sóc người cao tuổi Nhân Ái",
                        "Chăm sóc sinh hoạt hằng ngày cho người cao tuổi, hỗ trợ phục hồi chức năng.",
                    ],
                ),
                (
                    "NGUYỆN VỌNG",
                    [
                        "Mong muốn làm việc tại bệnh viện, khu vực Kansai.",
                        "Mức lương mong muốn từ 190.000 yên một tháng.",
                    ],
                ),
            ],
        },
        "expected": {
            "full_name": "Trần Văn Hùng",
            "birth_year": 1999,
            "gender": "nam",
            "education_level": "dai_hoc",
            "japanese_level": "N3",
            "experience_years": 4,
            "care_experience": True,
            "phone": "0987654321",
            "desired_employer_type": "benh_vien",
            "salary_expectation_jpy": 190000,
        },
    },
    {
        "slug": "03_le_thi_hoa",
        "format": "docx",
        "layout": "chuan",
        "note": "Chưa học tiếng Nhật. Chỉ hợp đơn thực tập sinh yêu cầu N5.",
        "content": {
            "full_name": "LÊ THỊ HOA",
            "title": "Hồ sơ xin việc",
            "contact": [
                "Năm sinh: 2007",
                "Giới tính: Nữ",
                "Số điện thoại: 0356 789 012",
                "Địa chỉ: huyện Yên Thành, tỉnh Nghệ An",
            ],
            "sections": [
                (
                    "TRÌNH ĐỘ HỌC VẤN",
                    [
                        "2022 - 2025: Trung cấp Y tế Nghệ An, ngành Điều dưỡng",
                    ],
                ),
                (
                    "NGOẠI NGỮ",
                    [
                        "Tiếng Nhật: chưa học.",
                        "Mong muốn được đào tạo tiếng Nhật trước khi xuất cảnh.",
                    ],
                ),
                (
                    "KINH NGHIỆM",
                    [
                        "Chưa đi làm.",
                    ],
                ),
                (
                    "NGUYỆN VỌNG",
                    [
                        "Đi Nhật Bản theo diện thực tập sinh ngành chăm sóc.",
                        "Không yêu cầu khu vực cụ thể, ưu tiên nơi chi phí thấp.",
                    ],
                ),
            ],
        },
        "expected": {
            "full_name": "Lê Thị Hoa",
            "birth_year": 2007,
            "gender": "nu",
            "education_level": "trung_cap",
            "japanese_level": "chua_hoc",
            "experience_years": 0,
            "care_experience": False,
            "phone": "0356789012",
        },
    },
    {
        "slug": "04_pham_minh_tuan",
        "format": "pdf",
        "layout": "bang",
        "note": "Bố cục bảng hai cột. Ba mươi tám tuổi, quá tuổi của phần lớn đơn.",
        "content": {
            "full_name": "PHẠM MINH TUẤN",
            "title": "Điều dưỡng viên",
            "contact": [
                "Ngày sinh: 22/11/1988",
                "Giới tính: Nam",
                "Điện thoại: +84 934 567 890",
                "Nơi ở hiện tại: quận Hải Châu, Đà Nẵng",
            ],
            "sections": [
                (
                    "HỌC VẤN",
                    [
                        "2008 - 2011: Cao đẳng Y tế Đà Nẵng, ngành Điều dưỡng",
                    ],
                ),
                (
                    "TIẾNG NHẬT",
                    ["JLPT N4, cấp tháng 12/2023"],
                ),
                (
                    "KINH NGHIỆM",
                    [
                        "2012 - 2017: Điều dưỡng viên, Bệnh viện Đà Nẵng",
                        "2017 - nay: Điều dưỡng trưởng ca, Viện dưỡng lão Bình An",
                        "Tổng cộng hơn 13 năm làm việc trong ngành chăm sóc.",
                    ],
                ),
                (
                    "NGUYỆN VỌNG",
                    [
                        "Mong muốn sang Nhật làm việc tại viện dưỡng lão.",
                        "Chấp nhận mọi khu vực.",
                    ],
                ),
            ],
        },
        "expected": {
            "full_name": "Phạm Minh Tuấn",
            "birth_year": 1988,
            "gender": "nam",
            "education_level": "cao_dang",
            "japanese_level": "N4",
            "experience_years": 13,
            "care_experience": True,
            "phone": "0934567890",
            "desired_employer_type": "vien_duong_lao",
        },
    },
    {
        "slug": "05_vu_thi_lan",
        "format": "pdf",
        "layout": "chuan",
        "note": "Thiếu năm sinh và giới tính. Kiểm nhánh CHƯA RÕ không loại đơn.",
        "content": {
            "full_name": "VŨ THỊ LAN",
            "title": "Sơ yếu lý lịch",
            "contact": [
                "Điện thoại: 0978 111 222",
                "Email: lanvu.dd@gmail.com",
                "Địa chỉ: thành phố Hải Dương",
            ],
            "sections": [
                (
                    "HỌC VẤN",
                    [
                        "Tốt nghiệp Cao đẳng Điều dưỡng, Trường Cao đẳng Y tế Hải Dương.",
                    ],
                ),
                (
                    "TIẾNG NHẬT",
                    ["Đã có chứng chỉ N4."],
                ),
                (
                    "KINH NGHIỆM",
                    [
                        "Hai năm làm điều dưỡng tại phòng khám tư nhân.",
                    ],
                ),
                (
                    "NGUYỆN VỌNG",
                    [
                        "Muốn làm ở khu vực Osaka.",
                    ],
                ),
            ],
        },
        "expected": {
            "full_name": "Vũ Thị Lan",
            "birth_year": None,
            "gender": None,
            "education_level": "cao_dang",
            "japanese_level": "N4",
            "experience_years": 2,
            "phone": "0978111222",
            "desired_prefecture": "Osaka",
        },
    },
    {
        "slug": "06_dang_thi_ngoc",
        "format": "pdf_scan",
        "layout": "chuan",
        "note": (
            "Bản scan, không có lớp chữ, phải nhận dạng bằng ảnh. "
            "Ghi 'N4 trở lên, đang ôn N3' để kiểm chuỗi nhiều mức."
        ),
        "content": {
            "full_name": "ĐẶNG THỊ NGỌC",
            "title": "Hồ sơ ứng tuyển điều dưỡng Nhật Bản",
            "contact": [
                "Ngày sinh: 30/06/2002",
                "Giới tính: Nữ",
                "Điện thoại: 0901 234 567",
                "Địa chỉ: huyện Kim Sơn, tỉnh Ninh Bình",
            ],
            "sections": [
                (
                    "HỌC VẤN",
                    [
                        "2020 - 2023: Cao đẳng Điều dưỡng, Trường Cao đẳng Y tế Ninh Bình",
                    ],
                ),
                (
                    "TIẾNG NHẬT",
                    [
                        "Trình độ hiện tại N4 trở lên, đang ôn thi N3 vào kỳ tháng 12.",
                    ],
                ),
                (
                    "KINH NGHIỆM",
                    [
                        "01/2024 - nay: Nhân viên chăm sóc, Trung tâm dưỡng lão Thiên Đức",
                        "Hỗ trợ ăn uống, vệ sinh và vận động cho người cao tuổi.",
                    ],
                ),
                (
                    "NGUYỆN VỌNG",
                    [
                        "Làm việc tại viện dưỡng lão, khu vực Kanto.",
                        "Chi phí có thể chuẩn bị khoảng 120 triệu đồng.",
                    ],
                ),
            ],
        },
        "expected": {
            "full_name": "Đặng Thị Ngọc",
            "birth_year": 2002,
            "gender": "nu",
            "education_level": "cao_dang",
            "japanese_level": "N4",
            "experience_years": 2,
            "care_experience": True,
            "phone": "0901234567",
            "desired_region_group": "kanto",
            "desired_employer_type": "vien_duong_lao",
            "budget_vnd": 120_000_000,
        },
    },
]
