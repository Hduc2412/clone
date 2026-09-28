"""Danh mục khóa học tiếng Nhật — dữ liệu thật, không phải dữ liệu mẫu.

Khác hẳn `job_orders_seed.py`: file kia là mười chín đơn bịa ra để demo bộ lọc.
File này chỉ có **một dòng**, và dòng đó là khóa học thật của trung tâm, mỗi ô
truy được về một nguồn cụ thể.

## Từng ô lấy từ đâu

| Ô | Giá trị | Nguồn |
|---|---|---|
| `months_min`/`months_max` | 6–7 tháng | trang *Học tiếng Nhật khó không – Bao lâu được Bay*: "học hết 50 bài tiếng Nhật mất 6-7 tháng" |
| `tuition_vnd` | 35.000.000 | trang *Quy trình đóng phí*: "Nhập học đóng thêm 35 triệu" |
| `package_total_vnd` | 90.000.000 | cùng trang: 10 đăng ký + 35 học tiếng + 45 xuất cảnh |
| `format` | tập trung, sáng + chiều, thứ 2–7 | trang *Học tiếng Nhật khó không* |
| `level_to` | N4 | **chủ đầu tư chốt miệng ngày 24/09**, không có trang nào ghi |

Ô cuối là ô cần chú ý. Tôi đã tra cả ba mươi hai đoạn trong kho tri thức: chuỗi
`N1`…`N5` và `JLPT` **không xuất hiện một lần nào**. Nên `level_to` ghi nguồn là
`chu_dau_tu` chứ không phải `kho_tri_thuc` — để sau này ai đọc lại còn biết con số
này không có trang web nào đỡ lưng, và hỏi lại được khi cần.

## Vì sao giữ cả `package_total_vnd`

35 triệu **không phải học phí độc lập**, nó là một chặng của tổng 90 triệu. Nói
"học phí 35 triệu" trơ trọi là để khách hiểu sai số tiền phải chuẩn bị. Phần tư
vấn bắt buộc nêu cả tổng, và nó chỉ nêu được nếu bảng giữ con số ấy.
"""
from typing import Any


NGUON_THOI_GIAN = "https://xklddieuduong.vn/?product=hoc-tieng-nhat-kho-khong-bao-lau-duoc-bay"
NGUON_CHI_PHI = "https://xklddieuduong.vn/?product=chi-phi-di-don-dieu-duong-tron-goi-la-90-trieu"


COURSES: list[dict[str, Any]] = [
    {
        "code": "KH-0001",
        "title": "Học tiếng Nhật tại trung tâm",
        "level_from": "chua_hoc",
        "level_to": "N4",
        "months_min": 6,
        "months_max": 7,
        "tuition_vnd": 35_000_000,
        "package_total_vnd": 90_000_000,
        "format": (
            "Học tập trung tại trung tâm, sáng và chiều, tối tự ôn. "
            "Học từ thứ Hai đến thứ Bảy, cuối tháng nghỉ 3–4 ngày. Có ký túc xá."
        ),
        "curriculum": "Minna no Nihongo Sơ cấp, hết 50 bài",
        "status": "published",
        "source_url": NGUON_THOI_GIAN,
        "source_note": (
            "Thời gian và hình thức học: trang “Học tiếng Nhật khó không – Bao lâu "
            f"được Bay” ({NGUON_THOI_GIAN}). "
            "Học phí 35 triệu và tổng gói 90 triệu: trang “Quy trình đóng phí đơn "
            f"điều dưỡng” ({NGUON_CHI_PHI}). "
            "Trình độ đạt được N4: chủ đầu tư chốt ngày 24/09/2026 — kho tri thức "
            "không ghi trình độ ở bất cứ đâu."
        ),
        # Ghi rõ từng ô lấy ở đâu, để màn hình quản trị hiện được và để người sau
        # biết ô nào có trang web đỡ lưng, ô nào chỉ có lời người nói.
        "source_fields": {
            "months_min": "kho_tri_thuc",
            "months_max": "kho_tri_thuc",
            "tuition_vnd": "kho_tri_thuc",
            "package_total_vnd": "kho_tri_thuc",
            "format": "kho_tri_thuc",
            "curriculum": "kho_tri_thuc",
            "level_to": "chu_dau_tu",
        },
    },
]
