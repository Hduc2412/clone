# Biên bản nghiệm thu chốt — 06/10/2026 17:33:15

Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra
từng bộ đo, ở `2026-10-06_1733_nghiem_thu_chot.json` cùng thư mục.

## Bản code

| | |
|---|---|
| Dấu vân tay mã (trước) | `e66af13735cc7e97af45bfcfa41771de7833a4ec93ab45257dd4c6f1e0c7debd` |
| Dấu vân tay mã (sau) | `e66af13735cc7e97af45bfcfa41771de7833a4ec93ab45257dd4c6f1e0c7debd` |
| Hợp lệ | **có** |
| HEAD lúc chạy | `2034de3` (chưa commit — xem mục *Kiểm lại sau khi commit*) |
| Số file mã | 362 |
| Máy chủ khởi động | 06/10/2026 17:30:27 — sau file mã máy chủ mới nhất (06/10/2026 17:21:35) |
| Mô hình | đọc CV / chat: `gemini-2.5-flash` · tư vấn: `gemini-3.8-flash` · dự phòng: `gemini-3.7-flash` |

## Kết quả

| Bộ đo | Trạng thái | Kết quả | Thời gian |
|---|---|---|---:|
| Kiểm thử backend | ĐẠT | Ran 1205 tests in 25.841s · OK | 30.1 s |
| Xuyên suốt, dựng bằng quy tắc | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.2 s |
| Năm hồ sơ qua HTTP thật | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 2.0 s |
| Agent — chấm lại bản ghi đo mô hình | ĐẠT | TỔNG trên gemini-3.8-flash: ĐẠT 6/6 | 1.1 s |
| Hành trình đầy đủ từ upload CV thật | ĐẠT | HÀNH TRÌNH: 0 chỗ hỏng | 12.4 s |
| Kiểm thử website (component) | ĐẠT | 65 đạt · 0 hỏng | 2.0 s |
| Kiểm thử hệ quản trị (component) | ĐẠT | 32 đạt · 0 hỏng | 1.7 s |

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

Mã lần chạy: `0b91cd08f668`. Mọi phiên dưới đây đã được ghi danh vào
`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.

- `ebb8ae69-810b-4cb0-9c8d-088aadd9494b` — e2e_xuyen_suot
- `a940e1ec-580f-4600-9687-6fa18d320059` — e2e_xuyen_suot
- `1611cd3d-a2de-4b17-9dee-fea26b4319a0` — e2e_xuyen_suot
- `e97f8113-45de-448c-b43d-b8034c561aa4` — e2e_xuyen_suot
- `f05173f3-2bf6-4bdb-b147-9b1650c3a995` — e2e_xuyen_suot
- `afcc837e-0697-4926-909f-6de2fde80053` — e2e_hanh_trinh

## Hành trình đầy đủ — đầu ra nguyên văn

```
Hành trình đầy đủ qua HTTP · http://127.0.0.1:8020
CV mẫu: 07_tran_thi_thu_ha.pdf (tên và số liệu đều là giả)
Gọi mô hình: 1 lượt cho bước đọc CV + 1 lượt hỏi trợ lý

[DB] MongoDB initialized successfully.
Tài khoản tạm (2 consultant + 1 manager): vừa tạo 3, dùng lại 0

   1. phiên afcc837e…
   2. CV 07_tran_thi_thu_ha.pdf → máy đọc 9 trường: ['birth_year', 'care_experience', 'education_level', 'experience_years', 'full_name', 'gender', 'japanese_level', 'major', 'phone']
   3. trợ lý: Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận tiếng Nhật N4, bằng cao đẳng, sinh năm 1999 và chuyên ngành Điều d…
   4. khách bổ sung ['phone'] + nguyện vọng → hồ sơ còn 9 trường
   5. đối chiếu: 5 đơn đạt, hạng 1 là DH-0001 (Tokyo)
      trợ lý [mo_hinh]: Hệ thống đối chiếu cho thấy hồ sơ của bạn hiện đang đáp ứng các tiêu chí cơ bản của 11 đơn tuyển dụng, trong đó đơn DH-0001 tại Tokyo đang có điểm phù hợp cao n…
   6. đăng ký DH-0001 → hồ sơ tuyển HS-8CA730
   7. yêu cầu HT-830F57 · lịch TV-20261009-C169 · 2026-10-09 14:00
      bấm gửi lần hai → cùng yêu cầu, cùng lịch
   8. hai nhân viên tư vấn đăng nhập: e2e-tu-van-a@local.test, e2e-tu-van-b@local.test
   9. cả hai thấy HT-830F57 trong hàng đợi hỗ trợ
   10. A đọc HT-830F57: bàn giao 1230 ký tự, lịch TV-20261009-C169
   11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403
   12. cả hai thấy HS-8CA730 · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình
   13. A đọc phiếu HS-8CA730 (có tên, đơn DH-0001, N4) · B đọc → 403
   13b. A đọc hồ sơ ứng viên UV-74CC98 và CV · B → bị chặn
   14. A đọc nhật ký: 18 đơn đã xét, 7 bị loại kèm lý do · B → 403
   15. A thử chuyển hồ sơ cho B → 403 (việc của quản lý)
   16. quản lý chuyển A → B: B xem được hồ sơ và nhật ký · A mất cả hai
[DB] MongoDB initialized successfully.

Trả về hàng đợi: 1 hồ sơ đăng ký, 1 yêu cầu hỗ trợ của lượt này.
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

Ra `e66af13735cc7e97af45bfcfa41771de7833a4ec93ab45257dd4c6f1e0c7debd` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.
