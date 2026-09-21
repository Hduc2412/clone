# Kiểm thử hệ thống

Lần chạy gần nhất: 21/09/2026. **617 ca kiểm thử backend và 5 ca frontend, tất cả đạt**, thời gian chạy khoảng 15 giây.

```bash
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -t .
```

Tham số `-t .` là bắt buộc. Thiếu nó thì Python nạp các file kiểm thử như module rời chứ không
như một gói, nên `tests/__init__.py` không chạy và giá trị cấu hình mặc định không được đặt.
Trên máy đã có `.env` thì vẫn chạy được nên lỗi này dễ bị bỏ qua; trên máy vừa clone repo về
thì toàn bộ bộ kiểm thử đổ lỗi nạp module.

Bộ kiểm thử **không cần mạng và không gọi Gemini**. Mọi lệnh gọi ra ngoài đều được thay bằng
bản giả lập, nên chạy được cả khi hết hạn mức gọi mô hình.

---

## 1. Tổng hợp theo module

| Module | Số ca | Phạm vi kiểm | Kết quả |
|---|---:|---|:---:|
| `test_matching_engine` | 65 | **Bộ đối chiếu**: bảy tiêu chí cứng, bốn tiêu chí mềm, tính tất định, thứ tự xếp hạng, không đọc đồng hồ | Đạt |
| `test_candidate_profiles` | 43 | Hồ sơ ứng viên: gộp theo thứ tự ưu tiên nguồn, khóa lạc quan theo phiên bản, chặn client tự khai nguồn, phân quyền | Đạt |
| `test_job_orders` | 30 | Danh mục đơn tuyển dụng: chuẩn hóa danh mục, ràng buộc dữ liệu, vòng đời trạng thái, phân quyền, lọc công khai | Đạt |
| `test_matching_service` | 27 | Tầng điều phối: kho đơn đem xét, dấu vân tay danh mục, bộ nhớ đệm mười phút, nội dung nhật ký | Đạt |
| `test_matching_seeded_data` | 28 | Nghiệm thu bộ đối chiếu trên đúng mười chín đơn mẫu sẽ dùng khi demo | Đạt |
| `test_matching_api` | 22 | API đối chiếu: chặn hồ sơ chưa xác nhận, ẩn đơn bị loại khỏi ứng viên, phạm vi xem của nhân viên | Đạt |
| `test_matching_weights` | 19 | Bộ trọng số ngoài mã: tổng đúng 100, mỗi luật con không vượt trọng số, thiếu file thì báo lỗi | Đạt |
| `test_matching_explain` | 12 | Khối lý do: khớp từng byte với bản thiết kế, không import gì liên quan mô hình ngôn ngữ | Đạt |
| `test_job_order_import` | 26 | Nhập hàng loạt từ Excel: đọc file, báo lỗi từng dòng, chốt chặn ở tầng API | Đạt |
| `test_seed_job_orders` | 13 | Dữ liệu mẫu: tính hợp lệ và độ phủ của mười chín đơn hàng | Đạt |
| `test_appointment_management` | 11 | Lịch hẹn: trạng thái, phân công, đổi lịch, chặn trùng | Đạt |
| `test_recruitment_applications` | 11 | Hồ sơ tuyển dụng: chuyển trạng thái, quyền sở hữu | Đạt |
| `test_lead_access_control` | 10 | Phân quyền truy cập khách hàng | Đạt |
| `test_chat_pipeline` | 8 | Luồng hội thoại: dự phòng, nguồn tham khảo, xếp hạng truy xuất | Đạt |
| `test_api_hardening` | 7 | Kiểm tra dữ liệu vào, giới hạn tần suất, không chặn vòng lặp sự kiện | Đạt |
| `test_auth` | 7 | Băm mật khẩu, ký và kiểm token, khóa sau năm lần sai | Đạt |
| `test_managed_lead_phone` | 7 | Chuẩn hóa và chống trùng số điện thoại | Đạt |
| `test_audit_log` | 6 | Nhật ký thao tác: che dữ liệu nhạy cảm, phân quyền đọc | Đạt |
| `test_customer_journey` | 5 | Hành trình khách hàng gộp từ nhiều nguồn | Đạt |
| `test_rag_resilience` | 5 | Chịu lỗi khi mô hình quá tải hoặc kho vector không phản hồi | Đạt |
| `test_analytics_service` | 4 | Số liệu thống kê hoạt động | Đạt |
| `test_booking` | 4 | Đặt lịch qua khung chat | Đạt |
| `test_intent_entity` | 3 | Phân loại ý định và trích xuất thực thể | Đạt |
| `test_session_lead` | 3 | Khôi phục phiên hội thoại | Đạt |
| `test_runtime` | 2 | Bảng mã đầu ra | Đạt |
| `test_cv_documents` | 31 | Đọc CV: nhận file, bóc tách, bộ kiểm chứng đoạn dẫn, gộp vào hồ sơ với nguồn `cv` | Đạt |
| `test_employee_scores` | 28 | Điểm nhân viên ghi theo từng sự kiện, chống cộng trùng, điều chỉnh của quản lý | Đạt |
| `test_registrations` | 26 | Đăng ký sơ bộ: chuỗi chốt chặn, dựng lại khách hàng cũ theo số điện thoại | Đạt |
| `test_handover` | 16 | Bàn giao hồ sơ: nhận xử lý, phân công, chuyển giao | Đạt |
| `test_response_validator` | 13 | Kiểm chứng câu trả lời của mô hình trước khi gửi đi | Đạt |
| `test_prompt_rules` | 18 | Quy tắc dựng prompt: mỗi luật sinh từ một lời đã đo được | Đạt |
| `test_refusal_flag` | 11 | Khi nào chatbot phải từ chối thay vì đoán | Đạt |
| `test_embedding_cache` | 10 | Bộ nhớ đệm vector nhúng, tiết kiệm hạn mức gọi mô hình | Đạt |
| `test_intent_classifier` | 10 | Phân loại ý định câu hỏi | Đạt |
| `test_retriever_selection` | 9 | Chọn đoạn đem vào ngữ cảnh: sàn tuyệt đối và dải tương đối | Đạt |
| `test_journey_profile` | 12 | Nối hội thoại với hồ sơ ứng viên: trích xuất theo quy tắc, ghi nguồn `chat`, không đè thông tin đã xác nhận | Đạt |
| `test_candidate_portal` | 21 | Hệ khách hàng: hai loại token không dùng lẫn được, ứng viên chỉ thấy hồ sơ của mình, danh sách trường được phép | Đạt |
| `test_password_resets` | 16 | Quên mật khẩu: không dò được ai đã đăng ký, phân quyền xử lý, bắt buộc đổi sau khi đặt lại | Đạt |
| `test_job_lookup` | 13 | Chatbot tra cứu đơn theo mã trong hội thoại | Đạt |
| **Tổng** | **617** | | **Đạt** |

**285 ca cho danh mục đơn hàng và bộ đối chiếu**, **101 ca** cho đọc CV, đăng ký sơ bộ, hàng đợi
và điểm nhân viên, **37 ca** cho hệ khách hàng và luồng mật khẩu, **194 ca** còn lại cho phần hội
thoại, truy xuất tri thức và nền hệ thống.

Ngoài ra website có **5 ca** chạy bằng `node --test` cho phần mã phiên dùng chung giữa khung
chat và luồng hồ sơ: `cd frontend && npm test`.

Bộ đối chiếu chiếm phần lớn số ca không phải ngẫu nhiên. Nó là thứ quyết định ứng viên nào được
giới thiệu đơn nào, và vì nó là Python thuần — không gọi mô hình ngôn ngữ, không đọc đồng hồ,
không chạm database — nên mọi tính chất của nó chứng minh được bằng số chứ không phải bằng lời.

---

## 2. Chi tiết ca kiểm thử

### 2.1. Danh mục đơn tuyển dụng

| Mã | Chức năng | Mục tiêu kiểm | Dữ liệu vào | Kết quả mong đợi | Đạt |
|---|---|---|---|---|:---:|
| DH-01 | Chuẩn hóa loại hình cơ sở | Bốn cách viết cùng cho một mã | `Viện dưỡng lão`, `vien duong lao`, `VIEN_DUONG_LAO`, có khoảng trắng thừa | Đều ra `vien_duong_lao` | ✔ |
| DH-02 | Chuẩn hóa tên tỉnh | Nhận cả chữ Latinh có dấu và tên gọi khác | `Tōkyō`, `Ōsaka`, `hyogo ken` | `Tokyo`, `Osaka`, `Hyogo` | ✔ |
| DH-03 | Danh mục tỉnh | Đủ và đúng bốn mươi bảy tỉnh | Bảng tỉnh | 47 tỉnh, mỗi tỉnh thuộc một vùng hợp lệ | ✔ |
| DH-04 | Suy vùng từ tỉnh | Không bắt nhập hai lần và nhập lệch nhau | `Tokyo`, `Fukuoka` | `kanto`, `kyushu` | ✔ |
| DH-05 | Giá trị lạ | Không đoán bừa khi không nhận ra | `nhà hàng`, `Hà Nội` | Trả về rỗng, không chọn giá trị gần đúng | ✔ |
| DH-06 | Trình độ tiếng Nhật mập mờ | Lấy **mức thấp nhất** khi câu có nhiều mức | `N4 trở lên, ưu tiên N3` | `N4`, kèm danh sách đủ `["N4","N3"]` | ✔ |
| DH-07 | Mức tiếng lẫn trong câu | Bắt được mã nằm giữa câu | `Trình độ N4`, `Chưa học`, `không rõ` | `N4`, `chua_hoc`, rỗng | ✔ |
| DH-08 | Đồ thị trạng thái | Khớp mục 7.1 của báo cáo | Bảng chuyển trạng thái | `draft→{open,closed}`, `open→{paused,filled,expired,closed}`, `closed` là điểm cuối | ✔ |
| DH-09 | Nhãn trạng thái | Mọi trạng thái đều có nhãn tiếng Việt | Bảng trạng thái | Không trạng thái nào thiếu nhãn | ✔ |
| DH-10 | Tạo đơn | Cấp mã tuần tự và tự suy vùng | Đơn tại Tokyo | Mã `DH-0001`, vùng `kanto`, đã tuyển 0 | ✔ |
| DH-11 | Hạn nộp đã qua | Không tạo đơn đang tuyển đã hết hạn | Hạn nộp hôm qua | Từ chối, mã lỗi 400 | ✔ |
| DH-12 | Đổi trạng thái | Rời trạng thái đang tuyển thì tự tắt công khai | `open` → `paused` | Khóa theo trạng thái hiện tại, `unpublish` bật | ✔ |
| DH-13 | Chuyển trạng thái sai | Không cho chuyển ngược từ trạng thái đóng | `closed` → `open` | Từ chối, mã lỗi 409 | ✔ |
| DH-14 | Hai người sửa cùng lúc | Người sau không ghi đè người trước | Trạng thái đã đổi bởi người khác | Mã lỗi 409, yêu cầu tải lại | ✔ |
| DH-15 | Bật công khai đơn nháp | Báo rõ đơn chưa thật sự hiển thị | Đơn `draft`, bật công khai | Trả về `visible_publicly` bằng sai | ✔ |
| DH-16 | Xóa đơn | Chỉ xóa được đơn nháp | Đơn `open` | Từ chối, mã lỗi 409 | ✔ |
| DH-17 | Sửa đơn đã đóng | Không sửa nội dung đơn đã đóng | Đơn `closed` | Từ chối, mã lỗi 409 | ✔ |
| DH-18 | Sửa lẻ khoảng tuổi | Kiểm tra với giá trị đang lưu, không chỉ giá trị gửi lên | Đang 20–35, sửa tuổi từ thành 40 | Từ chối, mã lỗi 400 | ✔ |
| DH-19 | Điều kiện công khai | Ba điều kiện luôn đi cùng nhau ở tầng dữ liệu | Hàm dựng bộ lọc công khai | Đủ `published`, `status` bằng `open`, hạn nộp còn | ✔ |
| DH-20 | Ẩn trường nội bộ | Loại ở tầng truy vấn, không dựa tầng trên | Projection công khai | Bỏ ghi chú nội bộ, người tạo, người sửa, số đã tuyển | ✔ |
| DH-28 | Danh sách công khai | Bộ lọc công khai không bị bỏ sót khi có tham số lọc | Lọc theo tỉnh `Tōkyō` | Truy vấn vẫn giữ đủ ba điều kiện, tỉnh chuẩn hóa thành `Tokyo` | ✔ |
| DH-21 | Cập nhật lồng nhau | Sửa một điều kiện không xóa các điều kiện khác | `{requirements:{age_min:20}}` | Thành `{"requirements.age_min":20}` | ✔ |
| DH-22 | Khoảng tuổi | Tuổi từ không lớn hơn tuổi đến | 40 và 25 | Từ chối ngay ở bước kiểm dữ liệu | ✔ |
| DH-23 | Khoảng lương | Lương từ không lớn hơn lương đến | 300.000 và 100.000 | Từ chối | ✔ |
| DH-24 | Loại hình lạ | Không nhận giá trị ngoài danh mục | `quán ăn` | Từ chối | ✔ |
| DH-25 | Trạng thái khởi tạo | Đơn mới chỉ ở nháp hoặc đang tuyển | Tạo đơn `Đã đóng` | Từ chối | ✔ |
| DH-26 | Chuẩn hóa khi tạo | Nhãn tiếng Việt thành mã lưu trữ | `Viện dưỡng lão`, `Cao đẳng`, `Không yêu cầu` | `vien_duong_lao`, `cao_dang`, `khong_yeu_cau` | ✔ |
| DH-27 | Cập nhật một phần | Chỉ gửi trường nào thì chỉ sửa trường đó | `{requirements:{age_min:25}}` | Đúng một khóa được ghi | ✔ |
| TG-01 | Tính tuổi | Theo năm sinh và mốc thời gian cho trước | Sinh 2003, mốc 11/09/2026 | 23 tuổi | ✔ |
| TG-02 | Thiếu năm sinh | Phân biệt "chưa rõ" với "bằng không" | Không có năm sinh | Trả về rỗng, **không** trả 0 | ✔ |

### 2.2. Nhập đơn hàng từ Excel

| Mã | Chức năng | Mục tiêu kiểm | Dữ liệu vào | Kết quả mong đợi | Đạt |
|---|---|---|---|---|:---:|
| NL-01 | File mẫu | Đủ sheet và đủ cột | File mẫu sinh ra | Có sheet nhập liệu, hướng dẫn, danh mục; tiêu đề khớp đúng thứ tự | ✔ |
| NL-02 | Vòng khứ hồi | Dữ liệu ví dụ trong file mẫu nhập lại được | Sheet ví dụ | Không dòng nào lỗi | ✔ |
| NL-03 | Dòng hợp lệ | Đọc thành bản ghi đúng | Một dòng đầy đủ | Nhãn thành mã, vùng tự suy, phụ cấp tách theo dấu chấm phẩy | ✔ |
| NL-04 | Nhãn không dấu | Nhận cả cách viết không dấu | `vien duong lao`, `khong yeu cau`, `co` | Nhận đúng | ✔ |
| NL-05 | Có mã đơn | Coi là cập nhật thay vì tạo mới | Dòng có `DH-0007` | Hành động `update` | ✔ |
| NL-06 | Định dạng ngày | Hiểu bốn cách viết ngày | `30/11/2026`, ISO, `30-11-2026`, ô kiểu ngày | Đều ra cùng một ngày | ✔ |
| NL-07 | **Tiếng Nhật nhiều mức** | Từ chối, không tự đoán | `N4 trở lên, ưu tiên N3` | Báo lỗi "ô ghi nhiều mức", buộc chọn một mức | ✔ |
| NL-08 | Dòng trống | Bỏ qua, không tính là lỗi | Xen một dòng trống | Chỉ đếm các dòng có dữ liệu | ✔ |
| NL-09 | Thứ tự cột | Đảo cột vẫn đọc được | Tiêu đề đảo ngược | Đọc đúng | ✔ |
| NL-10 | Thiếu cột bắt buộc | Báo trước khi đọc dòng nào | Bỏ cột tên đơn | Nêu tên cột thiếu, không trả dòng nào | ✔ |
| NL-11 | Thiếu giá trị bắt buộc | Nêu đúng tên cột | Ô tên đơn để trống | Thông báo có chữ "tên đơn" | ✔ |
| NL-12 | Giá trị ngoài danh mục | Liệt kê các lựa chọn hợp lệ | `nhà hàng` | Thông báo kèm danh sách nhận được | ✔ |
| NL-13 | Khoảng tuổi ngược | Bắt lỗi | 40 và 25 | Báo lỗi | ✔ |
| NL-14 | Khoảng lương ngược | Bắt lỗi | 300.000 và 100.000 | Báo lỗi | ✔ |
| NL-15 | **Ô sai ở cột không bắt buộc** | Báo lỗi thay vì âm thầm bỏ qua | `một năm`, `khoảng một trăm triệu`, `cuối tháng` | Cả ba đều báo lỗi có tên cột | ✔ |
| NL-16 | Hạn nộp đã qua | Chặn khi trạng thái đang tuyển | Hạn nộp năm ngày trước | Báo lỗi | ✔ |
| NL-17 | Hạn nộp đã qua trên đơn nháp | Cho phép | Hạn đã qua, trạng thái nháp | Không báo lỗi | ✔ |
| NL-18 | Ngày không đọc được | Báo lỗi rõ ràng | `tháng sau` | Thông báo "không đọc được thành ngày" | ✔ |
| NL-19 | Trạng thái đóng | Buộc đổi trên màn hình quản trị để lưu lịch sử | `Đã đóng` | Báo lỗi, chỉ dẫn sang màn hình quản trị | ✔ |
| NL-20 | Số lượng tuyển | Phải lớn hơn không | 0 | Báo lỗi | ✔ |
| NL-21 | Mã đơn lặp trong file | Chỉ rõ dòng đã xuất hiện trước | Hai dòng cùng `DH-0009` | Báo lỗi kèm số dòng đầu tiên | ✔ |
| NL-22 | Số dòng | Khớp tuyệt đối với số dòng Excel | Dòng 2 đúng, dòng 3 lỗi | Báo đúng dòng 2 và 3 | ✔ |
| NL-23 | File hỏng | Thông báo đọc được cho người dùng | Chuỗi không phải Excel | "Không đọc được file Excel" | ✔ |
| NL-24 | Sai định dạng | Chặn ở tầng API | File `.csv` | Mã lỗi 415 | ✔ |
| NL-25 | File quá lớn | Chặn trước khi đọc | Vượt 5MB | Mã lỗi 413 | ✔ |
| NL-26 | Thiếu cột ở tầng API | Chỉ dẫn tải lại file mẫu | Bỏ cột tên đơn | Mã lỗi 400, thông báo nêu tên cột | ✔ |

### 2.3. Dữ liệu mẫu

| Mã | Chức năng | Mục tiêu kiểm | Kết quả mong đợi | Đạt |
|---|---|---|---|:---:|
| DM-01 | Mã đơn | Tuần tự và không trùng | `DH-0001` đến `DH-0019`, không lặp | ✔ |
| DM-02 | Kiểu lưu trữ | Lưu mã chứ không lưu nhãn | Mọi enum thuộc bảng danh mục | ✔ |
| DM-03 | Vùng | Suy đúng từ tỉnh cho mọi đơn | Khớp bảng tra | ✔ |
| DM-04 | Kiểu ngày | Chuỗi ISO để so sánh được trong truy vấn | Đọc được bằng `date.fromisoformat` | ✔ |
| DM-05 | Khoảng giá trị | Tuổi, lương, số lượng đều hợp lệ | Không khoảng nào ngược | ✔ |
| DM-06 | Độ phủ chương trình | Đủ ba diện và ba loại hình cơ sở | 3 và 3 | ✔ |
| DM-07 | Độ phủ vùng | Trải ít nhất bốn vùng | Bảy vùng | ✔ |
| DM-08 | **Độ phủ tiếng Nhật** | Hồ sơ N4 phải vừa đạt đơn này vừa trượt đơn kia | Có đủ N5, N4, N3 | ✔ |
| DM-09 | Yêu cầu kinh nghiệm | Có đơn cần và có đơn không cần | Cả hai nhóm đều có | ✔ |
| DM-10 | Giới hạn giới tính | Có đơn giới hạn để kiểm tiêu chí này | Tồn tại đơn yêu cầu giới tính | ✔ |
| DM-11 | Số đơn bị ẩn | Đúng ba đơn không hiện trên website | 3 | ✔ |
| DM-12 | Lý do bị ẩn | Ba lý do khác nhau | Nháp, tạm dừng, và đang tuyển nhưng quá hạn | ✔ |
| DM-13 | Đánh dấu dữ liệu mẫu | Lệnh nạp lại không xóa nhầm đơn thật | Mọi đơn mẫu mang dấu `seed` | ✔ |

### 2.4. Hồ sơ ứng viên

| Mã | Chức năng | Mục tiêu kiểm | Dữ liệu vào | Kết quả mong đợi | Đạt |
|---|---|---|---|---|:---:|
| HS-01 | Ưu tiên nguồn | Bản đọc CV không đè thứ ứng viên đã tự sửa | Đã có N4 do ứng viên xác nhận, CV đọc ra N3 | Giữ N4, không ghi nhận thay đổi | ✔ |
| HS-02 | Ưu tiên nguồn | Nhân viên được phép sửa lại | Đã có N4 của ứng viên, nhân viên nhập N3 | Thành N3 | ✔ |
| HS-03 | Ưu tiên nguồn | Cùng nguồn thì được tự sửa mình | Ứng viên gõ lại tên có dấu | Nhận giá trị mới | ✔ |
| HS-04 | Nguồn dữ liệu | **Client không bao giờ khai được nguồn** | Gửi kèm `{"source": "staff"}` | Bị từ chối ngay ở bước kiểm dữ liệu | ✔ |
| HS-05 | Giá trị rỗng | Trường vắng mặt nghĩa là chưa rõ | Gửi chuỗi rỗng và `null` | Không ghi gì, không tạo ô rỗng | ✔ |
| HS-06 | Tách hai mục | Nguyện vọng không lọt vào chỗ dùng để loại đơn | Gửi `desired_prefecture` vào mục năng lực | Báo lỗi trường không hợp lệ | ✔ |
| HS-07 | Tách hai mục | Hai mục không dùng chung khóa nào | Giao của hai tập khóa | Rỗng | ✔ |
| HS-08 | Đã khai và chưa hỏi | `chua_hoc` là một câu trả lời | Hồ sơ khai chưa học tiếng | Không nằm trong danh sách còn thiếu | ✔ |
| HS-09 | Khóa lạc quan | Hai tab sửa cùng lúc | Tab sau gửi phiên bản đã cũ | Mã lỗi 409, yêu cầu tải lại | ✔ |
| HS-10 | Phiên bản | Gửi đúng giá trị đang có thì không đẻ phiên bản mới | Gửi lại tên cũ | Không ghi, không thêm bản lịch sử | ✔ |
| HS-11 | Xác nhận | Thiếu thông tin bắt buộc thì nói rõ thiếu gì | Hồ sơ trống | 409 kèm danh sách trường thiếu | ✔ |
| HS-12 | Xác nhận | Xác nhận hai lần không gây hại | Hồ sơ đã xác nhận | Trả về nguyên trạng, không ghi thêm | ✔ |
| HS-13 | **Suy ra vùng** | Vùng suy từ tỉnh phải thực sự vào được hồ sơ | Chỉ nêu `Tokyo` | Hồ sơ có `desired_region_group = kanto` | ✔ |
| HS-14 | Che dữ liệu | Bản công khai không lộ thông tin nội bộ | Hồ sơ đã phân công | Không có `assigned_to`, `lead_code`, lịch sử | ✔ |
| HS-15 | Phân quyền | Tư vấn viên chỉ thấy hồ sơ mình phụ trách | Vai trò `consultant` | Truy vấn bị ép thêm điều kiện phụ trách | ✔ |
| HS-16 | Phân quyền | Không mở được hồ sơ người khác | Hồ sơ của tư vấn viên khác | Mã lỗi 403 | ✔ |

### 2.5. Bộ đối chiếu

| Mã | Chức năng | Mục tiêu kiểm | Dữ liệu vào | Kết quả mong đợi | Đạt |
|---|---|---|---|---|:---:|
| DC-01 | **Tất định** | Chạy hai lần ra kết quả giống hệt | Cùng hồ sơ, cùng danh mục đơn | Hai chuỗi JSON giống nhau từng byte | ✔ |
| DC-02 | **Tất định** | Thứ tự database trả về không ảnh hưởng | Danh sách đơn đảo ngược | Vẫn ra đúng thứ tự hạng đó | ✔ |
| DC-03 | Không đọc đồng hồ | Thời điểm là tham số truyền vào | Chặn `local_today` | Không hàm nào gọi tới nó | ✔ |
| DC-04 | Bảy tiêu chí cứng | Mỗi đơn luôn sinh đúng bảy dòng | Mọi đơn, mọi hồ sơ | Bảy dòng, không hơn không kém | ✔ |
| DC-05 | Ba kết quả | Mỗi tiêu chí đạt đủ ba trạng thái | Ca dựng riêng cho từng tiêu chí | ĐẠT, KHÔNG ĐẠT, CHƯA RÕ | ✔ |
| DC-06 | **Chỉ loại khi chắc chắn** | Thiếu dữ liệu không loại đơn | Hồ sơ chỉ có họ tên | 16/18 đơn vẫn đạt | ✔ |
| DC-07 | Câu hỏi tiếp theo | Cái chưa biết thành câu hỏi | Hồ sơ thiếu chín trường | Chín câu hỏi bằng tiếng Việt | ✔ |
| DC-08 | Chưa khai năm sinh | Không phải là quá tuổi | Hồ sơ không có năm sinh | Không dòng tuổi nào KHÔNG ĐẠT | ✔ |
| DC-09 | Thứ bậc tiếng Nhật | `chua_hoc` thấp hơn `N5` | Sáu mức từ chưa học tới N1 | Số đơn đạt tăng đều, không giảm | ✔ |
| DC-10 | Thứ bậc bằng cấp | Bằng cao hơn không thấy ít đơn hơn | Bốn bậc bằng cấp | Số đơn đạt tăng đều | ✔ |
| DC-11 | Đơn hàng hỏng | Đơn thiếu hạn nộp hoặc trạng thái thì bị loại | Đơn khuyết trường | Loại, không phải CHƯA RÕ | ✔ |
| DC-12 | Bảng điểm mềm | Bốn tiêu chí, từng con số | Trùng tỉnh / trùng vùng / khác | 40 / 25 / 0 | ✔ |
| DC-13 | Mốc lương | Thiếu dưới 10% vẫn được điểm một phần | Đơn trả 90% mức mong muốn | Được điểm mốc gần | ✔ |
| DC-14 | **Đơn bị loại không có điểm** | Không mời người đọc đem so sánh | Đơn trượt tiêu chí cứng | Điểm 0, hạng rỗng, không có dòng mềm | ✔ |
| DC-15 | Phá thế hòa | Cùng điểm thì theo hạn nộp rồi tới mã đơn | Hai đơn cùng 60 điểm | Thứ tự `(-điểm, hạn, mã)` | ✔ |
| DC-16 | Nguyện vọng | Đổi nguyện vọng không đổi ai đạt ai trượt | Năm bộ nguyện vọng khác nhau | Số đơn đạt không đổi | ✔ |
| DC-17 | Nguyện vọng | Nhưng có đổi thứ tự | Mong muốn Kantō rồi Kyūshū | Đơn đứng đầu khác nhau | ✔ |
| DC-18 | Khung điểm | Không điểm nào vượt 100 hay âm | Mọi đơn mẫu | Trong khoảng 0–100 | ✔ |
| DC-19 | Trọng số | Tổng phải đúng 100 | File trọng số sai tổng | Báo lỗi ngay khi nạp | ✔ |
| DC-20 | Trọng số | Luật con không được vượt trọng số của nó | Luật 50 trong nhóm trọng số 40 | Báo lỗi | ✔ |
| DC-21 | Trọng số | **Thiếu file thì báo lỗi, không quay về số cứng** | Xóa đường dẫn file | Ném `WeightsError` | ✔ |
| DC-22 | Khối lý do | Khớp từng byte với bản thiết kế | Đơn mẫu trong tài liệu | Chuỗi giống hệt | ✔ |
| DC-23 | Khối lý do | Không dính gì tới mô hình ngôn ngữ | Quét module `explain` | Không import nào liên quan | ✔ |
| DC-24 | Kho đơn | Giữ đơn hết hạn và tạm dừng để chứng minh bộ lọc chạy | Truy vấn kho | Chỉ lọc `published`, không lọc trạng thái hay hạn | ✔ |
| DC-25 | Kho đơn | Đơn nháp không bao giờ được chào cho ai | Đơn `draft` | Không vào kho | ✔ |
| DC-26 | Dấu vân tay | Thứ tự database trả về không làm đổi dấu | Đảo danh sách | Dấu giống hệt | ✔ |
| DC-27 | Dấu vân tay | Sửa một đơn là bộ nhớ đệm mất hiệu lực | Đổi `updated_at` một đơn | Dấu khác đi | ✔ |
| DC-28 | Bộ nhớ đệm | Tra theo đủ bốn yếu tố đầu vào | Gọi lần hai trong mười phút | Dùng lại, không tính lại | ✔ |
| DC-29 | Bộ nhớ đệm | Nhân viên chạy lại thì bỏ qua đệm | Cờ `force` | Tính lại, kết quả vẫn giống hệt | ✔ |
| DC-30 | Nhật ký | Ghi mọi đơn đã xét kể cả đơn bị loại | 18 đơn, 9 đạt | 18 mục, mỗi mục có lý do từng tiêu chí | ✔ |
| DC-31 | Nhật ký | Đủ dữ liệu để tái lập kết quả | Một bản ghi | Có phiên bản bộ đối chiếu, trọng số, hai dấu vân tay, ngày tính | ✔ |
| DC-32 | Nhật ký | Danh sách không kéo theo bảng tiêu chí | Truy vấn danh sách | Trường `items` bị loại khỏi kết quả | ✔ |
| DC-33 | **Chốt chặn xác nhận** | Hồ sơ chưa xác nhận thì không được đối chiếu | Hồ sơ trạng thái `extracted` | Mã lỗi 409 | ✔ |
| DC-34 | Bản công khai | Ứng viên chỉ thấy đơn mình đạt | Kết quả có cả đơn trượt | Chỉ trả về đơn đạt | ✔ |
| DC-35 | Bản công khai | Luôn kèm câu miễn trừ | Mọi lần gọi | Có câu "không phải cam kết trúng tuyển" | ✔ |
| DC-36 | Phân quyền | Tư vấn viên chỉ xem nhật ký của mình | Vai trò `consultant` | Truy vấn bị ép thêm điều kiện phụ trách | ✔ |
| DC-37 | Phân quyền | Không chạy lại được trên hồ sơ người khác | Hồ sơ của người khác | Mã lỗi 403 | ✔ |
| DC-38 | Nhật ký thao tác | Nhân viên chạy lại thì có vết | Bấm chạy lại | Ghi `recommendation.rerun` | ✔ |

### 2.6. Nghiệm thu trên dữ liệu thật

Ngoài các ca đơn vị, có một kịch bản chạy trên database thật, đúng câu chuyện trong
`docs/design/14`: ứng viên 23 tuổi, Cao đẳng Điều dưỡng, N4, muốn làm viện dưỡng lão ở Tokyo.

```bash
cd backend
.\venv\Scripts\python.exe -m scripts.nghiem_thu_doi_chieu
```

Tám bước: kiểm kho đơn, nhập hồ sơ qua API công khai, đối chiếu, in khối lý do của đơn đứng đầu,
liệt kê đơn bị loại kèm lý do, chạy lại để so kết quả, thử hồ sơ mới điền một nửa, rồi dọn dẹp.
Lần chạy gần nhất: 18 đơn đã xét, 9 đạt, đơn đứng đầu 100/100, ba lần chạy cho kết quả giống hệt.
**Không gọi mô hình ngôn ngữ lần nào** — mọi điểm số và lời giải thích do Python sinh ra.

---

## 3. Chín lỗi thật do kiểm thử phát hiện

Phần này đáng chú ý hơn con số 617, vì nó cho thấy bộ kiểm thử có tác dụng thật.

| Lỗi | Nếu lọt ra thì sao | Ca chặn |
|---|---|---|
| Chuỗi `N4 trở lên, ưu tiên N3` bị đọc thành `N3` | Lấy mức khó hơn mức bắt buộc, **loại oan toàn bộ ứng viên N4** ngay ở bộ lọc cứng. Đúng loại sai mà hệ thống này tồn tại để tránh | DH-06, NL-07 |
| Ba trường được đọc sau bước kiểm lỗi | Ô sai ở kinh nghiệm, tổng chi phí, ngày phỏng vấn âm thầm biến thành rỗng. Người nhập không hề biết dữ liệu của mình bị mất | NL-15 |
| Đơn rời trạng thái đang tuyển mà cờ công khai vẫn bật | Đơn đã tạm dừng hoặc đã đóng vẫn nằm trên website, ứng viên nộp hồ sơ vào đơn không còn nhận | DH-12 |
| Vùng suy ra từ tỉnh bị loại khỏi hồ sơ trước khi lưu | Ứng viên muốn Tokyo sẽ chấm một đơn ở Kanagawa — cùng vùng Kantō, đáng cộng 25 điểm — **ngang bằng một đơn ở Fukuoka**. Danh sách giới thiệu vẫn ra, chỉ là sai thứ tự | HS-13 |
| `requirements.txt` thiếu sáu gói, trong đó có `pydantic-settings` | **Ai clone repo về đều không chạy được.** `app/core/config.py` import nó ngay dòng đầu. Bản trên GitHub đã ở tình trạng đó suốt nhiều ngày | Dựng venv trắng rồi cài lại từ file |
| `frontend/lib/publicApi.ts` trỏ cổng 8000 trong khi `lib/api.ts` cùng app đã là 8020 | Khung chat chạy bình thường còn **toàn bộ trang đơn hàng và luồng tư vấn thì rỗng**. Rất dễ chẩn đoán nhầm là lỗi nghiệp vụ | Rà soát toàn bộ khai báo cổng |
| Gửi CV xong làm **trắng cả trang tư vấn** | `POST /public/documents` trả hồ sơ không qua `decorate` nên thiếu `labels`; giao diện đọc `profile.labels.japanese_level` và ném `TypeError`, React gỡ sạch DOM. **Ứng viên mất trắng mọi thứ vừa khai, không thông báo gì** | Chạy tay trọn kịch bản demo trên trình duyệt |
| Mọi mốc thời gian trong màn hình quản trị **sai bảy tiếng** | Hồ sơ vừa đăng ký hiện là *"đăng ký 7 giờ trước"*. MongoDB lưu UTC nhưng driver trả datetime không mang múi giờ, FastAPI serialise thành chuỗi không có hậu tố `Z`, trình duyệt hiểu là giờ địa phương | Chạy tay trọn kịch bản demo |
| Bộ chấm chất lượng tự nó không chạy được trên bản clone sạch | Quảng cáo là "chạy ngoại tuyến không cần gì" nhưng vẫn đòi `GEMINI_API_KEY`, vì `app.core.config` kiểm tra lúc import | Chạy thử chính bộ chấm trong bản công bố không có `.env` |

Lỗi thứ nhất và lỗi thứ tư cùng một loại, và là loại nguy hiểm nhất: hệ thống vẫn chạy, không
báo lỗi gì, chỉ âm thầm cho ra kết quả sai. Không có ca kiểm thử thì chỉ phát hiện được khi một
ứng viên thật bị loại oan hoặc nhận một danh sách xếp sai.

Lỗi thứ tư đáng nói thêm: nó không bị bộ kiểm thử đơn vị bắt được, vì ca kiểm khi đó chỉ hỏi
"validator có suy ra vùng không" — và câu trả lời là có. Cái sai nằm ở bước sau, lúc đóng gói dữ
liệu để lưu. Nó lộ ra khi chạy kịch bản nghiệm thu đầu-cuối trên database thật và nhìn thấy dòng
`Vùng suy ra từ tỉnh: None`. Ca HS-13 được thêm vào sau đó, và giờ nó kiểm đúng chỗ: giá trị suy
ra có thực sự đi được tới hồ sơ hay không.

### 3.1. Lỗi lệch múi giờ — đã sửa và **đã xác minh**

Mục này trước đây để riêng vì "đã sửa" và "đã nhìn thấy chạy đúng" là hai chuyện
khác nhau. Nay đã xác minh xong ngày 17/09:

| Kiểm cái gì | Kết quả |
|---|---|
| API trả về mốc thời gian | `2026-09-16T11:45:17.616000Z` — có hậu tố `Z`, không còn mơ hồ |
| Màn hình hàng đợi | Hồ sơ tạo lúc `16/09 11:45Z`, xem lúc `17/09 09:27Z` → hiện **"đăng ký 21 giờ trước"** |
| Đối chiếu | Cách nhau 21,7 giờ. Đúng. Trước khi sửa sẽ lệch 7 tiếng |

### 3.2. Vấn đề còn mở

| Vấn đề | Ảnh hưởng | Đề xuất |
|---|---|---|
| Hạn mức Gemini gói miễn phí **20 lượt gọi mỗi ngày cho mỗi model** | Bộ câu hỏi chatbot 35 câu **không chạy trọn được trong một ngày**. Đây là ràng buộc phải đưa vào kế hoạch bảo vệ, không phải chuyện kỹ thuật vặt | Bộ đo đã lưu kết quả từng câu và chỉ đo phần còn thiếu ở lần sau |
| Bộ câu hỏi lệch: 27 phải-từ-chối trên 35 câu | Một con bot từ chối tất cả vẫn được 27/35. Tỷ lệ đó làm bộ đo dễ dãi | Cân thêm câu phải-trả-lời, nhưng việc đó gắn với chuyện kho tri thức còn mỏng |
| Bộ đọc CV mới có 6 hồ sơ mẫu | Spec §7 đặt mốc 30. Con số đọc CV chưa đủ tư cách làm bằng chứng trong báo cáo | Bổ sung thêm CV mẫu |
| Hai phiên làm việc song song giành cổng và giành file | Đã hai lần dựng trùng công cụ: bộ câu hỏi chatbot, và bộ khẳng định cho bộ đối chiếu. Cả hai lần đều phải gộp lại sau | Kiểm cái đã có trước khi dựng cái mới; chia cố định `8020/3100/3101` và `8030/4000/4001` |
| Chưa đóng gói Docker | Kế hoạch có hạng mục `docker-compose` 6 service kèm nginx | Làm sau khi chốt tính năng |
| Chưa có `docs/handoff/KNOWLEDGE_BASE_SPEC.md` | Nhóm chatbot đang chờ bản mô tả API quản lý tri thức cho màn hình "Tri thức AI" | Viết và gửi |

### 3.3. Đo chất lượng ngoại tuyến

Ngoài ba bộ nghiệm thu ở mục 6, có một bộ chấm **không cần dịch vụ nào** — không
Qdrant, không Gemini, không MongoDB, không cần cả `.env`:

```bash
cd backend
.\venv\Scripts\python.exe -m scripts.danh_gia_chat_luong
```

| Hạng mục | Kết quả 17/09 | Mục tiêu spec §7 | Đạt |
|---|---:|---:|:---:|
| Phân loại ý định | 85/100 = 85,0% | ≥ 85% | vừa đủ |
| Trích số điện thoại | 17/20 = 85,0% | ≥ 95% | chưa |

Dữ liệu ở `backend/tests/fixtures/danh_gia/`, nhãn do người gán chứ không lấy từ
đầu ra của chính hệ thống. Bốn câu thật sự nằm giữa hai nhóm ý định được đánh dấu
chấp nhận cả hai nhãn, nên con số đo chất lượng bộ phân loại chứ không đo tranh
cãi về nhãn.

Hai lỗi của phần chatbot phát hiện qua bộ này, đã báo lại chứ không tự sửa vì
`app/conversation/` thuộc phần người khác — chi tiết ở mục 9 của
`docs/handoff/BAO_CAO_GUI_NHOM_CHATBOT.md`:

- `extract_phone` bỏ sót `+84…`, `84 987 654 321`, `0971-716-939`, dù dự án **đã
  có sẵn** `app/core/phone.py: normalize_vietnamese_phone` xử lý đúng cả ba.
- Khớp từ khóa theo chuỗi con khiến `khoảng` trúng `khoản`, đẩy câu hỏi về lương
  sang nhóm chi phí.

---

## 4. Cách viết kiểm thử trong dự án

Dùng `unittest` sẵn có của Python, lớp `IsolatedAsyncioTestCase` cho hàm bất đồng bộ,
`AsyncMock` và `patch` để thay thế tầng dữ liệu. Gọi thẳng hàm xử lý của endpoint và truyền
người dùng vào như tham số, thay vì dựng máy chủ thật.

Nhờ cách đó bộ kiểm thử chạy trong khoảng bốn giây, không cần mạng, không cần Gemini, và không
phụ thuộc vào việc MongoDB có đang chạy hay không ở phần lớn ca.

Tên ca kiểm thử viết thành câu mô tả điều cần đúng, ví dụ
`test_ambiguous_japanese_requirement_takes_the_minimum`. Khi một ca đổ lỗi, tên của nó đã nói
ra điều gì vừa hỏng, không phải mở mã nguồn ra đọc mới biết.

---

## 5. Những phần chưa có kiểm thử tự động

Nói rõ để không hiểu nhầm con số 617 là đã phủ hết hệ thống.

| Phần | Hiện trạng | Dự kiến |
|---|---|---|
| Giao diện website và màn hình quản trị | Kiểm tra bằng mắt và bằng lệnh dựng bản phát hành | Chưa có kế hoạch kiểm thử tự động trong phạm vi đồ án |
| Đọc hồ sơ CV | Có bộ nghiệm thu `scripts/nghiem_thu_doc_cv.py` chấm từng trường trên sáu hồ sơ mẫu | Chạy lại trước mỗi mốc bàn giao |
| Chatbot trả lời có căn cứ | Có bộ nghiệm thu `scripts/nghiem_thu_chatbot.py` trên bộ câu hỏi chuẩn | Bổ sung câu hỏi khi kho tri thức dày thêm |
| Đăng ký sơ bộ và phiếu tóm tắt | Đã có `test_registrations.py` | — |
| Hàng đợi và điểm nhân viên | Đã có `test_handover.py` và `test_employee_scores.py`, gồm ca hai người cùng nhận một hồ sơ | — |
| Đóng gói Docker | Đã dựng và chạy thử cả sáu dịch vụ ngày 17/09: website, quản trị và backend lên qua nginx, nạp được 19 đơn mẫu, toàn bộ ca kiểm thử chạy trong container đều đạt | Chạy lại trước khi bàn giao |
| Chạy tải | Chưa làm | Ngoài phạm vi |

Sáu file CV mẫu đã sẵn sàng, gồm bốn định dạng khác nhau và một bản scan không có lớp chữ.
Mỗi hồ sơ nhắm một tình huống: đủ điều kiện, trình độ cao, chưa học tiếng, quá tuổi, thiếu năm
sinh, và ghi trình độ tiếng Nhật mập mờ. File `dap_an.json` đi kèm ghi những gì bộ đọc phải rút
ra đúng, dùng để chấm điểm bằng số khi phần đó hoàn thành.


---

## 6. Ba bộ nghiệm thu chạy tay

`docs/design/13 §4` đặt ra ba câu hỏi đúng/sai cho phần đo kiểm. Mỗi câu có một bộ riêng.
Cả ba **không nằm trong `unittest`** vì chúng cần mạng, cần database thật, và hai trong ba
bộ gọi mô hình ngôn ngữ. Bộ kiểm thử thường phải chạy được cả khi mất mạng và hết hạn mức,
nên trộn vào đó là làm hỏng tính chất ấy.

| Câu hỏi của spec | Bộ nghiệm thu | Cần gì |
|---|---|---|
| Hệ thống có trả lời sai khi không đủ căn cứ không? | `scripts.nghiem_thu_chatbot` | Qdrant, MongoDB, gọi mô hình |
| Bộ lọc điều kiện cứng có loại nhầm đơn nào không? | `scripts.nghiem_thu_doi_chieu` | MongoDB. **Không** gọi mô hình |
| Thông tin rút từ CV có đúng bản gốc không? | `scripts.nghiem_thu_doc_cv` | Gọi mô hình |

```bash
cd backend
.\venv\Scripts\python.exe -m scripts.nghiem_thu_chatbot
.\venv\Scripts\python.exe -m scripts.nghiem_thu_doi_chieu
.\venv\Scripts\python.exe -m scripts.nghiem_thu_doc_cv
```

### Bộ câu hỏi chatbot có hai chiều

`tests/fixtures/chatbot/bo_cau_hoi.json` chia câu hỏi làm hai loại ngược nhau:

- **phải trả lời** — kho tri thức có nội dung này. Hỏng khi bot từ chối, vì khách bị đẩy
  sang hotline một cách vô ích.
- **phải từ chối** — kho không có. Hỏng khi bot trả lời, vì khách tin và hành động theo.

Phải có cả hai chiều. Chỉ đo chiều "không được bịa" thì cách đạt điểm tuyệt đối rẻ nhất là
cho bot từ chối mọi câu, và nó sẽ vô dụng trong khi bảng điểm rất đẹp.

### Hạn mức gọi mô hình chặn việc chạy một lượt

Gói miễn phí của Gemini cho **20 lượt gọi mỗi ngày** cho mỗi model
(`GenerateRequestsPerDayPerProjectPerModel-FreeTier`). Bộ câu hỏi hiện có hơn ba mươi câu,
mỗi câu một lượt gọi, nên **không thể chạy trọn trong một ngày** trên khoá miễn phí.

Vì vậy bộ nghiệm thu chatbot lưu kết quả từng câu vào `ket_qua_gan_nhat.json` và lần chạy
sau chỉ đo những câu chưa có:

```bash
.\venv\Scripts\python.exe -m scripts.nghiem_thu_chatbot                 # chạy tiếp
.\venv\Scripts\python.exe -m scripts.nghiem_thu_chatbot --gioi-han=10   # chỉ đo 10 câu
.\venv\Scripts\python.exe -m scripts.nghiem_thu_chatbot --lam-lai       # bỏ kết quả cũ, đo lại từ đầu
```

Muốn chạy trọn một lượt thì cần khoá trả phí. Đây là điều kiện cần ghi vào kế hoạch bảo vệ,
không phải chuyện phát sinh lúc chạy.

### Bộ nghiệm thu phải trung thực về chính nó

Hai chốt chặn được thêm sau khi cả hai bộ đều từng cho ra **bảng kết quả sai**:

- **Kho tri thức không với tới được.** Lần chạy đầu tiên, Qdrant đang tắt nên mọi câu rơi
  vào câu dự phòng: toàn bộ phần phải-trả-lời hỏng, toàn bộ phần phải-từ-chối đạt. Nhìn
  bảng thì tưởng chatbot hỏng nặng, thật ra chưa đo được gì. Nay bộ này kiểm tra kho trước
  khi đo và dừng hẳn nếu không kết nối được.
- **Dịch vụ quá tải.** Câu trả lời "chatbot đang có nhiều yêu cầu cùng lúc" từng bị chấm là
  "đã từ chối" — làm câu phải-từ-chối đạt vì một lý do chẳng liên quan gì. Nay nó được ghi
  là *chưa đo được*.

Một bộ nghiệm thu báo sai về chính nó còn tệ hơn là không có bộ nào, vì nó tạo ra niềm tin
sai. Cả hai lỗi trên đều lộ ra ngay trong lần chạy đầu, và đều nằm trong bộ đo chứ không
nằm trong sản phẩm.

### Bộ đọc CV: bốn cột thay vì một con số

`nghiem_thu_doc_cv` chấm mỗi trường vào một trong bốn cột. **ĐÚNG** và **SAI** thì rõ.
**THIẾU** nghĩa là máy không dám nhận — không nguy hiểm bằng SAI, vì hệ thống sẽ hỏi lại
ứng viên; nhưng nhiều quá thì bộ đọc thành vô dụng. **NGOÀI PHẠM VI** là các trường nguyện
vọng, mà bộ đọc **cố ý không rút** từ CV: nguyện vọng phải do chính ứng viên nói ra.

Chỉ cột SAI làm lượt nghiệm thu thất bại. Không biết thì hỏi là hành vi đúng; biết sai mới
là hỏng.
