# 07 — Thiết kế AI Pipeline

Hệ thống có **ba pipeline** độc lập, dùng chung tầng LLM và Vector Store.

---

## 1. Chat Pipeline (đồng bộ, p95 ≤ 6s)

```
User Input
   ↓
[1] Session Manager      lấy/tạo session, nạp 6 lượt gần nhất
   ↓
[2] Intent Classifier    10 nhóm intent
   ↓
[3] Entity Extractor     regex + LLM
   ↓
[4] Reference Resolver   giải "cái đó", "chỗ này" theo ngữ cảnh
   ↓
[5] RAG Retriever        embed → Qdrant → lọc score ≥ 0.65 → Top-4
   ↓
[6] Prompt Builder       system + context + history + question
   ↓
[7] Gemini Service       gọi LLM, retry 3 lần
   ↓
[8] Response Validator   kiểm tra bám nguồn, tính confidence
   ↓
[9] Post-Actions         lưu message, cập nhật profile, tạo lead nếu cần
   ↓
Output
```

### 1.1 Intent Classifier

10 nhóm: `CHI_PHI`, `DIEU_KIEN`, `QUY_TRINH`, `DON_HANG`, `HO_SO`, `VISA`,
`LUONG`, `DIA_DIEM`, `TIENG_NHAT`, `DANG_KY`. Thêm `CHUNG` cho câu ngoài phạm vi
và `CHAO_HOI` cho xã giao.

Chiến lược 2 tầng để tiết kiệm quota và giảm độ trễ:

1. **Tầng rule** — từ khóa và mẫu regex cho các câu rõ ràng
   (`bao nhiêu tiền`, `chi phí`, `học phí` → `CHI_PHI`). Bao phủ khoảng 60% lưu lượng
   thực tế, độ trễ gần bằng 0.
2. **Tầng LLM** — chỉ chạy khi tầng rule không chắc chắn. Gọi Gemini với
   `response_mime_type = application/json` và enum cố định, `temperature = 0`.

Trả về `{intent, confidence}`. Nếu `confidence < 0.5` → coi như `CHUNG`.

### 1.2 Entity Extractor

| Entity | Phương pháp | Chuẩn hóa |
|---|---|---|
| `phone` | Regex `(0\|\+84)(3\|5\|7\|8\|9)\d{8}` | Về dạng `0xxxxxxxxx` |
| `full_name` | LLM + heuristic sau "tên tôi là", "em là" | Hoa đầu từ |
| `japanese_level` | Regex `\bN[1-5]\b` + từ khóa "chưa học", "mất gốc" | Enum |
| `desired_location` | Đối chiếu danh mục 47 tỉnh Nhật Bản | Tên chuẩn |
| `age` / `birth_year` | Regex số + ngữ cảnh | Số nguyên |

Quy tắc hợp nhất: giá trị mới ghi đè giá trị cũ **trừ khi** giá trị cũ có
`source = user_confirmed` mà giá trị mới chỉ là `AI` suy ra.

### 1.3 RAG Retriever

```python
# Tham số chốt
TOP_K = 4
SCORE_THRESHOLD = 0.65
EMBEDDING_MODEL = "gemini-embedding-001"   # 768 chiều
DISTANCE = "Cosine"
```

Luồng:
1. Embed câu hỏi (đã được Reference Resolver làm rõ).
2. Nếu intent xác định được → thêm `query_filter` theo `topic` để thu hẹp.
3. Truy vấn Qdrant `limit = TOP_K`.
4. Lọc bỏ chunk có `score < 0.65`.
5. Nếu còn 0 chunk → **thử lại lần 2 không dùng filter topic** (phòng trường hợp
   phân loại intent sai làm mất kết quả đúng).
6. Vẫn 0 chunk → trả `[]`, kích hoạt fallback.

Fallback khi Qdrant lỗi: bắt `ResponseHandlingException`, `UnexpectedResponse`,
trả `[]` và ghi log ERROR — **không** để exception nổi lên tầng API.

### 1.4 Prompt Builder

```
[SYSTEM]
Bạn là trợ lý tư vấn của công ty XKLĐ điều dưỡng Nhật Bản.
Quy tắc bắt buộc:
1. Chỉ trả lời dựa trên phần TÀI LIỆU bên dưới.
2. Nếu tài liệu không chứa câu trả lời, nói rõ là chưa có thông tin
   và đề nghị để lại số điện thoại. Tuyệt đối không bịa số liệu.
3. Không hứa hẹn chắc chắn trúng tuyển, không cam kết mức lương cụ thể
   ngoài con số có trong tài liệu.
4. Xưng "em", gọi khách là "anh/chị". Trả lời tiếng Việt, ngắn gọn,
   dùng gạch đầu dòng khi liệt kê.

[TÀI LIỆU]
[1] (nguồn: Bảng chi phí 2026 — mục Tổng chi phí)
...
[4] ...

[LỊCH SỬ] 6 lượt gần nhất

[HỒ SƠ ĐÃ BIẾT] tên, tiếng Nhật, địa điểm mong muốn (nếu có)

[CÂU HỎI] ...
```

Giới hạn context: tối đa 4 chunk và 6 lượt hội thoại. Nếu vượt token budget,
cắt lịch sử trước, giữ nguyên tài liệu.

### 1.5 Gemini Service

| Tham số | Giá trị |
|---|---|
| Model | `gemini-2.5-flash` |
| Timeout | 30s |
| Retry | 3 lần với mã 429/500/503 |
| Delay | 2s → 5s → 10s |
| Client | `httpx.AsyncClient` |
| Temperature | 0.3 (sinh câu trả lời), 0.0 (trích xuất JSON) |

Điểm cần sửa so với code hiện tại: `app/llm/gemini.py` đang dùng `requests`
đồng bộ, chặn event loop của FastAPI. Phải chuyển sang `httpx.AsyncClient` và
`asyncio.sleep` cho phần delay. Đây là lỗi hiệu năng thật, không phải góp ý hình thức.

Ngoài retry, cần **circuit breaker** đơn giản: nếu 5 lần gọi liên tiếp thất bại
trong 60s, tạm ngắt 30s và trả fallback ngay, tránh mọi request đều phải chờ 17s.

### 1.6 Response Validator

Tính `confidence` từ ba thành phần:

```
confidence = 0.5 * retrieval_score_max
           + 0.3 * grounding_ratio
           + 0.2 * intent_confidence
```

- `retrieval_score_max`: score cao nhất trong các chunk lấy được.
- `grounding_ratio`: tỷ lệ câu trong trả lời có từ khóa/số liệu xuất hiện trong
  context (đo bằng code, không hỏi LLM).
- Nếu không có chunk nào → `confidence = 0`, ép fallback.

Chặn cứng: nếu trả lời chứa số tiền/số liệu **không** có trong context →
thay bằng câu fallback và ghi log WARNING. Đây là hàng rào chống bịa số.

---

## 2. CV Analysis Pipeline (bất đồng bộ)

```
File CV
   ↓
[1] Validator        định dạng, kích thước, checksum chống trùng
   ↓
[2] Text Extractor   PDF → PyMuPDF | DOCX → python-docx | Ảnh/PDF scan → Gemini Vision
   ↓
[3] Cleaner          bỏ ký tự rác, chuẩn hóa khoảng trắng, gộp dòng gãy
   ↓
[4] Profile Extractor   LLM + JSON schema cố định, temperature = 0
   ↓
[5] Evidence Validator  loại field không có evidence
   ↓
[6] Merger           hợp nhất với profile sẵn có theo thứ tự ưu tiên nguồn
   ↓
Candidate Profile
```

**Chọn phương pháp trích text**: nếu PyMuPDF trả về < 100 ký tự trên toàn tài liệu
→ coi là PDF scan, chuyển sang Gemini Vision OCR.

**JSON schema ép LLM tuân thủ** (`response_schema` của Gemini):

```json
{
  "type": "object",
  "properties": {
    "full_name":        { "type": ["string", "null"] },
    "birth_year":       { "type": ["integer", "null"] },
    "gender":           { "type": ["string", "null"], "enum": ["male", "female", null] },
    "education_level":  { "type": ["string", "null"] },
    "major":            { "type": ["string", "null"] },
    "experience_years": { "type": ["number", "null"] },
    "japanese_level":   { "type": ["string", "null"],
                          "enum": ["N1","N2","N3","N4","N5","CHUA_HOC", null] },
    "care_experience":  { "type": ["boolean", "null"] },
    "skills":           { "type": "array", "items": {
                            "type": "object",
                            "properties": { "name": {"type":"string"},
                                            "evidence": {"type":"string"} },
                            "required": ["name","evidence"] } },
    "work_history":     { "type": "array", "items": { "type": "object" } },
    "strengths":        { "type": "array", "items": {
                            "type": "object",
                            "properties": { "text": {"type":"string"},
                                            "evidence": {"type":"string"} },
                            "required": ["text","evidence"] } },
    "evidence":         { "type": "object" }
  },
  "required": ["full_name", "evidence"]
}
```

**Prompt chống suy diễn** (phần bắt buộc):

```
Chỉ trích xuất thông tin CÓ TRONG văn bản. Với mỗi kết luận, bạn phải trích
nguyên văn đoạn làm căn cứ vào trường evidence.
Nếu không tìm được căn cứ, đặt giá trị null. Không suy đoán.
CẤM sinh các nhận xét về tính cách như "kiên nhẫn", "chịu khó", "tận tâm",
"nhiệt tình", "ham học hỏi" — CV không chứng minh được những điều này.
strengths chỉ được nêu năng lực suy ra trực tiếp từ bằng cấp, kinh nghiệm
hoặc chứng chỉ có trong văn bản.
```

**Evidence Validator** (code, không phải prompt): duyệt từng phần tử `skills` và
`strengths`, loại bỏ phần tử có `evidence` rỗng hoặc `evidence` không xuất hiện
trong `raw_text` (so khớp mờ, ngưỡng 0.8). Đây là chốt chặn thật; prompt chỉ là
lớp phòng thủ thứ nhất.

**Thứ tự ưu tiên khi hợp nhất**:
`staff` > `user_confirmed` > `cv` > `chat` > suy luận của LLM.

---

## 3. Need Analysis Pipeline

Chạy khi: hội thoại đạt lượt thứ 3, 6, 10...; hoặc ngay sau khi upload CV;
hoặc khi xuất hiện entity mới. Không chạy mỗi lượt để tiết kiệm quota.

Input: toàn bộ hội thoại của phiên (tối đa 30 lượt gần nhất).
Output: Consultation Profile theo JSON schema, mỗi trường kèm `message_id` làm bằng chứng.

---

## 4. Matching Engine (code thuần, không dùng LLM để chấm điểm)

Quyết định thiết kế quan trọng: **điểm số do Python tính, LLM chỉ diễn giải.**
Lý do: LLM chấm điểm không nhất quán giữa các lần gọi, không kiểm thử được và
không giải thích được cho hội đồng bảo vệ đồ án.

### 4.1 Bước 1 — Hard filter

Loại thẳng đơn hàng nếu: `status != OPEN`, quá `deadline`,
tuổi ứng viên ngoài `[age_min, age_max]`, giới tính không khớp yêu cầu bắt buộc.

### 4.2 Bước 2 — Chấm điểm thành phần

| Tiêu chí | Trọng số | Cách tính |
|---|:--:|---|
| Ngành nghề | 0.30 | Khớp `job_group` = 1.0; cùng `industry` = 0.7; khác = 0.0 |
| Tiếng Nhật | 0.25 | Đạt yêu cầu = 1.0; thiếu 1 bậc = 0.6; thiếu 2 bậc = 0.2; thiếu hơn = 0.0 |
| Kinh nghiệm | 0.20 | `min(exp_years / required_years, 1.0)`; không yêu cầu = 1.0 |
| Học vấn | 0.15 | Đạt = 1.0; thấp hơn 1 bậc = 0.5; thấp hơn nữa = 0.0 |
| Địa điểm | 0.10 | Đúng tỉnh = 1.0; cùng vùng = 0.6; khác = 0.3 |

```
score = Σ (trọng số × điểm thành phần)
```

Địa điểm chỉ chiếm 0.1 vì đây là nguyện vọng, không phải điều kiện loại trừ —
ứng viên thường sẵn sàng đổi tỉnh nếu đơn hàng tốt.

### 4.3 Bước 3 — Phân mức

| Mức | Ngưỡng |
|---|---|
| `CAO` | score ≥ 0.75 |
| `TRUNG_BINH` | 0.50 ≤ score < 0.75 |
| `THAP` | score < 0.50 |

Chỉ đề xuất cho ứng viên các đơn `CAO` và `TRUNG_BINH`, tối đa 3 đơn.
Nhân viên nội bộ xem được cả mức `THAP`.

### 4.4 Bước 4 — Sinh lý do bằng LLM

LLM nhận `breakdown` đã tính sẵn và thông tin hai bên, nhiệm vụ **chỉ là diễn đạt**:

```
Dưới đây là kết quả so khớp đã được hệ thống tính toán.
Hãy viết 2-3 câu tiếng Việt giải thích vì sao ứng viên phù hợp,
dựa ĐÚNG các con số được cung cấp. Không được tự đánh giá lại mức độ phù hợp,
không đưa thêm tiêu chí ngoài danh sách. Nếu có mục thiếu, nêu thẳng và trung thực.
```

Nếu LLM lỗi → dùng template ghép chuỗi từ `matched_reasons` (đã sinh bằng code),
hệ thống vẫn hoạt động bình thường.

---

## 5. Consultation Summary Pipeline

Input: Candidate Profile + Consultation Profile + Top-3 recommendation + lịch hẹn.
Output: phiếu tổng hợp 5 mục cố định (thông tin, nhu cầu, điểm mạnh, đề xuất,
hành động tiếp theo).

Đây là chức năng tiết kiệm thời gian rõ rệt nhất cho nhân viên: thay vì đọc 40 tin
nhắn, họ đọc một phiếu nửa trang. Phiếu được đánh dấu `is_stale` khi profile
thay đổi, kèm nút tạo lại.

---

## 6. Chiến lược fallback tổng hợp

| Sự cố | Hành vi hệ thống |
|---|---|
| Qdrant chết | Retriever trả `[]`, chat trả lời chung + mời để lại SĐT |
| Gemini 429 | Retry 3 lần; thất bại → câu xin lỗi cố định, tạo Lead `NEED_CONTACT` |
| Gemini timeout | Như trên; log ERROR kèm `request_id` |
| Không có chunk ≥ 0.65 | Fallback, `is_fallback = true`, tính vào chỉ số fallback rate |
| LLM trả JSON sai schema | Retry 1 lần với prompt sửa lỗi; thất bại → `PARTIAL` |
| MongoDB chết | API trả 503; widget hiện thông báo bảo trì |

Nguyên tắc: **ứng viên không bao giờ nhìn thấy stack trace hay màn hình trắng.**

---

## 7. Đánh giá chất lượng AI

| Hạng mục | Cách đo | Mục tiêu |
|---|---|---|
| Intent accuracy | Bộ test 200 câu tự gán nhãn | ≥ 85% |
| Entity F1 (SĐT) | Bộ test 100 câu | ≥ 95% |
| RAG hit rate | 50 câu hỏi có đáp án đã biết, kiểm tra chunk đúng nằm trong Top-4 | ≥ 80% |
| Fallback rate | Đo trên dữ liệu thật | ≤ 15% |
| CV extraction accuracy | 30 CV mẫu, so field thủ công | ≥ 80% field đúng |
| Tỷ lệ suy diễn | Đếm strengths không có evidence hợp lệ | 0% |

Bộ dữ liệu kiểm thử đặt tại `backend/tests/fixtures/`, dùng làm bằng chứng
định lượng trong báo cáo đồ án.
