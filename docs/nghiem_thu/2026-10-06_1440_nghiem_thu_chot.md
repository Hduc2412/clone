# Biên bản nghiệm thu chốt — 06/10/2026 14:40:14

> **Ghi chú sau, 06/10.** Đây là lượt chốt đạt trọn đầu tiên. Lời tư vấn ở bước hỏi trợ
> lý đến từ mô hình thật (nguồn `mo_hinh`), nhưng do **model dự phòng** `gemini-3.7-flash`
> viết — model chính `gemini-3.8-flash` hết giờ chờ (`advisor_turns.model` ghi đúng như
> vậy). Bảng "Mô hình" dưới đây là model ĐƯỢC CẤU HÌNH, không phải model đã trả lời.
> Nguyên văn câu hỏi và câu trả lời:
>
> *Hỏi:* Em còn thiếu gì để nộp đơn này ạ?
> *Đáp:* Hệ thống đối chiếu cho thấy hồ sơ của bạn đã đủ điều kiện nộp vào 11 đơn tuyển
> dụng, trong đó đơn DH-0001 tại Tokyo đang đứng đầu danh sách. Tuy nhiên, thông tin về
> mức lương mong muốn và ngân sách chuẩn bị của bạn hiện chưa được ghi nhận để tính điểm
> độ phù hợp chi tiết hơn. Bạn có thể chia sẻ thêm về mức lương kỳ vọng cũng như khả
> năng tài chính của mình không?


Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra
từng bộ đo, ở `2026-10-06_1440_nghiem_thu_chot.json` cùng thư mục.

## Bản code

| | |
|---|---|
| Dấu vân tay mã (trước) | `02bcab0e7674bffa55773664c95beb44cef59b6839a673109dbfc23845f8a983` |
| Dấu vân tay mã (sau) | `02bcab0e7674bffa55773664c95beb44cef59b6839a673109dbfc23845f8a983` |
| Hợp lệ | **có** |
| HEAD lúc chạy | `3a42598` (chưa commit — xem mục *Kiểm lại sau khi commit*) |
| Số file mã | 351 |
| Máy chủ khởi động | 06/10/2026 14:18:13 — sau file mã máy chủ mới nhất (06/10/2026 12:09:50) |
| Mô hình | đọc CV / chat: `gemini-2.5-flash` · tư vấn: `gemini-3.8-flash` · dự phòng: `gemini-3.7-flash` |

## Kết quả

| Bộ đo | Trạng thái | Kết quả | Thời gian |
|---|---|---|---:|
| Kiểm thử backend | ĐẠT | Ran 1162 tests in 19.071s · OK | 21.5 s |
| Xuyên suốt, dựng bằng quy tắc | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 0.6 s |
| Năm hồ sơ qua HTTP thật | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.8 s |
| Agent — chấm lại bản ghi đo mô hình | ĐẠT | TỔNG trên gemini-3.8-flash: ĐẠT 6/6 | 0.5 s |
| Hành trình đầy đủ từ upload CV thật | ĐẠT | HÀNH TRÌNH: 0 chỗ hỏng | 35.8 s |
| Kiểm thử website (component) | ĐẠT | 64 đạt · 0 hỏng | 1.1 s |
| Kiểm thử hệ quản trị (component) | ĐẠT | 15 đạt · 0 hỏng | 1.1 s |

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

Mã lần chạy: `aaf3c44fe852`. Mọi phiên dưới đây đã được ghi danh vào
`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.

- `3200bdf5-99fa-4236-b990-2fb4507cc57f` — e2e_xuyen_suot
- `e28eb0bf-8d35-490c-8b44-62582282d1e6` — e2e_xuyen_suot
- `f121c681-0420-45ed-8ccb-62a74a07e15e` — e2e_xuyen_suot
- `55ee7909-5d1e-4a43-9ac7-2735faada4cc` — e2e_xuyen_suot
- `3ba58362-0b4d-4f80-b191-743322779665` — e2e_xuyen_suot
- `055cd0bf-cde9-4a89-b1c9-77a6c5f86fda` — e2e_hanh_trinh

## Hành trình đầy đủ — đầu ra nguyên văn

```
Hành trình đầy đủ qua HTTP · http://127.0.0.1:8020
CV mẫu: 07_tran_thi_thu_ha.pdf (tên và số liệu đều là giả)
Gọi mô hình: 1 lượt cho bước đọc CV + 1 lượt hỏi trợ lý

[DB] MongoDB initialized successfully.
Tài khoản tạm (2 consultant + 1 manager): vừa tạo 3, dùng lại 0

   1. phiên 055cd0bf…
   2. CV 07_tran_thi_thu_ha.pdf → máy đọc 9 trường: ['birth_year', 'care_experience', 'education_level', 'experience_years', 'full_name', 'gender', 'japanese_level', 'major', 'phone']
   3. trợ lý: Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận tiếng Nhật N4, bằng cao đẳng, sinh năm 1999 và chuyên ngành Điều d…
   4. khách bổ sung ['phone'] + nguyện vọng → hồ sơ còn 9 trường
   5. đối chiếu: 5 đơn đạt, hạng 1 là DH-0001 (Tokyo)
      trợ lý [mo_hinh]: Hệ thống đối chiếu cho thấy hồ sơ của bạn đã đủ điều kiện nộp vào 11 đơn tuyển dụng, trong đó đơn DH-0001 tại Tokyo đang đứng đầu danh sách. Tuy nhiên, thông ti…
   6. đăng ký DH-0001 → hồ sơ tuyển HS-558B5B
   7. yêu cầu HT-FE18B6 · lịch TV-20261009-5E91 · 2026-10-09 14:00
      bấm gửi lần hai → cùng yêu cầu, cùng lịch
   8. hai nhân viên tư vấn đăng nhập: e2e-tu-van-a@local.test, e2e-tu-van-b@local.test
   9. cả hai thấy HT-FE18B6 trong hàng đợi hỗ trợ
   10. A đọc HT-FE18B6: bàn giao 1230 ký tự, lịch TV-20261009-5E91
   11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403
   12. cả hai thấy HS-558B5B · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình
   13. A đọc phiếu HS-558B5B (có tên, đơn DH-0001, N4) · B đọc → 403
   13b. A đọc hồ sơ ứng viên UV-583EB4 và CV · B → bị chặn
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

Ra `02bcab0e7674bffa55773664c95beb44cef59b6839a673109dbfc23845f8a983` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.
