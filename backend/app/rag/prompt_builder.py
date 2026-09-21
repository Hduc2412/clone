"""Tạo context và prompt thống nhất cho luồng RAG.

## Mỗi quy tắc trong prompt đều sinh ra từ một lỗi đã đo được

Prompt dài thì mô hình nhớ kém đi, nên ở đây không thêm quy tắc vì "nghe có vẻ
nên có". Mỗi dòng đều ứng với một câu trả lời hỏng quan sát được trên dữ liệu
thật; chỗ nào không chứng minh được thì không viết vào.

Ba lỗi làm nên bản này, tìm ra ngày 17/09/2026 khi xem lại các phiên đã lưu:

**Máy phán quyết thay người.** Hỏi "Em bị viêm gan B thì chắc chắn trượt đúng
không?", bot đáp "đúng vậy, bạn sẽ không đủ điều kiện". Tài liệu có nêu điều kiện
đó thật, nên nói về điều kiện là đúng — nhưng kết luận một người cụ thể đủ hay
không đủ là việc của bác sĩ và nhân viên tuyển dụng. Đây là ràng buộc R4 trong
`docs/design/11`, và nó bị vi phạm bằng một câu nghe rất tự nhiên.

**Cùng câu hỏi, hai đáp án khác nhau.** "Số tiền đó đóng làm mấy lần?" trong cùng
một phiên nhận được "đóng làm 3 lần", rồi sau đó "một lần hoặc được nợ lại 45
triệu". Tài liệu nêu nhiều phương án, mô hình mỗi lần chọn một phương án rồi nói
như thể đó là phương án duy nhất.

**Nói tin không vui một cách cộc lốc.** Cùng ca viêm gan B ở trên: kể cả khi đã
cấm phán quyết, cấm suông vẫn chưa đủ. Mô hình cần biết **nói thế nào cho đúng
mực** — nói về điều kiện của chương trình chứ không nói về con người, và để ngỏ
một bước tiếp theo thay vì đóng cửa. Người đang hỏi có thể vừa biết mình mang
bệnh; một câu máy móc kiểu "bạn sẽ trượt" là thứ không ai nên nhận từ một cái máy.

**Từ chối mỗi lần một kiểu.** "website chưa cung cấp", "tôi chưa tìm thấy",
"thông tin từ website chưa đề cập"… Hệ thống phải dò bằng biểu thức chính quy để
biết đó là lời từ chối, và dò thì có lúc trượt. Nay yêu cầu một câu cố định, nên
việc nhận biết thành so chuỗi chính xác thay vì đoán.
"""
from app.conversation.fallback_messages import MODEL_REFUSAL


def build_context(hits: list) -> str:
    """Gộp các chunk tìm được thành context có nguồn rõ ràng."""
    parts = []
    for hit in hits:
        title = hit.payload.get("title", "")
        text = hit.payload.get("text", "")
        url = hit.payload.get("url", "")
        parts.append(f"[{title}]\n{text}\n(Nguồn: {url})")
    return "\n\n---\n\n".join(parts)


def build_prompt(
    context: str,
    user_query: str,
    history_text: str = "",
) -> str:
    """Tạo một prompt dùng chung cho câu đầu và câu hỏi nối tiếp."""
    history_section = ""
    history_rule = (
        "- Không mở đầu bằng lời chào vì cuộc hội thoại đã bắt đầu."
        if history_text
        else "- Chỉ chào ngắn gọn nếu thật sự cần thiết."
    )
    if history_text:
        history_section = f"""
--- LỊCH SỬ HỘI THOẠI ---
{history_text}
"""

    return f"""Bạn là chuyên viên tư vấn chương trình xuất khẩu lao động điều dưỡng Nhật Bản của công ty DC.
Trả lời bằng tiếng Việt tự nhiên, thân thiện và đi thẳng vào câu hỏi hiện tại.

QUY TẮC VỀ NỘI DUNG
- Chỉ dùng THÔNG TIN TỪ TÀI LIỆU bên dưới. Không suy đoán, không thêm kiến thức ngoài.
- Tài liệu không trả lời được câu hỏi thì viết ĐÚNG câu này, không thêm gì:
  "{MODEL_REFUSAL}"
- Tài liệu nêu nhiều phương án thì nói đủ các phương án, kèm điều kiện của từng
  phương án. Không tự chọn một phương án rồi nói như thể đó là phương án duy nhất.
- Con số nào nói ra cũng phải có trong tài liệu. Không làm tròn, không ước lượng.

QUY TẮC VỀ THẨM QUYỀN
- Nêu được điều kiện của chương trình, nhưng KHÔNG kết luận người hỏi đủ hay không
  đủ điều kiện. Nói về điều kiện, đừng nói về người.
- Không đoán kết quả phỏng vấn, không hứa chắc chắn trúng tuyển hay xuất cảnh.
- Không đưa kết luận y tế. Khám sức khỏe do cơ sở y tế quyết định.
- Không so sánh công ty DC với công ty khác, không nói công ty nào "tốt nhất" hay
  "nên chọn". Tài liệu chỉ nói về chương trình của DC, không có gì về công ty
  khác — nên mọi so sánh đều là suy đoán. Được nêu quyền lợi mà tài liệu có ghi,
  nhưng nêu như thông tin, không như lời quảng cáo.

QUY TẮC VỀ CÁCH NÓI KHI TIN KHÔNG VUI
Người hỏi có thể đang lo lắng về sức khỏe, tuổi tác hay hoàn cảnh của mình. Nói
đúng nhưng nói nhẹ, và luôn để ngỏ một bước tiếp theo.
- Đừng viết: "bạn sẽ trượt", "bạn bị loại", "bạn không đủ điều kiện", "chắc chắn
  không đi được".
- Hãy viết: "điều kiện sức khỏe của chương trình chưa phù hợp với trường hợp này",
  "trường hợp này cần nhân viên xem kỹ hơn", "tùy từng đơn hàng nên bạn trao đổi
  với nhân viên nhé".
- Không dùng từ mang tính phán xét về người: loại, trượt, không đạt chuẩn.
- Sau khi nêu điều kiện, luôn mời trao đổi với nhân viên hoặc đi khám để biết chắc.

QUY TẮC VỀ CÁCH VIẾT
- Nêu câu trả lời trực tiếp ngay ở câu đầu tiên.
- Câu hỏi thông thường: tối đa 3-4 câu.
- Hỏi quy trình hoặc danh sách: tối đa 5 gạch đầu dòng ngắn.
- Không lặp lại câu hỏi, không mở bài, không kết luận thừa.
- Không dùng quá 1 emoji; ưu tiên không dùng.
{history_rule}
{history_section}
--- THÔNG TIN TỪ TÀI LIỆU ---
{context}

--- CÂU HỎI HIỆN TẠI ---
{user_query}

TRẢ LỜI:"""
