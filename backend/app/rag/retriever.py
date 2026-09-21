from app.db.qdrant import get_qdrant_client, COLLECTION_NAME
from app.core.config import settings
from app.llm.gemini import create_embedding
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from app.rag.taxonomy import infer_topic

TOP_K = 5

# Sàn tuyệt đối: đoạn hợp nhất không vượt mức này thì coi như kho không có nội
# dung, và hệ thống từ chối.
#
# ## Sàn này KHÔNG quyết định được "câu hỏi có trả lời được không"
#
# Đo trên bộ 35 câu hỏi chuẩn, sau khi kho được nhúng lại đúng kiểu:
#
#     trong phạm vi (11 câu):  thấp nhất 0,6901   cao nhất 0,8004
#     ngoài phạm vi (24 câu):  thấp nhất 0,5814   cao nhất 0,7107
#
# **Hai vùng chồng lên nhau.** Câu "Anh đoán xem em có đỗ phỏng vấn không?" lấy
# về bài phỏng vấn với 0,7107 — rất gần nghĩa, nhưng kho không trả lời được câu
# đang hỏi. Không con số nào tách được hai nhóm đó, vì điểm đo độ gần nghĩa chứ
# không đo khả năng trả lời.
#
# Nên sàn chỉ làm đúng một việc nhỏ: chặn phần đuôi rõ ràng không liên quan
# ("giá bitcoin" 0,6134, "thời tiết Tokyo" 0,5935). Việc còn lại thuộc về quy
# tắc trong prompt — chỉ dùng thông tin từ kho, không đủ thì nói rõ là chưa có.
# Đo trên bộ câu hỏi cho thấy phần đó đang làm đúng.
#
# 0,65 nằm giữa hai mốc thật: dưới câu trong phạm vi thấp nhất 0,04 và trên câu
# ngoài phạm vi rõ ràng nhất 0,037. Đây là con số đo được trên kho hiện tại, kho
# đổi nhiều thì phải đo lại.
MIN_TOP_SCORE = settings.min_retrieval_score

# Dải tương đối: giữ những đoạn không thấp hơn đoạn đầu quá chừng này.
#
# Thay cho ngưỡng tuyệt đối cũ (0,65). Điểm của cả kho nằm gọn trong khoảng hẹp
# 0,56–0,73, nên một con số cố định cắt ngang giữa dải đó rất tùy tiện: cùng một
# câu hỏi, viết có dấu thì đoạn đúng được 0,72 và lọt, viết không dấu thì còn
# 0,64 và bị loại. Ca thật: "Quy trình đóng phí đơn điều dưỡng như thế nào?" —
# kho có đúng bài tên như vậy, nhưng gõ không dấu thì bài đó xếp hạng ba với
# 0,6423 và bị ngưỡng 0,65 cắt mất, nên bot trả lời là không có thông tin.
#
# So với đoạn đầu thì không còn phụ thuộc vào mức điểm tuyệt đối nữa.
RELATIVE_BAND = 0.06

# Giữ lại để tầng trên và phần thống kê còn biết mỗi ý định thuộc nhóm chủ đề
# nào. Không còn dùng để lọc hay để xếp hạng — lý do ở docstring của `search`.
INTENT_TO_TOPICS = {
    "chi_phi": ["chi_phi"],
    "quy_trinh": ["quy_trinh"],
    "dieu_kien": ["dieu_kien"],
    "luong_thuong": ["luong_thuong"],
    "cong_viec": ["cong_viec"],
    "phong_van": ["phong_van"],
    "thoi_gian": ["thoi_gian"],
    "hoc_tap": ["hoc_tap"],
    "ky_tuc_xa": ["ky_tuc_xa"],
    "lead": ["chi_phi", "quy_trinh", "dieu_kien"],
    "chung": [],
}


def _topic_of(hit) -> str:
    """Chủ đề của đoạn; suy ra cho dữ liệu cũ chưa gắn sẵn."""
    topic = hit.payload.get("topic")
    if not topic:
        topic = infer_topic(
            hit.payload.get("section", ""),
            hit.payload.get("title", ""),
        )
        hit.payload["topic"] = topic
    return topic


def select(points: list) -> list:
    """Chọn những đoạn đem vào ngữ cảnh, theo hai điều kiện đi cùng nhau.

    1. **Sàn tuyệt đối** — đoạn đầu phải vượt `MIN_TOP_SCORE`, nếu không thì trả
       về rỗng và tầng trên sẽ từ chối.
    2. **Dải tương đối** — giữ các đoạn không thấp hơn đoạn đầu quá `RELATIVE_BAND`.

    Phải có **cả hai**. Chỉ dùng dải tương đối thì câu ngoài phạm vi cũng lọt:
    hỏi "giá bitcoin hôm nay", tám đoạn đầu chênh nhau chưa tới 0,002 điểm, nên
    dải tương đối giữ lại cả tám và đưa cho mô hình một đống bài về xuất khẩu lao
    động để nó xoay xở — đúng tình huống dễ sinh ra câu bịa nhất.

    Hàm tách riêng và thuần để kiểm thử được mà không cần Qdrant lẫn mạng.
    """
    if not points:
        return []
    top = points[0].score
    if top < MIN_TOP_SCORE:
        return []
    return [point for point in points if point.score >= top - RELATIVE_BAND]


def search(query: str, intent: str = "chung") -> list:
    """Embed câu hỏi rồi lấy các đoạn gần nghĩa nhất trên toàn kho tri thức.

    Chủ đề suy ra từ ý định **không** tham gia vào việc chọn đoạn nữa, vì đo trên
    dữ liệu thật cho thấy nó chỉ làm hỏng kết quả:

    - Lọc cứng theo chủ đề: câu "Khi bắt đầu thì tiền cọc là bao nhiêu?" bị xếp
      vào `quy_trinh` chỉ vì hai chữ "bắt đầu", nên đoạn ghi rõ "đặt cọc 10 triệu"
      (chủ đề `chi_phi`) bị loại thẳng. Chatbot trả lời là tài liệu không nêu,
      trong khi kho tri thức có sẵn câu trả lời.
    - Cộng điểm thưởng cho đoạn đúng chủ đề: nhẹ tay hơn nhưng vẫn sai cùng kiểu.
      Phân loại sai thì phần thưởng đẩy nhầm đoạn lên đầu. Vẫn với câu trên,
      thưởng 0.04 đưa đoạn "Cách đăng ký" (0.679 → 0.719) vượt lên trên đoạn
      "Quy trình đóng phí" (0.706) là đoạn thật sự chứa con số.

    Trên bộ câu hỏi thử, xếp hạng thuần theo độ gần nghĩa chọn đúng đoạn ở **cả
    năm câu**, tốt hơn cả hai cách trên. Chừng nào bộ phân loại ý định còn nhầm
    thì mọi cách dùng nó để can thiệp vào xếp hạng đều khuếch đại cái nhầm đó.

    `intent` vẫn nhận vào để chữ ký hàm không đổi và để ghi log đối chiếu.
    """
    query_vector = create_embedding(query)
    if not query_vector:
        return []

    qdrant = get_qdrant_client()
    try:
        points = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=TOP_K,
        ).points
    except (ResponseHandlingException, UnexpectedResponse) as exc:
        print(f"[Qdrant] Search failed: {exc}")
        return []

    hits = select(points)
    for hit in hits:
        _topic_of(hit)

    if hits:
        wanted = set(INTENT_TO_TOPICS.get(intent, []))
        lech = [h.payload.get("topic") for h in hits[:1] if wanted and h.payload.get("topic") not in wanted]
        if lech:
            print(f"[Retriever] Ý định '{intent}' nhưng đoạn hợp nhất thuộc chủ đề '{lech[0]}'.")

    return hits
