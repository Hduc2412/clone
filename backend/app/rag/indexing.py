"""Cách dựng đoạn chữ đem đi nhúng vector.

Một hàm, một dòng — nhưng phải nằm ở đây, vì **hai nơi cùng nhúng kho tri thức**:
`ingestion/embedder.py` lúc thu thập bài mới, và `ingestion/clean_knowledge.py`
lúc dọn rác rồi nhúng lại.

Hai nơi đó đã từng lệch nhau thật, và lệch âm thầm. Bản thu thập nhúng
`tiêu đề + thân bài`, bản dọn rác chỉ nhúng thân bài. Hậu quả không phải là một
lỗi nổ ra, mà là **kho tri thức có hai loại vector khác nhau nằm lẫn lộn**: bài
nào mới thu thập thì mang tiêu đề, bài nào từng dọn rác thì không. Tìm kiếm vẫn
chạy, điểm vẫn ra, chỉ là không bài nào so được công bằng với bài nào.

Gom về một hàm để hai nơi không thể lệch được nữa. Cùng lý do với `TASK_DOCUMENT`
trong `app/llm/gemini.py` — cũng là một chỗ hai bên từng làm khác nhau.

## Vì sao ghép tiêu đề vào

Tiêu đề là câu tóm tắt ngắn nhất của bài, và người hỏi rất hay hỏi gần đúng tiêu
đề: "Quy trình đóng phí đơn điều dưỡng như thế nào?" cho bài tên "Quy trình đóng
phí đơn điều dưỡng". Bỏ tiêu đề ra thì câu hỏi đó không còn gì để bấu vào.

Đo trên hai câu thật thì ghép tiêu đề **không phải lúc nào cũng có lợi**: câu hỏi
theo tiêu đề được thêm 0,019, còn câu hỏi về một chi tiết bên trong bài thì mất
0,013. Nên lý do giữ cách này là **nhất quán**, không phải vì nó luôn cho điểm
cao hơn.
"""


def text_for_embedding(title: str, chunk: str) -> str:
    """Đoạn chữ thật sự đem đi nhúng: tiêu đề, xuống dòng, rồi nội dung."""
    title = (title or "").strip()
    chunk = (chunk or "").strip()
    if not title:
        return chunk
    return f"{title}\n{chunk}"
