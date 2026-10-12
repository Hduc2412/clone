# Biên bản nghiệm thu chốt — 07/10/2026 20:48:38

Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra
từng bộ đo, ở `2026-10-07_2048_nghiem_thu_chot.json` cùng thư mục.

## Bản code

| | |
|---|---|
| Dấu vân tay mã (trước) | `f93e0e337edd857ab122a81bb98c22ce50a9b636873fe4fedcd12681e1ebfa29` |
| Dấu vân tay mã (sau) | `f93e0e337edd857ab122a81bb98c22ce50a9b636873fe4fedcd12681e1ebfa29` |
| Hợp lệ | **có** |
| HEAD lúc chạy | `2034de3` (chưa commit — xem mục *Kiểm lại sau khi commit*) |
| Số file mã | 371 |
| Máy chủ khởi động | 07/10/2026 20:47:57 — sau file mã máy chủ mới nhất (07/10/2026 20:40:55) |
| Mô hình | đọc CV / chat: `gemini-2.5-flash` · tư vấn: `gemini-3.8-flash` · dự phòng: `gemini-3.7-flash` |

## Kết quả

| Bộ đo | Trạng thái | Kết quả | Thời gian |
|---|---|---|---:|
| Kiểm thử backend | ĐẠT | Ran 1245 tests in 21.819s · OK | 25.6 s |
| Xuyên suốt, dựng bằng quy tắc | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.1 s |
| Năm hồ sơ qua HTTP thật | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 2.1 s |
| Agent — chấm lại bản ghi đo mô hình | CHƯA ĐO ĐƯỢC | mã thoát 3 | 1.0 s |
| Hành trình đầy đủ từ upload CV thật | CHƯA ĐO ĐƯỢC | HÀNH TRÌNH: 0 chỗ hỏng | 38.2 s |
| Kiểm thử website (component) | ĐẠT | 65 đạt · 0 hỏng | 1.9 s |
| Kiểm thử hệ quản trị (component) | ĐẠT | 35 đạt · 0 hỏng | 2.5 s |

**Tổng: CHƯA ĐO ĐƯỢC**

## Phạm vi — đo gì, bằng gì, và CHƯA đo gì

| Phần | Đo bằng | Ở lượt này |
|---|---|---|
| Máy chủ, dữ liệu, phân quyền, chuỗi nghiệp vụ | kiểm thử backend + bộ HTTP | có |
| Đọc CV và lời trợ lý viết | **mô hình thật**, trong bộ hành trình | có — 2 lượt gọi |
| Giao diện: hành vi component, gồm ca lỗi mạng | kiểm thử component (`node --test`, API giả) | có |
| Giao diện trên **trình duyệt thật** — bố cục, thao tác, mạng thật | — | **KHÔNG** |

Lượt HTTP từ CV thật không đi qua giao diện. Kết quả của nó **không** được dùng
để tuyên bố giao diện đã nghiệm thu đầy đủ. Hai lỗi giao diện sửa ngày 06/10
(thử lại lượt mở đầu; mã phiên rỗng và lỗi không hiện ở bước kết quả) được
chứng minh bằng kiểm thử component và phép đột biến, chưa bằng một lượt bấm
trên trình duyệt.

## Phiên của lượt này

Mã lần chạy: `c152075b0191`. Mọi phiên dưới đây đã được ghi danh vào
`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.

- `5e1b9f22-d0ee-4e12-9bf7-6eaff4223112` — e2e_xuyen_suot
- `346f5996-34e6-45eb-8e10-dc656e882b55` — e2e_xuyen_suot
- `56f18776-83e1-4ea2-a8dd-1e0507084181` — e2e_xuyen_suot
- `8ef25c84-8540-4577-9423-551567f81659` — e2e_xuyen_suot
- `db5f2d1b-ebbf-48dc-9c3f-d59be23d6e09` — e2e_xuyen_suot
- `9f502456-9d37-4993-aaf1-0813fda1d4f2` — e2e_hanh_trinh

## Hành trình đầy đủ — đầu ra nguyên văn

```
Hành trình đầy đủ qua HTTP · http://127.0.0.1:8020
CV mẫu: 07_tran_thi_thu_ha.pdf (tên và số liệu đều là giả)
Gọi mô hình: 1 lượt cho bước đọc CV + 1 lượt hỏi trợ lý

[DB] MongoDB initialized successfully.
Tài khoản tạm (2 consultant + 1 manager): vừa tạo 3, dùng lại 0

   1. phiên 9f502456…
   2. CV 07_tran_thi_thu_ha.pdf → máy đọc 9 trường: ['birth_year', 'care_experience', 'education_level', 'experience_years', 'full_name', 'gender', 'japanese_level', 'major', 'phone']
   3. trợ lý: Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận tiếng Nhật N4, bằng cao đẳng, sinh năm 1999 và chuyên ngành Điều d…
   4. khách bổ sung ['phone'] + nguyện vọng → hồ sơ còn 9 trường
   5. đối chiếu: 5 đơn đạt, hạng 1 là DH-0001 (Tokyo)
      trợ lý [khong_goi_duoc]: Trợ lý tư vấn đang tạm thời chưa trả lời được, nên mình gửi bạn tóm tắt tự động từ kết quả đối chiếu — đây chưa phải câu trả lời riêng cho câu bạn vừa hỏi. Hệ t…
   6. đăng ký DH-0001 → hồ sơ tuyển HS-B19AE8
   7. yêu cầu HT-C4069F · lịch TV-20261010-4F60 · 2026-10-10 14:00
      bấm gửi lần hai → cùng yêu cầu, cùng lịch
   8. hai nhân viên tư vấn đăng nhập: e2e-tu-van-a@local.test, e2e-tu-van-b@local.test
   9. cả hai thấy HT-C4069F trong hàng đợi hỗ trợ
   10. A đọc HT-C4069F: bàn giao 1315 ký tự, lịch TV-20261010-4F60
   11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403
   12. cả hai thấy HS-B19AE8 · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình
   13. A đọc phiếu HS-B19AE8 (có tên, đơn DH-0001, N4) · B đọc → 403
   13b. A đọc hồ sơ ứng viên UV-F5258E và CV · B → bị chặn
   14. A đọc nhật ký: 18 đơn đã xét, 7 bị loại kèm lý do · B → 403
   15. A thử chuyển hồ sơ cho B → 403 (việc của quản lý)
   16. quản lý chuyển A → B: B xem được hồ sơ và nhật ký · A mất cả hai
   17. quản lý chuyển yêu cầu HT-C4069F A → B · A mất quyền trả lời/trả về · B trả về hàng đợi
[DB] MongoDB initialized successfully.

Trả về hàng đợi: 1 hồ sơ đăng ký, 0 yêu cầu hỗ trợ của lượt này.
[DB] MongoDB initialized successfully.

Đã xóa 3 tài khoản nhân viên tạm.

========================================================================
  ? KHÔNG ĐO ĐƯỢC — hỏi trợ lý: mô hình không trả lời (khong_goi_duoc) — chất lượng tư vấn bằng mô hình thật CHƯA được đo ở lượt này
HÀNH TRÌNH: 0 chỗ hỏng
```

## Kiểm lại sau khi commit

Checkout bản commit rồi chạy:

```bash
cd backend && venv/Scripts/python.exe -m scripts.dau_van_tay_ma
```

Ra `f93e0e337edd857ab122a81bb98c22ce50a9b636873fe4fedcd12681e1ebfa29` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.
