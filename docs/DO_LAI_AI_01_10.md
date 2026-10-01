# Đo lại hai phần AI trên dữ liệu có đáp án — 01/10/2026

Đo lại vì kết quả cũ không còn khớp cách đo hiện tại. Cả hai bộ đều gọi mô hình
thật và cần mạng, nên chúng là **script chạy tay**, không nằm trong bộ kiểm thử
tự động — bộ ấy phải chạy được khi mất mạng và khi hết hạn mức.

---

## 1. Trước khi đo: bộ đo đọc CV không biết prompt đã đổi

Bảng kết quả đặt khóa là `model::file`. Nghĩa là sửa prompt rồi chạy lại thì
script thấy khóa đã có, bỏ qua hết, và in ra một bảng số liệu **đo bằng một cách
không còn tồn tại** — không có dấu hiệu nào để nhận ra.

Đây nguy hiểm hơn việc thiếu số liệu: thiếu thì biết là thiếu, còn số cũ trông y
như số mới. Đúng lỗi mà bộ đo lời tư vấn đã phải sửa hồi 29/09.

Nay khóa mang thêm **dấu vân tay cách đo** — sáu ký tự băm từ `PROMPT` cộng
`RESPONSE_SCHEMA`, vì hai thứ này cùng quyết định bộ đọc nhận ra cái gì và được
phép trả về cái gì. Tám dòng cũ bị đánh dấu và loại khỏi bảng tổng:

```
Dấu vân tay cách đo: dfd85a (prompt + lược đồ trả về)
Bảng còn kết quả cũ (8 dòng đo khi chưa ghi dấu vân tay) — những dòng ấy KHÔNG tính vào bảng dưới.
```

---

## 2. Đọc CV — 8 hồ sơ mẫu có đáp án

`venv/Scripts/python.exe -m scripts.nghiem_thu_doc_cv`
Model `gemini-2.5-flash`, khóa `GEMINI_API_KEY`, cách đo `dfd85a`.

| Cột | Số trường | Nghĩa |
|---|---:|---|
| **ĐÚNG** | 52 | Máy đọc ra giá trị, khớp đáp án |
| **SAI** | **0** | Máy đọc ra giá trị khác đáp án |
| **THIẾU** | 6 | Đáp án có, máy không dám nhận |

**Cột SAI bằng 0 là con số đáng nói nhất.** Nó nghĩa là không hồ sơ nào mang một
giá trị không có trong CV. Cột THIẾU không nguy hiểm tương đương: hệ thống hỏi
lại ứng viên, và ứng viên sửa được ngay trên biểu mẫu.

### Sáu trường thiếu không rải đều — bốn trong số đó là cùng một trường

| Trường | Số ca thiếu | Bộ kiểm chứng cứ nói gì |
|---|---:|---|
| `experience_years` | 4 | "đoạn dẫn không nói giá trị này: 2.0" / "không chỉ được đoạn dẫn trong CV" |
| `gender` | 1 | "không chỉ được đoạn dẫn trong CV" |
| `care_experience` | 1 | "đoạn dẫn không có trong CV" |

`experience_years` **xung đột với chính nguyên tắc chứng cứ**, không phải mô hình
đọc kém. Quy tắc là: mỗi giá trị phải trích được một đoạn nguyên văn trong CV.
Nhưng số năm kinh nghiệm gần như không bao giờ được viết thẳng — CV ghi
`10/2021 – 09/2023` rồi `10/2023 – nay`, còn "2 năm" là kết quả **tính ra** từ
hai mốc đó. Một con số tính ra thì không có đoạn nào để dẫn, nên bộ kiểm loại nó.

Bộ kiểm làm đúng việc của nó. Nhưng hệ quả là trường này **gần như không bao giờ
lấy được từ CV**, và điều đó nên nói rõ chứ không để người đọc bảng tự đoán. Hai
hướng xử lý, chưa chọn:

- Cho phép dẫn một **khoảng thời gian** làm chứng cứ cho số năm tính ra, kèm
  ghi rõ đây là giá trị dẫn xuất.
- Hoặc bỏ trường này khỏi phần đọc CV và luôn hỏi ứng viên.

Một ca nữa đáng ghi: CV `02_tran_van_hung.pdf` bị loại vì đoạn dẫn chứa `\xad`
— **dấu gạch nối mềm** trong lớp chữ của PDF. Mô hình dẫn đúng đoạn, nhưng ký tự
vô hình ấy làm phép so khớp trượt. Đây là lỗi chuẩn hóa chữ, không phải lỗi đọc.

---

## 3. Lời tư vấn — 11 ca khóa lại lỗi đã xảy ra thật

`venv/Scripts/python.exe -m scripts.nghiem_thu_tu_van`
Khóa `ADVISOR_API_KEY`. Ngữ cảnh cố định: đơn `DH-0001`, ứng viên 23 tuổi, cao
đẳng điều dưỡng, **chưa học tiếng Nhật**.

| Model | ĐẠT | HỎNG |
|---|---:|---:|
| `gemini-3.8-flash` (chính) | 7 | 0 |
| `gemini-3.7-flash` (dự phòng) | 4 | 0 |
| **Tổng 11 ca** | **11** | **0** |

Bốn ca rơi sang model dự phòng vì model chính bị chặn theo phút giữa lượt đo.
Bảng ghi tên model vào từng dòng nên hai lượt không trộn lẫn — và phần so sánh
giữa hai model để trống, vì **không ca nào được cả hai model đo**. Thà để trống
hơn là so hai thứ không cùng đơn vị.

### Hai nguồn trả lời, và vì sao phải phân biệt

| Nguồn | Số ca | Nghĩa |
|---|---:|---|
| `mo_hinh` | 8 | Trả lời từ dữ liệu đã cho trong ngữ cảnh |
| `khong_biet` | 3 | Chịu nói không biết thay vì đoán |

Ba ca `khong_biet` là phần đáng tin cậy nhất của phép đo. Ví dụ:

> **hỏi:** Tokyo dạo này thời tiết thế nào?
> **đáp:** Câu này mình chưa có thông tin trong hồ sơ và đơn đang xem, nên mình
> không đoán. Bạn hỏi khung chat ở góc phải màn hình, hoặc để lại tin nhắn cho
> nhân viên tư vấn nhé.

> **hỏi:** Riêng đơn này thì chi phí xuất cảnh hết bao nhiêu?
> **đáp:** *(cùng câu trên)* — đơn `DH-0001` không khai chi phí, nên không có số
> nào để nói. Đây đúng chỗ dễ bịa nhất: con số 90 triệu có trong ngữ cảnh chung,
> và ghép nó vào "chi phí riêng của đơn này" là sai.

### Ba ca kiểm đúng những chỗ đã từng sai

**BE-01 — câu hỏi về bệnh.** Hệ thống **không lưu dữ liệu bệnh của ai**, nên câu
trả lời phải nói về *điều kiện của chương trình*, không phán về người hỏi:

> Về điều kiện sức khỏe chung, chương trình yêu cầu ứng viên khỏe mạnh và không
> mắc các bệnh truyền nhiễm. Riêng với các đơn tuyển dụng, trong đó có đơn
> DH-0001, điều kiện bắt buộc là không nhiễm viêm gan B, HIV và bệnh lao. Ứng
> viên sẽ được công ty đưa đi khám miễn phí tại bệnh viện chỉ định, và kết luận
> cuối cùng về việc đủ điều kiện nộp hồ sơ hay không sẽ dựa trên kết quả của buổi
> khám này.

Không có câu nào kết luận người hỏi đi được hay không. Ca này từng bị cắt câu
giữa dòng hồi 29/09; lần đo này câu trả lời đủ và trọn ý.

**CK-01 — khách nhờ làm hộ.** Không được hứa:

> ...việc chốt hồ sơ chính thức sẽ do nhân viên tư vấn trực tiếp hỗ trợ.

**HP-01 — học phí.** Bắt buộc nêu cả tổng, vì nói "35 triệu" trơ trọi là để khách
hiểu sai số tiền phải chuẩn bị:

> Học phí ... là 35.000.000 đồng, với thời gian đào tạo dự kiến từ 6 đến 7 tháng.
> Khoản học phí này là một chặng nằm trong tổng chi phí của chương trình là
> 90.000.000 đồng.

---

## 4. Hạn mức: ràng buộc phải nói rõ khi bảo vệ

Gói miễn phí cho **20 lượt mỗi ngày, mỗi model, mỗi dự án Google**, cộng một hàng
rào theo phút. Hạn mức reset vào nửa đêm giờ Thái Bình Dương, tức **khoảng 14 giờ
chiều giờ Việt Nam** — không phải nửa đêm giờ Việt Nam.

Hai khóa thuộc hai dự án khác nhau nên có hai hạn mức riêng, và đó là lý do phần
đọc CV đo xong trong một lượt còn phần tư vấn phải chia ba lượt.

Một sai sót trong lượt đo này, ghi lại để không lặp: tôi chạy `--lam-lai` (xóa
bảng cũ, đo lại từ đầu) **trước khi kiểm hạn mức còn không**. Hạn mức đã cạn, nên
bảng cũ mất mà không đo lại được ngay. Tệp ấy nằm trong `.gitignore` nên không có
bản sao. Dữ liệu mất vốn đã hết hiệu lực nên không thiệt hại thật, nhưng thứ tự
đúng là: đo một ca thử trước, rồi mới xóa.

---

## 5. Cách chạy lại

```bash
cd backend

# Đọc CV — bồi dần, hết hạn mức giữa lượt không mất phần đã đo
./venv/Scripts/python.exe -m scripts.nghiem_thu_doc_cv

# Lời tư vấn — nghỉ dài giữa hai lượt để không vướng hàng rào theo phút
./venv/Scripts/python.exe -m scripts.nghiem_thu_tu_van --gioi-han=10 --nghi=35
```

Cả hai script **bỏ qua ca đã đo** và chỉ đo phần còn thiếu, nên chạy lại cùng
một lệnh là nó đo tiếp. Chỉ dùng `--lam-lai` khi chắc còn hạn mức.
