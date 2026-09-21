# Vòng đời hồ sơ đăng ký — hiện trạng và đề xuất

**Người duyệt:** Hoàng Minh Đức
**Ngày:** 21/09/2026
**Cần quyết:** bốn việc ở mục 6

Kế hoạch ban đầu hẹn một tài liệu để bạn duyệt **trước khi** viết phần vòng đời.
Việc đã làm ngược lại: mã nguồn chạy trước, tài liệu viết sau. Nên tài liệu này
làm hai việc cùng lúc — ghi lại cái đang chạy, rồi mới đề xuất phần còn thiếu.

Lý do phải có nó: **hiện không tài liệu nào mô tả vòng đời hồ sơ đăng ký.**
`docs/design/11`–`14` nói về vòng đời *đơn tuyển dụng*; Hình 4.3 trong báo cáo
cũng vậy. Mười ba trạng thái của hồ sơ ứng viên chỉ tồn tại trong
`backend/app/api/applications.py`. Hội đồng hỏi "một hồ sơ đi qua những bước
nào" thì hôm nay phải mở mã nguồn ra đọc.

---

## 1. Hai trục độc lập, không phải một

Đây là điều dễ hiểu sai nhất, và cũng là chỗ bản đề xuất cũ trong kế hoạch đã
nhầm.

| Trục | Trả lời câu hỏi | Lưu ở đâu | Ai đổi được |
|---|---|---|---|
| **Trạng thái nghiệp vụ** | Hồ sơ đi tới đâu trong quy trình? | `status` | Người đang phụ trách, hoặc quản lý |
| **Quyền sở hữu** | Ai đang cầm hồ sơ này? | `assigned_to` | Quản lý; hoặc chính nhân viên qua nhận/trả |

Nhận một hồ sơ từ hàng đợi **không** đổi trạng thái của nó — chỉ đặt
`assigned_to`. Một hồ sơ `screening` có thể đang chưa ai cầm (vừa bị trả về hàng
đợi), và một hồ sơ `draft` có thể đã có người phụ trách (vừa nhận, chưa kịp gọi).

Gộp hai trục thành một dãy trạng thái duy nhất — như `pending_intake → received`
trong bản đề xuất cũ — nghe gọn hơn nhưng tạo ra một câu hỏi không trả lời được:
**một hồ sơ đang ở `collecting_documents` mà nhân viên trả về hàng đợi thì nó lùi
về `received` hay giữ nguyên?** Cả hai đáp án đều sai. Lùi về thì mất thông tin
giấy tờ đã thu; giữ nguyên thì hàng đợi không tìm ra nó.

Hàng đợi hiện lọc theo `source = "self_registration"` và `assigned_to = null`,
không đụng tới `status`. Nhờ vậy câu hỏi trên không bao giờ phát sinh.

---

## 2. Mười ba trạng thái đang chạy

```
draft ──► collecting_documents ──► screening ──► eligible ──┬──► training ──┐
                                      │                      │              │
                                      │                      └──────────────┴──► waiting_interview
                                      │                                              │
                                      ▼                                              ▼
                                  rejected                                        passed
                                                                                     │
                                                                                     ▼
                                                                            visa_processing
                                                                                     │
                                                                                     ▼
                                                                            ready_departure
                                                                                     │
                                                                                     ▼
                                                                                 departed

Từ bất kỳ trạng thái mở nào cũng rẽ được sang: withdrawn, cancelled
```

| Trạng thái | Nhãn trên màn hình | Chuyển tiếp được sang |
|---|---|---|
| `draft` | Mới tạo | `collecting_documents`, `withdrawn`, `cancelled` |
| `collecting_documents` | Thu giấy tờ | `screening`, `withdrawn`, `cancelled` |
| `screening` | Sơ tuyển | `collecting_documents`, `eligible`, `rejected`, `withdrawn`, `cancelled` |
| `eligible` | Đủ điều kiện | `training`, `waiting_interview`, `withdrawn`, `cancelled` |
| `training` | Đang đào tạo | `waiting_interview`, `withdrawn`, `cancelled` |
| `waiting_interview` | Chờ phỏng vấn | `training`, `passed`, `rejected`, `withdrawn`, `cancelled` |
| `passed` | Đã trúng tuyển | `visa_processing`, `withdrawn`, `cancelled` |
| `visa_processing` | Đang làm visa | `ready_departure`, `withdrawn`, `cancelled` |
| `ready_departure` | Chờ xuất cảnh | `departed`, `withdrawn`, `cancelled` |
| `departed` | Đã xuất cảnh | — (điểm cuối) |
| `rejected` | Không đạt | — (điểm cuối) |
| `withdrawn` | Khách rút hồ sơ | — (điểm cuối) |
| `cancelled` | Đã hủy | — (điểm cuối) |

Bốn trạng thái cuối nằm trong `CLOSED_STATUSES`; vào một trong bốn thì
`is_active` tự về `false`, và ràng buộc "mỗi khách chỉ một hồ sơ đang hoạt động"
nhả ra cho hồ sơ sau.

**Hai đường lùi có chủ đích, không phải sơ suất.** `screening → collecting_documents`
cho trường hợp sơ tuyển phát hiện thiếu giấy tờ. `waiting_interview → training`
cho trường hợp hoãn phỏng vấn và cho ứng viên học thêm. Cả hai là chuyện xảy ra
thật ở doanh nghiệp, không phải đường vòng để sửa lỗi bấm nhầm.

Chuyển sai luật trả **409** kèm câu tiếng Việt nói rõ từ đâu sang đâu. Không có
đường nào chuyển thẳng tới trạng thái đóng rồi mở lại: đóng là hết.

---

## 3. Chỉ một mốc sinh điểm

| Sự kiện | Điểm | Ghi ở |
|---|---:|---|
| Nhận hồ sơ từ hàng đợi | +2 | `registrations.accept` |
| Nhận trong 2 giờ đầu kể từ lúc ứng viên đăng ký | +3 (cộng thêm) | `score_service.award_pickup` |
| Gọi được cho khách và ghi kết quả | +5 | `appointment.completed` |
| Đã gọi nhưng không liên lạc được | +1 | `appointment.unreachable` |
| **Ứng viên xuất cảnh** | **+20** | `applications.update` khi vào `departed` |
| Trả hồ sơ về hàng đợi | 0 | `registrations.release` |
| Quản lý điều chỉnh tay | ±N, bắt buộc lý do | `staff-scores/{email}/adjust` |

Trong cả vòng đời, **chỉ `departed` sinh điểm**. Các bước giữa chỉ là đi qua.
Chấm điểm từng bước sẽ thành thưởng cho việc bấm nút: nhân viên đẩy hồ sơ qua
`collecting_documents → screening → eligible` trong ba phút là được 15 điểm mà
chưa gọi cho ai.

> **Bảng điểm trong kế hoạch cũ đã lạc hậu.** Nó ghi "Liên hệ lần đầu trong 24h
> +5", "Đủ điều kiện sơ bộ +5", "Đã nộp đơn +10", "Trúng tuyển +20". Không dòng
> nào trong số đó là quy tắc đang chạy. Bảng trên mới là thật; lấy từ
> `backend/app/services/scoring.py`.

---

## 4. Ba chỗ đang thiếu

### 4.1. Không chuyển nào bắt buộc ghi lý do

Đây là thiếu sót đáng kể nhất. Hôm nay nhân viên chuyển một hồ sơ sang `rejected`
hay `cancelled` mà không phải gõ một chữ nào. Nhật ký ghi lại *ai* và *lúc nào*,
nhưng không có *vì sao*.

Hậu quả không trừu tượng: ba tháng sau ứng viên gọi lại hỏi "sao hồ sơ em bị
loại", người trực máy mở ra thấy đúng hai chữ "Không đạt" và không dựng lại được
chuyện gì đã xảy ra. Bàn giao hồ sơ (`handover`) thì **đã** bắt buộc lý do tối
thiểu 3 ký tự — chuyển trạng thái quan trọng hơn nhiều lại không.

**Đề xuất:** bắt buộc `note` từ 10 ký tự cho bốn chuyển tiếp sang trạng thái
đóng (`rejected`, `withdrawn`, `cancelled`) và cho hai đường lùi
(`screening → collecting_documents`, `waiting_interview → training`). Sáu chỗ,
đúng những chỗ mà sáu tháng sau người ta sẽ hỏi. Các chuyển tiếp tiến thẳng
không cần, vì chúng tự nói lên điều đã xảy ra.

Mười ký tự thay vì ba: ba ký tự cho phép gõ "xxx" cho xong. Mười thì vẫn gõ bừa
được, nhưng phải cố ý.

### 4.2. Bảng chuyển trạng thái nằm ở hai nơi

`backend/app/api/applications.py:45` và
`admin-frontend/app/admin/applications/page.tsx:29` giữ hai bản chép tay của cùng
một bảng **chuyển tiếp**. Hôm nay chúng khớp nhau từng dòng — tôi đã đối chiếu.
Nhưng không có gì bắt chúng phải khớp.

Khi chúng lệch: bản frontend thừa một đường thì nhân viên chọn được một trạng
thái rồi nhận 409 không hiểu vì sao; bản frontend thiếu một đường thì một chuyển
tiếp hợp lệ biến mất khỏi ô chọn và không ai biết nó từng tồn tại.

**Bảng nhãn thì đã lệch thật, và đã sửa hôm nay.** Nhãn tiếng Việt cũng nằm ở hai
nơi: `AdminUI.statusLabels` (dùng cho huy hiệu trạng thái) và `statuses` trong
chính trang hồ sơ (dùng cho ô chọn). Bảng đầu **thiếu bảy trong mười ba trạng
thái**, mà `StatusBadge` lại rơi về `|| status` khi thiếu khóa. Kết quả trên màn
hình là một hàng như thế này:

```
[collecting_documents]   [Thu giấy tờ ▾]
```

Huy hiệu tiếng Anh nằm ngay cạnh ô chọn tiếng Việt của **cùng một trạng thái**.
Bảy trạng thái bị vậy: `draft`, `collecting_documents`, `screening`, `eligible`,
`ready_departure`, `rejected`, `withdrawn`. Riêng `visa_processing` có đủ hai nơi
nhưng hai nơi ghi hai kiểu — "Đang làm visa" ở huy hiệu, "Làm visa" ở ô chọn.

Đã bổ sung bảy nhãn thiếu và thống nhất `visa_processing`. Nhưng đây đúng là cái
giá của việc chép tay: lỗi này nằm sẵn trên màn hình quản trị từ lâu, không ca
kiểm thử nào bắt được, và chỉ lộ ra khi ngồi đối chiếu hai file.

**Đề xuất:** thêm `GET /applications/meta` trả về danh sách trạng thái, nhãn
tiếng Việt và bảng chuyển tiếp — đúng lối `GET /job-orders/meta` đang làm, giao
diện đã quen tiêu thụ dạng đó. Frontend xoá hai hằng số, đọc từ máy chủ. Khoảng
một giờ làm, kể cả kiểm thử.

### 4.3. `draft` là tên sai cho thứ nó đang chỉ

Hồ sơ ứng viên tự đăng ký trên website được tạo với `status = "draft"`, hiện lên
màn hình là **"Mới tạo"**. Nhưng nó không phải bản nháp của nhân viên — nó là một
người thật vừa để lại số điện thoại và đang chờ được gọi.

`draft` đúng nghĩa cho hồ sơ nhân viên tạo tay rồi để đó. Dùng chung một tên cho
hai tình huống khác hẳn nhau khiến bảng hàng đợi đọc sai ý.

**Đề xuất:** không thêm trạng thái mới — chỉ đổi nhãn hiển thị theo `source`.
`source = "self_registration"` hiện **"Ứng viên tự đăng ký"**; còn lại giữ "Mới
tạo". Trường `source` đã có sẵn trong bản ghi, đây thuần là việc hiển thị.

Không đề xuất tách thành trạng thái riêng, vì như mục 1 đã nói, "đã tiếp nhận
hay chưa" là câu hỏi của trục sở hữu, không phải trục nghiệp vụ.

---

## 5. Đề xuất cũ trong kế hoạch: không nên làm

Kế hoạch đề nghị thay mười ba trạng thái bằng dãy:

```
pending_intake → received → contacted → collecting_documents
  → preliminary_qualified → submitted → interviewing → passed | failed
  (nhánh đóng: unqualified, unreachable, withdrawn)
```

Không nên, vì ba lý do:

1. **Nó trộn hai trục.** `pending_intake`, `received` và `contacted` mô tả quan
   hệ giữa *nhân viên* và hồ sơ, không phải vị trí của *hồ sơ* trong quy trình.
   Mục 1 đã nói vì sao trộn lại là ngõ cụt.
2. **Nó cắt mất đoạn sau khi trúng tuyển.** Dãy này dừng ở `passed`. Đời thật
   còn `visa_processing → ready_departure → departed`, mà `departed` mới là mốc
   duy nhất sinh điểm và cũng là kết quả doanh nghiệp quan tâm. Bỏ ba trạng thái
   đó là bỏ luôn phần đo được của cả quy trình.
3. **Giá phải trả không nhỏ.** Mười ba trạng thái này đã đi qua 11 ca kiểm thử
   trong `test_recruitment_applications.py`, một màn hình quản trị, một bảng điểm
   và luồng đăng ký từ website. Thay nó là viết lại cả bốn, đổi lấy một dãy tên
   dễ đọc hơn.

`contacted` là thứ duy nhất trong dãy cũ có giá trị mà mô hình hiện tại chưa nắm
trực tiếp. Nhưng nó **đã được nắm gián tiếp**: một hồ sơ có lịch hẹn ở trạng thái
`completed` hoặc `unreachable` là một hồ sơ đã liên hệ, và chính hai sự kiện đó
sinh điểm. Thêm một trạng thái nữa chỉ tạo thêm một chỗ để hai nguồn nói khác
nhau.

---

## 6. Bốn việc cần bạn quyết

| # | Việc | Công sức | Khuyến nghị |
|---|---|---|---|
| 1 | Bắt buộc lý do ≥10 ký tự cho 6 chuyển tiếp ở §4.1 | ~2 giờ, gồm kiểm thử | **Nên làm.** Đây là thứ hội đồng hỏi được, và cũng là thứ doanh nghiệp cần thật |
| 2 | `GET /applications/meta`, frontend bỏ bản chép tay | ~1 giờ | **Nên làm.** Rẻ, và loại lỗi này đã xảy ra thật một lần rồi (§4.2) |
| 3 | Đổi nhãn `draft` theo `source` | ~30 phút | **Nên làm.** Thuần hiển thị, không đụng dữ liệu |
| 4 | Thay vòng đời theo bản đề xuất cũ | ~2 ngày | **Không nên.** Lý do ở §5 |

Nếu duyệt 1–3 thì nói một câu, tôi làm liền và cập nhật `docs/KIEM_THU.md` kèm
theo. Nếu để sau cũng không sao: hệ thống hiện chạy đúng, đây là phần làm cho nó
giải trình được và khó sai về sau.

---

## 7. Nguồn của tài liệu này

Đọc thẳng từ mã nguồn ngày 21/09/2026, không chép lại từ bản thiết kế:

| Nội dung | File |
|---|---|
| Danh sách trạng thái, bảng chuyển tiếp, trạng thái đóng | `backend/app/api/applications.py` |
| Điểm khi xuất cảnh | `backend/app/api/applications.py` |
| Nhận, bàn giao, trả hồ sơ về hàng đợi | `backend/app/api/registrations.py` |
| Bảng quy tắc điểm | `backend/app/services/scoring.py` |
| Bộ lọc hàng đợi | `backend/app/db/database.py` |
| Nhãn tiếng Việt và bản chép tay bảng chuyển tiếp | `admin-frontend/app/admin/applications/page.tsx` |
