"""
Intent Classifier — Sprint 2
Phân loại câu hỏi của user thuộc nhóm nào.
"""
from app.rag.taxonomy import normalize_text

INTENT_PATTERNS = {
    "chi_phi": [
        "chi phí", "học phí", "tổng phí", "giá đơn",
        "đặt cọc", "phí", "vay", "trả góp", "khoản",
        "hoàn tiền", "trả lại tiền", "phỏng vấn không đỗ"
    ],
    "dieu_kien": [
        "điều kiện", "yêu cầu", "cần gì", "tiêu chuẩn",
        "bằng cấp", "tuổi", "sức khỏe", "kinh nghiệm"
    ],
    "quy_trinh": [
        "quy trình", "các bước", "thủ tục", "làm thế nào",
        "như thế nào", "bắt đầu", "đăng ký", "hồ sơ"
    ],
    "luong_thuong": [
        "lương", "thu nhập", "kiếm được", "tiền lương",
        "trợ cấp", "phụ cấp", "thu nhập"
    ],
    "thoi_gian": [
        "bao lâu", "thời gian", "mấy tháng", "mấy năm",
        "khi nào", "lịch", "thời hạn", "xuất cảnh", "được bay"
    ],
    "cong_viec": [
        "công việc", "làm những gì", "làm gì", "vất vả",
        "hộ lý", "điều dưỡng làm"
    ],
    "phong_van": [
        "phỏng vấn", "thi tuyển", "không đỗ", "trượt phỏng vấn"
    ],
    "hoc_tap": [
        "học tiếng", "lớp học", "tiếng nhật", "trung tâm học",
        "thời gian học", "học viên", "hỗ trợ"
    ],
    "ky_tuc_xa": [
        "ký túc xá", "kí túc xá", "chỗ ở", "nơi ở"
    ],
    "booking": [
        "đặt lịch", "hẹn lịch", "lịch tư vấn", "hẹn tư vấn",
        "đặt hẹn", "gọi lại cho tôi", "gọi cho tôi"
    ],
    "lead": [
        "tư vấn", "liên hệ", "muốn đi",
        "quan tâm", "muốn tham gia", "apply"
    ],
    "chung": []
}

# Khi nhiều nhóm có cùng điểm, ưu tiên ý định cụ thể hơn các từ khóa chung
# như "đăng ký", "như thế nào" hoặc "thời gian".
INTENT_PRIORITY = [
    "booking",
    "lead",
    "ky_tuc_xa",
    "hoc_tap",
    "phong_van",
    "chi_phi",
    "dieu_kien",
    "luong_thuong",
    "cong_viec",
    "thoi_gian",
    "quy_trinh",
    "chung",
]

# Tạo bản không dấu của keywords để match
INTENT_PATTERNS_NODIAC = {
    intent: [normalize_text(kw) for kw in keywords]
    for intent, keywords in INTENT_PATTERNS.items()
}

def classify(query: str) -> str:
    query_normalized = normalize_text(query)
    scores = {intent: 0 for intent in INTENT_PATTERNS}

    for intent, keywords in INTENT_PATTERNS_NODIAC.items():
        for keyword in keywords:
            if keyword in query_normalized:
                scores[intent] += 1

    best_intent = max(
        INTENT_PRIORITY,
        key=lambda intent: scores[intent],
    )

    if scores[best_intent] == 0:
        return "chung"

    print(f"[IntentClassifier] '{query}' → {best_intent} (score: {scores[best_intent]})")
    return best_intent
