# Biên bản kiểm — Bảng đối chiếu ✓ và cửa xác nhận hồ sơ (08/10/2026)

Phạm vi: bước 2–3 của yêu cầu đổi giao diện tư vấn chuyên sâu (bảng đối chiếu, tổng
kết, điểm nguyện vọng, phân tích). Bước 4–6 (nối dữ liệu nhân viên, hiệu ứng, kiểm
chatbot chung) **chưa làm** trong đợt này.

## 1. Môi trường

| Mục | Giá trị |
|---|---|
| Database | `xkld_kiem_thu_0710` |
| Kho tệp | `F:/DoAnTotNghiep/_tam/kiem_thu_0710/storage` |
| Backend | `127.0.0.1:8020`, `ADVISOR_ENABLED=false`, `LLM_EXPLANATIONS_ENABLED=false`, proxy ra ngoài trỏ cổng chết |
| Website | `next dev -p 3100` |

**Xác minh đích trước khi ghi:** gắn dấu `[KIỂM THỬ]` vào tên đơn `DH-0001` **chỉ trong
database thử**, rồi đọc `GET /public/job-orders/DH-0001` từ máy chủ đang chạy — tên trả
về có dấu, tức máy chủ đọc đúng database thử. Không có dấu thì không chạy bước ghi nào.
Dấu vẫn còn trên đơn thử (thấy được trong ảnh).

**Database thật sau đợt kiểm** — không đổi: `candidate_profiles` 342, `advisor_turns` 197,
`recruitment_applications` 85, `support_requests` 83, `recommendation_logs` 294,
`staff_users` 2, `audit_logs` 679. `backend/storage/cv` 25 tệp, không tệp mới.

Log máy chủ thử: một dòng `Engine tư vấn: TẮT`, không lượt gọi mô hình nào.

## 2. Kiểm thử tự động

| Bộ | Kết quả |
|---|---|
| Backend `unittest discover` | 1260 ca, OK |
| Website `node --test` | 76 ca, OK (11 ca mới ở `tests/bangDoiChieu.test.cjs`) |
| Admin `node --test` | 35 ca, OK |
| `tsc --noEmit` website | sạch |
| `next build` website | sạch (lỗi `fetch failed` khi dựng trang tĩnh là do backend tắt lúc build — có từ trước) |
| Đột biến mới (`dot_bien --khong-ghi-db`) | 8/8 bắt được |

## 3. Kiểm trên trình duyệt

**Giới hạn:** điều khiển bằng sự kiện DOM và đọc DOM/kiểu tính toán; ảnh là ảnh chụp
khung nhìn thật của bản dựng. **Chưa phải** kiểm thao tác chuột thật. Ảnh "toàn trang"
của công cụ bị lặp khung đầu nên không dùng; chỉ dùng ảnh khung nhìn sau khi cuộn.

| Ca | Cách kiểm | Kết quả |
|---|---|---|
| Đơn trượt, hồ sơ đã xác nhận (`/tu-van/don/DH-0001`, 1280px) | DOM | 7/7 dòng đủ (nhật ký rút gọn được chấm lại); ✓ ở 6 dòng đạt, dòng Tiếng Nhật trống, chữ ẩn "Chưa đáp ứng hoặc chưa rõ"; tổng kết "6 đạt · 1 chưa đạt · 0 chưa rõ"; "không chấm điểm nguyện vọng" |
| Cùng trang, 390px | DOM + ảnh | Bảng `display:none`, 7 thẻ hiện; ✓ cùng vị trí; `scrollWidth` 375 ≤ 390, không phần tử tràn ngang |
| Đơn đạt có nguyện vọng | DOM | 7/7 ✓; "60 / 100 — … không phải khả năng trúng tuyển"; từng phần: khu vực +25/40, loại hình +30/30, lương +0/20 (chưa rõ), chi phí +5/10 (chưa rõ) |
| Hồ sơ chưa xác nhận | đổi trạng thái hồ sơ thử sang `extracted` trong DB thử, tải lại | Không bảng, không thẻ, không điểm, không kết luận; nút dẫn `/tu-van?don=DH-0001` |
| `/tu-van?don=DH-0001` sau xác nhận | DOM + ảnh | Thanh bước A–F, đang ở D; thẻ "Đơn bạn vừa xem" có nút tới bảng đối chiếu; trợ lý nằm **dưới** danh sách đơn; mỗi thẻ đơn có "Tư vấn riêng đơn này" |

Ảnh (`docs/nghiem_thu/anh_2026-10-08/`): `1_bang_doi_chieu_may_tinh_don_truot.png`,
`2_the_tieu_chi_dien_thoai_390.png`, `3_chua_xac_nhan_dien_thoai_390.png`,
`4_thanh_buoc_va_don_vua_xem.png`, `5_the_don_va_tro_ly_duoi_danh_sach.png`.

## 4. Hồi quy gửi lại không tạo trùng

Dùng cơ chế có sẵn (`booking_key`, yêu cầu đang mở). Gửi **hai lần** cùng một yêu cầu
gặp mặt (số thử của bộ kiểm, 09/10/2026 09:30) qua `POST /tu-van/v1/{phiên}/ho-tro`:

- Cả hai lần 201, cùng `HT-B048C6`, cùng lịch `TV-20261009-09CE`, cùng câu báo.
- Database thử: 1 yêu cầu, 1 lịch theo khóa, 1 thông báo cho mỗi mã.

Không tái hiện được lỗi → không sửa cơ chế.

## 5. Mô hình thật — ngân sách 8 lượt

Phân bổ công bố trước khi gọi: 8 ca × 1 lượt; model duy nhất `gemini-3.7-flash`; model
dự phòng tắt; đọc CV 0 lượt; không thử lại. Chốt chặn bằng code
(`scripts/ngan_sach_mo_hinh.py`, 6 ca kiểm) đếm mọi yêu cầu HTTP tới dịch vụ mô hình.

| Lượt | Kết quả |
|---|---|
| 1 | `ReadTimeout` |
| 2 | `ReadTimeout` → hai lỗi liên tiếp, **dừng** |

**8/8 ca CHƯA ĐO ĐƯỢC**, dùng 2/8 lượt. Không có câu trả lời mô hình hợp lệ nào; không
ca nào được tính đạt. Tệp: `2026-10-08_tu_van_mo_hinh_that.json`. Bộ 6 ca Agent
(`nghiem_thu_agent`) không chạy trong đợt này — vẫn CHƯA ĐO ĐƯỢC.

## 6. Còn mở

- Cửa xác nhận chặn ở **giao diện** và ở **khối gửi cho trợ lý**; API
  `tu_van_theo_don` vẫn trả kết quả cho hồ sơ chưa xác nhận (ai gọi thẳng API vẫn đọc được).
- Luật `cost.unknown = 5` trong `weights.json`: chi phí chưa rõ vẫn được 5/10 điểm. Giao
  diện ghi "(chưa rõ nguyện vọng)", nhưng con số vẫn cộng vào tổng — cần quyết.
- Thẻ đơn ghi "Còn thiếu: Khu vực: khu vực Hyogo, mong muốn Kantō" — đây là nguyện vọng
  lệch, không phải thông tin thiếu (có từ trước, chưa sửa).
- Lượt trả lời dự phòng cũ (trước 07/10) trong DB thử còn hiện khóa thô
  `experience_years…` — dữ liệu lịch sử, mã hiện tại đã sửa.
