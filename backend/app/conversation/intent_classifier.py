"""
Intent Classifier — Sprint 2
Phân loại câu hỏi của user thuộc nhóm nào.
"""
INTENT_PATTERNS = {
    "chi_phi": [
        "chi phí", "học phí", "tiền", "bao nhiêu", "giá",
        "đặt cọc", "phí", "vay", "trả góp", "khoản"
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
        "khi nào", "lịch", "thời hạn"
    ],
    "lead": [
        "đăng ký", "tư vấn", "liên hệ", "muốn đi",
        "quan tâm", "tham gia", "nộp hồ sơ", "apply"
    ],
    "chung": []  # fallback
}

def classify(query: str) -> str:
    """
    Trả về intent của câu hỏi.
    Nếu không khớp intent nào thì trả về 'chung'.
    """
    query_lower = query.lower()
    scores = {intent: 0 for intent in INTENT_PATTERNS}

    for intent, keywords in INTENT_PATTERNS.items():
        for keyword in keywords:
            if keyword in query_lower:
                scores[intent] += 1
      # Lấy intent có điểm cao nhất
    best_intent = max(scores, key=scores.get)

    # Nếu không khớp gì thì fallback
    if scores[best_intent] == 0:
        return "chung"             
    print(f"[IntentClassifier] '{query}' → {best_intent} (score: {scores[best_intent]})")
    return best_intent