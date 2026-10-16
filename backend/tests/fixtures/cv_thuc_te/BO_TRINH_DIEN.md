# Bộ CV trình diễn: CV nào đạt, CV nào không đạt, vì sao

Dùng khi trình diễn bộ đối chiếu. Mọi kết quả dưới đây do **chính bộ đối chiếu của
hệ thống** tính trên hồ sơ lấy từ đáp án của CV và 19 đơn mẫu, không gọi AI; ca kiểm
thử `tests/test_cv_trinh_dien.py` giữ cho bảng này luôn đúng. CV ở thư mục này
(09–30) và `tests/fixtures/cv/` (01–08). Người và số liệu đều là giả.

## Đơn dùng để trình diễn

| Đơn | Nơi | Tiếng Nhật | Bằng cấp | Kinh nghiệm | Tuổi | Giới tính | Ghi chú |
|---|---|---|---|---|---|---|---|
| **DH-0001** | Tokyo, viện dưỡng lão | N4 | Cao đẳng | 0 | 20–35 | Không yêu cầu | Đơn chính |
| DH-0003 | Saitama, chăm sóc tại nhà | N5 | Trung cấp | 0 | 18–30 | **Nữ** | |
| DH-0004 | Chiba, viện dưỡng lão | N4 | Trung cấp | 0 | 20–38 | Không yêu cầu | |
| DH-0007 | Hyogo, viện dưỡng lão | N5 | Trung cấp | 0 | 18–32 | Không yêu cầu | |
| DH-0014 | Hokkaido, viện dưỡng lão | N4 | Trung cấp | **≥ 1 năm** | 20–38 | Không yêu cầu | |
| DH-0017 | Tokyo, viện dưỡng lão | N3 | Cao đẳng | ≥ 2 năm | 23–35 | Không yêu cầu | **Đã quá hạn nộp** |
| DH-0019 | Kanagawa, viện dưỡng lão | N4 | Trung cấp | 0 | 20–35 | Không yêu cầu | **Tạm dừng** |

## 1. Đạt — khách được đăng ký sơ bộ

| CV | Hồ sơ | Với đơn | Vì sao đạt |
|---|---|---|---|
| 15 Bùi Thị Thanh Tâm (PDF, kèm thư xin việc) | 1998, cử nhân Điều dưỡng, N2, 5 năm hồi sức | DH-0001 | Vượt mọi điều kiện |
| 20 Đặng Thị Mỹ Linh (PDF, có người tham chiếu) | 2001, cao đẳng, N4, 2 năm phòng khám | DH-0001 | Đúng N4, đúng cao đẳng |
| 23 Pham Thi Ngoc Anh (CV tiếng Anh) | 2000, cao đẳng, N4, 3 năm | DH-0001 | CV tiếng Anh vẫn đối chiếu được |
| 30 Hà Thị Lan Anh (PDF có đầu trang) | 2000, cao đẳng Hộ sinh, N4, 4 năm | DH-0001 | Đúng điều kiện |
| 16 Lương Thị Kim Oanh (Word) | 2003, cao đẳng, N4, chưa đi làm | DH-0001 | Đơn này không đòi kinh nghiệm |

## 2. Đạt sơ bộ nhưng còn “chưa rõ” — hệ thống hỏi thêm, **không loại**

| CV | Chưa rõ | Hệ thống làm gì |
|---|---|---|
| 18 Đinh Văn Long — có NAT-TEST 4Q, không có JLPT | Tiếng Nhật | Không tự quy NAT-TEST thành N4; giữ đơn, hỏi khách và để nhân viên xác minh ở buổi sơ tuyển |
| 24 Trần Thị Bích — CV vài dòng | Tiếng Nhật, bằng cấp | Giữ đơn, hỏi bổ sung từng mục; người chưa khai không bị coi là không đủ điều kiện |

## 3. Không đạt đúng một tiêu chí — mỗi tiêu chí bắt buộc một ví dụ

| Tiêu chí | CV | Với đơn | Lý do | Khách được đưa tới đâu |
|---|---|---|---|---|
| Tiếng Nhật | 09 Phạm Thị Thu Trang (TopCV hai cột) | DH-0001 | Có N5, đơn cần N4 | **Nhánh tư vấn học**: lộ trình lên N4; và vẫn **đạt DH-0007** (cần N5) |
| Bằng cấp | 26 Tạ Văn Tùng (đang học liên thông) | DH-0001 | Trung cấp, đơn cần cao đẳng; liên thông chưa xong không được tính | Gợi ý đơn khác: **đạt DH-0004** (cần trung cấp) |
| Tuổi | 04 Phạm Minh Tuấn | DH-0001 | 38 tuổi, đơn nhận 20–35 | Gợi ý đơn nhận tới 38–40 tuổi |
| Giới tính | 26 Tạ Văn Tùng | DH-0003 | Nam, đơn chỉ nhận nữ | Gợi ý đơn khác |
| Kinh nghiệm | 16 Lương Thị Kim Oanh | DH-0014 | Chưa đi làm, đơn cần ≥ 1 năm | Vẫn **đạt DH-0001** |
| Hạn nộp | 15 Bùi Thị Thanh Tâm | DH-0017 | Hồ sơ rất mạnh nhưng đơn đã quá hạn | Đơn quá hạn không cho đăng ký dù hồ sơ đạt mọi thứ khác |
| Trạng thái đơn | 20 Đặng Thị Mỹ Linh | DH-0019 | Đơn đang tạm dừng | Không cho đăng ký |

## 4. Không đạt nhiều tiêu chí

| CV | Với đơn | Lý do |
|---|---|---|
| 19 Phan Văn Hải — 40 tuổi | DH-0001 | N5, trung cấp, quá tuổi |
| 13 Nguyen Van Duc — gõ không dấu | DH-0001 | Chưa học tiếng Nhật, chỉ có bằng THPT — nhánh tư vấn học, và mời gặp nhân viên |

## Kịch bản ngắn khi trình diễn

1. Mở đơn **DH-0001**, cho khách **CV 20** → bảng đối chiếu toàn dấu đạt → đăng ký sơ bộ → hồ sơ vào hàng đợi nhân viên.
2. Cùng đơn đó, **CV 09** → chỉ vướng tiếng Nhật → nút đăng ký ẩn, hiện lộ trình học → đổi sang **DH-0007** thì đạt.
3. **CV 18** → tiếng Nhật “chưa rõ” vì NAT-TEST → vẫn được giữ, hệ thống hỏi thêm thay vì loại.
4. **CV 15** với **DH-0017** → hồ sơ rất mạnh vẫn bị chặn vì đơn đã quá hạn: quy tắc áp cho đơn, không chỉ cho người.
5. Ảnh chụp **CV 14** → hệ thống báo không đọc ảnh và mời khai tay.

## Lưu ý

Bảng trên dựng hồ sơ từ đáp án, tức coi như khách đã xác nhận đúng những gì CV ghi —
đúng như luồng thật, nơi khách xem lại và xác nhận hồ sơ trước khi đối chiếu. Khi đọc
CV bằng mô hình thật, trường nào bộ đọc chưa nhận sẽ thành “chưa rõ” cho tới khi khách
bổ sung: đáng chú ý nhất là **số năm kinh nghiệm phải tự tính từ khoảng thời gian**
(đợt đo 15/10 cho thấy bộ đọc thường để trống trường này), nên ví dụ “thiếu kinh
nghiệm” ở mục 3 sẽ hiện là “chưa rõ” nếu khách không khai thêm. Vì vậy khi trình diễn
luồng đọc CV thật, nên cho khách xem và sửa hồ sơ ở bước xác nhận.
