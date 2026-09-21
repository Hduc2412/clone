# Đặc tả API quản lý kho tri thức

**Gửi:** người phát triển chatbot và pipeline RAG
**Từ:** phần nghiệp vụ (đơn tuyển dụng, hồ sơ ứng viên, đối chiếu)
**Ngày:** 17/09/2026

Tài liệu này đặc tả **một chiều duy nhất**: những gì màn hình *Tri thức AI* bên
quản trị cần từ phía bạn. Chiều ngược lại — toàn bộ endpoint `/public/*` mà phần
nghiệp vụ mở ra cho khung chat — nằm ở `TICH_HOP_VOI_CHATBOT.md` §4, đã cập nhật
đường dẫn thật, không chép lại ở đây.

---

## 1. Vì sao cần

`admin-frontend/app/admin/knowledge/page.tsx` hiện là một trang **số liệu viết
cứng**. Nguyên văn trong mã nguồn:

```tsx
const topics = [ ["Chi phí", 1], ["Quy trình", 3], ["Điều kiện", 1], … ];
…
["32", "Bài viết đã lập chỉ mục", "Đủ nội dung từ ảnh"],
["10", "Nhóm chủ đề", "Taxonomy đang sử dụng"],
["0", "Nguồn thiếu ảnh", "Kiểm tra nghiêm ngặt đạt"],
```

Ba con số ấy đúng vào ngày ai đó gõ chúng vào. Chúng không đọc Qdrant, không đọc
MongoDB, và không đổi khi bạn nạp thêm tài liệu. Hệ quả thực tế: nếu trong buổi
bảo vệ có người bấm vào màn hình này rồi hỏi "số này lấy ở đâu", câu trả lời
trung thực là "không ở đâu cả".

Đây là phần thuộc pipeline RAG nên tôi không tự làm. Tôi chỉ nêu rõ cần gì để
khi bạn làm xong thì bên tôi ráp vào mất một buổi.

**Nếu bạn không kịp thì không sao.** Tôi sẽ để màn hình ở trạng thái rỗng kèm câu
"chưa nối dữ liệu thật", đúng hơn là để số giả. Không phần nào khác của hệ thống
phụ thuộc vào năm endpoint này.

---

## 2. Quy ước chung

| Việc | Dùng cái có sẵn |
|---|---|
| Xác thực | `get_current_user` trong `app/auth/security.py` |
| Phân quyền | `require_roles("admin", "manager")` — nhân viên tư vấn chỉ cần đọc |
| Nhật ký | `audit_action(...)` với `target_type="knowledge_document"` |
| Index MongoDB | khai trong `app/db/indexes.py` như các module khác |
| File gốc | `storage/kb/`, đã nằm trong `.gitignore` |
| Tiền tố router | `/knowledge` |

Lỗi trả theo đúng lối hiện hành: mã HTTP chuẩn, thân là `{"detail": "câu tiếng
Việt"}`. Giao diện quản trị in thẳng `detail` ra cho người dùng, nên câu đó phải
đọc được, không phải tên biến.

Mọi mốc thời gian trả về **kèm múi giờ** (`2026-09-17T14:40:12Z` hoặc
`+07:00`). Bỏ hậu tố đi thì trình duyệt hiểu là giờ địa phương và mọi mốc hiển
thị lệch 7 tiếng — lỗi này đã xảy ra một lần ở phần nghiệp vụ, mất nửa buổi để
tìm ra, sửa bằng `AsyncIOMotorClient(..., tz_aware=True)` trong
`app/db/database.py`.

---

## 3. Năm endpoint

### 3.1. `GET /knowledge/stats`

Ba thẻ số ở đầu màn hình và biểu đồ phân bố chủ đề.

```jsonc
{
  "collection": "xkld_knowledge",
  "collection_version": "xkld_knowledge_v20260730",
  "documents_total": 32,
  "documents_indexed": 32,
  "documents_failed": 0,
  "chunks_total": 187,
  "vectors_total": 187,
  "missing_image_content": 0,
  "by_topic": {
    "chi_phi": 1, "quy_trinh": 3, "dieu_kien": 1, "luong_thuong": 3,
    "cong_viec": 2, "phong_van": 1, "thoi_gian": 2, "hoc_tap": 14,
    "ky_tuc_xa": 3, "chung": 2
  },
  "last_indexed_at": "2026-07-30T09:12:44Z"
}
```

`by_topic` phải khóa theo **mã** chủ đề, không phải nhãn hiển thị. Mười mã hợp lệ
nằm trong `VALID_TOPICS` ở `app/rag/taxonomy.py`; giao diện tự dịch sang tiếng
Việt. Trả nhãn "Chi phí" thì mỗi lần đổi cách viết hoa là giao diện hỏng một chỗ.

`documents_total` đếm **bài viết**, `chunks_total` đếm **đoạn**. Hai con số này
khác nhau hẳn một bậc và trộn lẫn chúng là cách chắc chắn để báo cáo sai. Nếu
`vectors_total` lệch `chunks_total` thì có đoạn nhúng hỏng — giao diện sẽ bật
cảnh báo chỗ đó, nên đừng làm tròn cho bằng nhau.

### 3.2. `GET /knowledge/documents`

Bảng danh sách. Tham số lọc: `topic`, `status`, `q` (tìm trong tiêu đề),
`limit` (mặc định 100, tối đa 500).

```jsonc
{
  "items": [
    {
      "id": "KB-7F3A21",
      "title": "Chi phí đi Nhật ngành điều dưỡng 2026",
      "source": "crawl",            // crawl | upload
      "url": "https://…/chi-phi-di-nhat",
      "topic": "chi_phi",
      "section": "chi_phi",
      "status": "indexed",          // pending | indexing | indexed | failed
      "chunk_count": 6,
      "image_content_included": true,
      "content_length": 8421,
      "error": null,
      "created_at": "2026-07-30T09:10:02Z",
      "indexed_at": "2026-07-30T09:12:44Z"
    }
  ],
  "count": 32
}
```

Bốn trạng thái, không gộp: `pending` (đã nhận, chưa xử lý), `indexing` (đang
chạy), `indexed` (xong), `failed` (hỏng, `error` nói vì sao). Gộp `pending` với
`failed` thành "chưa xong" thì người trực không phân biệt được "chờ thêm hai
phút" với "phải vào sửa".

`image_content_included` giữ nguyên tên vì đó là khóa payload bạn đang ghi trong
`ingestion/embedder.py`. Nó tương ứng với thẻ "nguồn thiếu ảnh" trên màn hình:
nhiều bài trên trang nguồn đặt bảng giá trong ảnh, đoạn nào không đọc được ảnh là
đoạn trả lời thiếu số.

### 3.3. `POST /knowledge/documents`

`multipart/form-data`, khóa file là `file`, kèm `title` và `topic` tùy chọn.
Nhận PDF, DOCX, TXT, MD. Trả **202** ngay, xử lý nền — nhúng một tài liệu dài
mất hàng chục giây, giữ kết nối chờ là giao diện treo.

```jsonc
{ "id": "KB-9C1B07", "status": "pending" }
```

Giao diện sẽ hỏi lại `GET /knowledge/documents/{id}` mỗi vài giây cho tới khi
trạng thái rời `pending`/`indexing`. Nếu tiến trình nền chết vì máy chủ khởi động
lại, xin cho trạng thái chuyển sang `failed` sau một ngưỡng thời gian thay vì
treo ở `indexing` vĩnh viễn; phần đọc CV bên tôi đặt ngưỡng 10 phút và đã đủ.

Từ chối file quá `MAX_UPLOAD_MB` bằng **413**, sai định dạng bằng **415**.

### 3.4. `POST /knowledge/documents/{id}/reindex`

Nhúng lại một tài liệu, ví dụ sau khi bạn đổi cách chia đoạn. Trả **202** cùng
hình dạng như trên.

### 3.5. `DELETE /knowledge/documents/{id}`

Xóa bản ghi, file gốc, **và mọi điểm vector mang `document_id` đó**. Trả **204**.

Chỗ này là điểm dễ sót nhất của cả năm endpoint: xóa bản ghi MongoDB mà để lại
vector trong Qdrant thì tài liệu biến mất khỏi màn hình nhưng **chatbot vẫn trích
dẫn nó**. Một bảng giá đã gỡ vẫn được đọc cho khách nghe, và không ai tra ra được
vì trên giao diện nó không còn tồn tại.

---

## 4. Ràng buộc payload Qdrant — xin giữ nguyên

Phần truy xuất và khung chat đang đọc thẳng những khóa này trong
`app/rag/retriever.py`, `app/rag/prompt_builder.py`, `app/services/chat_service.py`:

| Khóa | Ai đọc | Hỏng ra sao nếu đổi tên |
|---|---|---|
| `text` | `prompt_builder` | Ngữ cảnh rỗng, bot từ chối mọi câu |
| `title` | `prompt_builder`, khung chat | Nguồn hiện ra không có tên |
| `url` | `chat_service`, khung chat | **Mất liên kết nguồn** — khách không kiểm chứng được |
| `image` | `chat_service` | Thẻ nguồn mất ảnh |
| `topic` | `retriever._topic_of`, lọc theo ý định | Lọc theo chủ đề hỏng, trả nhầm chủ đề |
| `section` | `infer_topic` khi thiếu `topic` | Dữ liệu cũ mất đường suy ra chủ đề |

Thêm khóa mới thì thoải mái. Tôi đề nghị thêm đúng một khóa: **`document_id`**,
để xóa và nhúng lại có thứ để bám. Hiện không có khóa nào nối một điểm vector về
bản ghi tài liệu, nên §3.5 chưa làm sạch được nếu thiếu nó.

Hai thứ khác cũng xin giữ nguyên vì phần nghiệp vụ đang dựa vào:

- Trường `intent` trên collection `messages` — phiếu tóm tắt tư vấn thống kê ứng
  viên đã hỏi những chủ đề nào.
- Khóa `url` trong mảng `sources` trả về cho khung chat.

---

## 5. Luồng staging đã có, nên giữ

`ingestion/embedder.py` đã dựng sẵn lối an toàn: nạp vào
`{QDRANT_COLLECTION_NAME}_staging` rồi mới chuyển sang collection đang phục vụ.
Endpoint upload nên đi theo lối đó thay vì ghi thẳng vào collection đang chạy —
một lần nhúng hỏng giữa chừng sẽ không làm chatbot trả lời sai trong lúc đang có
khách.

Nếu luồng staging được phơi ra API thì bên tôi thêm được hai nút "Kiểm thử bản
nháp" và "Đưa vào phục vụ" trên màn hình; nhưng đó là phần thêm, không phải điều
kiện.

---

## 6. Hai việc đã biết, thuộc phần bạn

Nêu ở đây cho đủ, vì chúng ảnh hưởng thẳng tới chất lượng câu trả lời chứ không
chỉ tới màn hình quản trị. Cả hai đã báo trong `BAO_CAO_GUI_NHOM_CHATBOT.md` §7:

1. **Mười sáu chỗ sai số điện thoại** trong kho tri thức. Bộ kiểm tra câu trả lời
   đang phải chặn hậu kiểm, nghĩa là mô hình vẫn đọc dữ liệu sai rồi mới bị gạt.
2. **Hai mươi hai trên ba mươi hai đoạn** còn rác nhận dạng ảnh. Đây chính là con
   số mà thẻ "nguồn thiếu ảnh" trên màn hình sẽ phơi ra khi nối dữ liệu thật —
   không phải `0` như đang viết cứng.

---

## 7. Nghiệm thu

Bên tôi coi là xong khi cả bốn điều dưới đây đúng:

1. Mở `/admin/knowledge`, ba thẻ số khớp với số đếm thật trong Qdrant.
2. Tải lên một PDF, màn hình tự chuyển `pending` → `indexed` mà không cần F5.
3. Xóa tài liệu vừa tải, rồi hỏi chatbot đúng nội dung trong đó — **không** còn
   trích dẫn nó nữa.
4. Ngắt Qdrant, mở lại màn hình: hiện lỗi đọc được, không phải trang trắng.
