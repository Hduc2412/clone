# Biên bản nghiệm thu chốt — 06/10/2026 14:23:38

> **Ghi chú sau, 06/10 — đọc trước khi đọc biên bản này.**
> Kết luận "CÓ CHỖ HỎNG" dưới đây là do **bộ đo sai**, không phải sản phẩm sai.
> Chỗ hỏng duy nhất — *"phiếu tóm tắt thiếu tên ứng viên ('Trần Thị Thu Hà')"* — là
> bộ đo so phiếu với cách viết trong đáp án, trong khi CV mẫu in tên bằng chữ hoa và hồ
> sơ (đã xác nhận, kèm chứng cứ nguyên văn) mang `TRẦN THỊ THU HÀ`. Phiếu chứa đúng tên
> ấy. Bộ đo đã sửa để so với tên trong hồ sơ của chính phiên. Lời tư vấn ở lượt này do
> **model dự phòng** `gemini-3.7-flash` viết, model chính hết giờ chờ.


Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra
từng bộ đo, ở `2026-10-06_1423_nghiem_thu_chot.json` cùng thư mục.

## Bản code

| | |
|---|---|
| Dấu vân tay mã (trước) | `7eb30909aa6ae002a0c372d4cbd742d562ed8ea1aa113df8aa94066a0408dc48` |
| Dấu vân tay mã (sau) | `7eb30909aa6ae002a0c372d4cbd742d562ed8ea1aa113df8aa94066a0408dc48` |
| Hợp lệ | **có** |
| HEAD lúc chạy | `3a42598` (chưa commit — xem mục *Kiểm lại sau khi commit*) |
| Số file mã | 351 |
| Máy chủ khởi động | 06/10/2026 14:18:13 — sau file mã máy chủ mới nhất (06/10/2026 12:09:50) |
| Mô hình | đọc CV / chat: `gemini-2.5-flash` · tư vấn: `gemini-3.8-flash` · dự phòng: `gemini-3.7-flash` |

## Kết quả

| Bộ đo | Trạng thái | Kết quả | Thời gian |
|---|---|---|---:|
| Kiểm thử backend | ĐẠT | Ran 1158 tests in 31.200s · OK | 33.6 s |
| Xuyên suốt, dựng bằng quy tắc | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 0.6 s |
| Năm hồ sơ qua HTTP thật | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.8 s |
| Agent — chấm lại bản ghi đo mô hình | ĐẠT | TỔNG trên gemini-3.8-flash: ĐẠT 6/6 | 0.5 s |
| Hành trình đầy đủ từ upload CV thật | HỎNG | HÀNH TRÌNH: 1 chỗ hỏng | 37.4 s |
| Kiểm thử website (component) | ĐẠT | 64 đạt · 0 hỏng | 1.2 s |
| Kiểm thử hệ quản trị (component) | ĐẠT | 15 đạt · 0 hỏng | 0.9 s |

**Tổng: HỎNG**

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

Mã lần chạy: `f41cbe7694e3`. Mọi phiên dưới đây đã được ghi danh vào
`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.

- `a0f73365-1286-4458-aaa4-77b358c2ddbf` — e2e_xuyen_suot
- `994abf85-a215-4314-995f-b041f0eedabe` — e2e_xuyen_suot
- `8ad25f68-8180-48fc-92f3-98b48a1f8641` — e2e_xuyen_suot
- `f7e4a96d-6223-4415-b4ea-1ff0bb36cf98` — e2e_xuyen_suot
- `e6c28dcc-f784-4a1e-a33b-d0b12fc95ce8` — e2e_xuyen_suot
- `81f926e4-0baf-4f5b-9ef7-474b147cefc2` — e2e_hanh_trinh

## Hành trình đầy đủ — đầu ra nguyên văn

```
Hành trình đầy đủ qua HTTP · http://127.0.0.1:8020
CV mẫu: 07_tran_thi_thu_ha.pdf (tên và số liệu đều là giả)
Gọi mô hình: 1 lượt cho bước đọc CV + 1 lượt hỏi trợ lý

[DB] MongoDB initialized successfully.
Tài khoản tạm (2 consultant + 1 manager): vừa tạo 3, dùng lại 0

   1. phiên 81f926e4…
   2. CV 07_tran_thi_thu_ha.pdf → máy đọc 9 trường: ['birth_year', 'care_experience', 'education_level', 'experience_years', 'full_name', 'gender', 'japanese_level', 'major', 'phone']
   3. trợ lý: Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận tiếng Nhật N4, bằng cao đẳng, sinh năm 1999 và chuyên ngành Điều d…
   4. khách bổ sung ['phone'] + nguyện vọng → hồ sơ còn 9 trường
   5. đối chiếu: 5 đơn đạt, hạng 1 là DH-0001 (Tokyo)
      trợ lý: Hệ thống đối chiếu cho thấy bạn đạt các điều kiện cứng của 11 đơn tuyển dụng, trong đó đơn DH-0001 tại Viện dưỡng lão Sakura ở Tokyo đang đứng đầu danh sách. Tu…
   6. đăng ký DH-0001 → hồ sơ tuyển HS-011212
   7. yêu cầu HT-C305C2 · lịch TV-20261009-2012 · 2026-10-09 14:00
      bấm gửi lần hai → cùng yêu cầu, cùng lịch
   8. hai nhân viên tư vấn đăng nhập: e2e-tu-van-a@local.test, e2e-tu-van-b@local.test
   9. cả hai thấy HT-C305C2 trong hàng đợi hỗ trợ
   10. A đọc HT-C305C2: bàn giao 1230 ký tự, lịch TV-20261009-2012
   11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403
   12. cả hai thấy HS-011212 · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình
   13b. A đọc hồ sơ ứng viên UV-0FFAD3 và CV · B → bị chặn
   14. A đọc nhật ký: 18 đơn đã xét, 7 bị loại kèm lý do · B → 403
   15. A thử chuyển hồ sơ cho B → 403 (việc của quản lý)
   16. quản lý chuyển A → B: B xem được hồ sơ và nhật ký · A mất cả hai
[DB] MongoDB initialized successfully.

Đã xóa 3 tài khoản nhân viên tạm.

========================================================================
  ! phiếu tóm tắt thiếu tên ứng viên ('Trần Thị Thu Hà')
HÀNH TRÌNH: 1 chỗ hỏng
```

## Kiểm lại sau khi commit

Checkout bản commit rồi chạy:

```bash
cd backend && venv/Scripts/python.exe -m scripts.dau_van_tay_ma
```

Ra `7eb30909aa6ae002a0c372d4cbd742d562ed8ea1aa113df8aa94066a0408dc48` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.
