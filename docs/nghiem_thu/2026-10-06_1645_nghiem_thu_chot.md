# Biên bản nghiệm thu chốt — 06/10/2026 16:45:06

Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra
từng bộ đo, ở `2026-10-06_1645_nghiem_thu_chot.json` cùng thư mục.

## Bản code

| | |
|---|---|
| Dấu vân tay mã (trước) | `c6328b30f974c5c828161afba6e7b2deaa6cf24ab8fd7eb2d83c8cd7707f80b6` |
| Dấu vân tay mã (sau) | `c6328b30f974c5c828161afba6e7b2deaa6cf24ab8fd7eb2d83c8cd7707f80b6` |
| Hợp lệ | **có** |
| HEAD lúc chạy | `3a42598` (chưa commit — xem mục *Kiểm lại sau khi commit*) |
| Số file mã | 358 |
| Máy chủ khởi động | 06/10/2026 16:38:19 — sau file mã máy chủ mới nhất (06/10/2026 16:27:39) |
| Mô hình | đọc CV / chat: `gemini-2.5-flash` · tư vấn: `gemini-3.8-flash` · dự phòng: `gemini-3.7-flash` |

## Kết quả

| Bộ đo | Trạng thái | Kết quả | Thời gian |
|---|---|---|---:|
| Kiểm thử backend | ĐẠT | Ran 1188 tests in 34.515s · OK | 41.4 s |
| Xuyên suốt, dựng bằng quy tắc | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.3 s |
| Năm hồ sơ qua HTTP thật | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.8 s |
| Agent — chấm lại bản ghi đo mô hình | ĐẠT | TỔNG trên gemini-3.8-flash: ĐẠT 6/6 | 0.8 s |
| Hành trình đầy đủ từ upload CV thật | ĐẠT | HÀNH TRÌNH: 0 chỗ hỏng | 24.3 s |
| Kiểm thử website (component) | ĐẠT | 65 đạt · 0 hỏng | 2.8 s |
| Kiểm thử hệ quản trị (component) | ĐẠT | 27 đạt · 0 hỏng | 2.2 s |

**Tổng: ĐẠT**

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

Mã lần chạy: `25c1508a44ad`. Mọi phiên dưới đây đã được ghi danh vào
`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.

- `22045535-44d3-42af-96e5-c18f659d3168` — e2e_xuyen_suot
- `e7bf37c0-cf53-4465-a0db-0e740b82073b` — e2e_xuyen_suot
- `d0ec8197-fae0-4b3b-b505-562ee08f0e24` — e2e_xuyen_suot
- `c6221662-434e-4493-80f0-68d8fdf46d90` — e2e_xuyen_suot
- `3eada3ab-d69c-4738-a9c8-341cdd3978b8` — e2e_xuyen_suot
- `09b9fcb6-9b2e-4ae8-8401-5302bc8ff3e6` — e2e_hanh_trinh

## Hành trình đầy đủ — đầu ra nguyên văn

```
Hành trình đầy đủ qua HTTP · http://127.0.0.1:8020
CV mẫu: 07_tran_thi_thu_ha.pdf (tên và số liệu đều là giả)
Gọi mô hình: 1 lượt cho bước đọc CV + 1 lượt hỏi trợ lý

[DB] MongoDB initialized successfully.
Tài khoản tạm (2 consultant + 1 manager): vừa tạo 3, dùng lại 0

   1. phiên 09b9fcb6…
   2. CV 07_tran_thi_thu_ha.pdf → máy đọc 9 trường: ['birth_year', 'care_experience', 'education_level', 'experience_years', 'full_name', 'gender', 'japanese_level', 'major', 'phone']
   3. trợ lý: Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận tiếng Nhật N4, bằng cao đẳng, sinh năm 1999 và chuyên ngành Điều d…
   4. khách bổ sung ['phone'] + nguyện vọng → hồ sơ còn 9 trường
   5. đối chiếu: 5 đơn đạt, hạng 1 là DH-0001 (Tokyo)
      trợ lý [mo_hinh]: Hệ thống đối chiếu cho thấy bạn có 11 đơn đủ điều kiện nộp, trong đó đơn DH-0001 tại Tokyo đang xếp hạng cao nhất. Tuy nhiên, hồ sơ của bạn hiện chưa có thông t…
   6. đăng ký DH-0001 → hồ sơ tuyển HS-5B15FC
   7. yêu cầu HT-1C0D2B · lịch TV-20261009-15E1 · 2026-10-09 14:00
      bấm gửi lần hai → cùng yêu cầu, cùng lịch
   8. hai nhân viên tư vấn đăng nhập: e2e-tu-van-a@local.test, e2e-tu-van-b@local.test
   9. cả hai thấy HT-1C0D2B trong hàng đợi hỗ trợ
   10. A đọc HT-1C0D2B: bàn giao 1230 ký tự, lịch TV-20261009-15E1
   11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403
   12. cả hai thấy HS-5B15FC · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình
   13. A đọc phiếu HS-5B15FC (có tên, đơn DH-0001, N4) · B đọc → 403
   13b. A đọc hồ sơ ứng viên UV-0E48CA và CV · B → bị chặn
   14. A đọc nhật ký: 18 đơn đã xét, 7 bị loại kèm lý do · B → 403
   15. A thử chuyển hồ sơ cho B → 403 (việc của quản lý)
   16. quản lý chuyển A → B: B xem được hồ sơ và nhật ký · A mất cả hai
[DB] MongoDB initialized successfully.

Đã xóa 3 tài khoản nhân viên tạm.

========================================================================
HÀNH TRÌNH: 0 chỗ hỏng
```

## Kiểm lại sau khi commit

Checkout bản commit rồi chạy:

```bash
cd backend && venv/Scripts/python.exe -m scripts.dau_van_tay_ma
```

Ra `c6328b30f974c5c828161afba6e7b2deaa6cf24ab8fd7eb2d83c8cd7707f80b6` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.
