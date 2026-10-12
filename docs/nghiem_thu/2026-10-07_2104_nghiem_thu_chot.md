# Biên bản nghiệm thu chốt — 07/10/2026 21:04:44

Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra
từng bộ đo, ở `2026-10-07_2104_nghiem_thu_chot.json` cùng thư mục.

## Bản code

| | |
|---|---|
| Dấu vân tay mã (trước) | `cd71501bbd07d92d8629de5d644802a3fa559fbb8fa4cc1e205efc1d79d6dc5a` |
| Dấu vân tay mã (sau) | `cd71501bbd07d92d8629de5d644802a3fa559fbb8fa4cc1e205efc1d79d6dc5a` |
| Hợp lệ | **có** |
| HEAD lúc chạy | `2034de3` (chưa commit — xem mục *Kiểm lại sau khi commit*) |
| Số file mã | 371 |
| Máy chủ khởi động | 07/10/2026 21:03:03 — sau file mã máy chủ mới nhất (07/10/2026 21:00:25) |
| Mô hình | đọc CV / chat: `gemini-2.5-flash` · tư vấn: `gemini-3.8-flash` · dự phòng: `gemini-3.7-flash` |

## Kết quả

| Bộ đo | Trạng thái | Kết quả | Thời gian |
|---|---|---|---:|
| Kiểm thử backend | ĐẠT | Ran 1247 tests in 20.758s · OK | 24.6 s |
| Xuyên suốt, dựng bằng quy tắc | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.0 s |
| Năm hồ sơ qua HTTP thật | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 2.1 s |
| Agent — chấm lại bản ghi đo mô hình | CHƯA ĐO ĐƯỢC | mã thoát 3 | 1.0 s |
| Hành trình đầy đủ từ upload CV thật | ĐẠT | HÀNH TRÌNH: 0 chỗ hỏng | 35.9 s |
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

Mã lần chạy: `f3ecd1c84b6f`. Mọi phiên dưới đây đã được ghi danh vào
`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.

- `b725591a-5432-4636-a71a-39f2e89d89ab` — e2e_xuyen_suot
- `afa299e1-2058-4ab4-b910-c7090701bc74` — e2e_xuyen_suot
- `1698ccc4-9482-4695-8781-6a0cd67361f9` — e2e_xuyen_suot
- `38f88a3d-32d9-4779-a69f-43586e9a564d` — e2e_xuyen_suot
- `7c3445e3-c606-4938-99f4-1e70c970c8b1` — e2e_xuyen_suot
- `8eb2fb47-9738-4a95-b8e5-92665ff60402` — e2e_hanh_trinh

## Hành trình đầy đủ — đầu ra nguyên văn

```
Hành trình đầy đủ qua HTTP · http://127.0.0.1:8020
CV mẫu: 07_tran_thi_thu_ha.pdf (tên và số liệu đều là giả)
Gọi mô hình: 1 lượt cho bước đọc CV + 1 lượt hỏi trợ lý

[DB] MongoDB initialized successfully.
Tài khoản tạm (2 consultant + 1 manager): vừa tạo 0, dùng lại 3

   1. phiên 8eb2fb47…
   2. CV 07_tran_thi_thu_ha.pdf → máy đọc 9 trường: ['birth_year', 'care_experience', 'education_level', 'experience_years', 'full_name', 'gender', 'japanese_level', 'major', 'phone']
   3. trợ lý: Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận tiếng Nhật N4, bằng cao đẳng, sinh năm 1999 và chuyên ngành Điều d…
   4. khách bổ sung ['phone'] + nguyện vọng → hồ sơ còn 9 trường
   5. đối chiếu: 5 đơn đạt, hạng 1 là DH-0001 (Tokyo)
      trợ lý [mo_hinh]: Hệ thống đối chiếu cho thấy bạn đã đáp ứng đủ các tiêu chí bắt buộc của 11 đơn tuyển dụng, trong đó có đơn DH-0001 tại Viện dưỡng lão Sakura ở Tokyo. Để hồ sơ đ…
   6. đăng ký DH-0001 → hồ sơ tuyển HS-89DA12
   7. yêu cầu HT-DD9A38 · lịch TV-20261010-9B48 · 2026-10-10 14:00
      bấm gửi lần hai → cùng yêu cầu, cùng lịch
   8. hai nhân viên tư vấn đăng nhập: e2e-tu-van-a@local.test, e2e-tu-van-b@local.test
   9. cả hai thấy HT-DD9A38 trong hàng đợi hỗ trợ
   10. A đọc HT-DD9A38: bàn giao 1230 ký tự, lịch TV-20261010-9B48
   11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403
   12. cả hai thấy HS-89DA12 · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình
   13. A đọc phiếu HS-89DA12 (có tên, đơn DH-0001, N4) · B đọc → 403
   13b. A đọc hồ sơ ứng viên UV-E94B9B và CV · B → bị chặn
   14. A đọc nhật ký: 18 đơn đã xét, 7 bị loại kèm lý do · B → 403
   15. A thử chuyển hồ sơ cho B → 403 (việc của quản lý)
   16. quản lý chuyển A → B: B xem được hồ sơ và nhật ký · A mất cả hai
   17. quản lý chuyển yêu cầu HT-DD9A38 A → B · A mất quyền trả lời/trả về · B trả về hàng đợi

========================================================================
HÀNH TRÌNH: 0 chỗ hỏng
```

## Kiểm lại sau khi commit

Checkout bản commit rồi chạy:

```bash
cd backend && venv/Scripts/python.exe -m scripts.dau_van_tay_ma
```

Ra `cd71501bbd07d92d8629de5d644802a3fa559fbb8fa4cc1e205efc1d79d6dc5a` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.
