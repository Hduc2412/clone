# Biên bản nghiệm thu chốt — 06/10/2026 14:31:13

> **Ghi chú sau, 06/10 — đọc trước khi đọc biên bản này.**
> Chữ "ĐẠT" dưới đây **không** có nghĩa là lời tư vấn bằng mô hình thật đã được đo. Ở
> bước hỏi trợ lý, model chính hết giờ chờ và model dự phòng báo 503 — khách nhận câu
> ghép sẵn "trợ lý đang bận" (nguồn `khong_goi_duoc`). Bộ đo khi ấy chỉ kiểm câu trả lời
> không rỗng, nên vẫn thoát 0. Đã sửa: trường hợp này nay ra mã 3 — **CHƯA ĐO ĐƯỢC**. Bước
> đọc CV ở lượt này thì đã gọi mô hình thật và đạt.


Sinh tự động bởi `backend/scripts/nghiem_thu_chot.py`. Bản đầy đủ, kèm toàn bộ đầu ra
từng bộ đo, ở `2026-10-06_1431_nghiem_thu_chot.json` cùng thư mục.

## Bản code

| | |
|---|---|
| Dấu vân tay mã (trước) | `252db53df338099e36546ab2cb90f76a6d4fbea2942e63242e1aef162fa11d97` |
| Dấu vân tay mã (sau) | `252db53df338099e36546ab2cb90f76a6d4fbea2942e63242e1aef162fa11d97` |
| Hợp lệ | **có** |
| HEAD lúc chạy | `3a42598` (chưa commit — xem mục *Kiểm lại sau khi commit*) |
| Số file mã | 351 |
| Máy chủ khởi động | 06/10/2026 14:18:13 — sau file mã máy chủ mới nhất (06/10/2026 12:09:50) |
| Mô hình | đọc CV / chat: `gemini-2.5-flash` · tư vấn: `gemini-3.8-flash` · dự phòng: `gemini-3.7-flash` |

## Kết quả

| Bộ đo | Trạng thái | Kết quả | Thời gian |
|---|---|---|---:|
| Kiểm thử backend | ĐẠT | Ran 1158 tests in 33.138s · OK | 35.5 s |
| Xuyên suốt, dựng bằng quy tắc | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 0.6 s |
| Năm hồ sơ qua HTTP thật | ĐẠT | TỔNG: 5 ca · 0 chỗ hỏng | 1.5 s |
| Agent — chấm lại bản ghi đo mô hình | ĐẠT | TỔNG trên gemini-3.8-flash: ĐẠT 6/6 | 0.7 s |
| Hành trình đầy đủ từ upload CV thật | ĐẠT | HÀNH TRÌNH: 0 chỗ hỏng | 42.0 s |
| Kiểm thử website (component) | ĐẠT | 64 đạt · 0 hỏng | 1.1 s |
| Kiểm thử hệ quản trị (component) | ĐẠT | 15 đạt · 0 hỏng | 0.9 s |

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

Mã lần chạy: `4800035d5fa1`. Mọi phiên dưới đây đã được ghi danh vào
`storage/_e2e/so_phien.jsonl` và **được giữ lại** để xem trên màn hình quản trị.

- `621c7123-d579-4a11-8d3d-8fcd56355d31` — e2e_xuyen_suot
- `a8e11878-9d8d-49cd-8fe5-c160096e98eb` — e2e_xuyen_suot
- `7412e98e-9734-45fb-853f-1b8f70ae7549` — e2e_xuyen_suot
- `5112d48c-e49f-4403-9491-ffb01bd623ad` — e2e_xuyen_suot
- `2384fc73-1b61-4b67-9848-d295354d999a` — e2e_xuyen_suot
- `c9a0d91b-780f-43fa-98a1-5ee668c7399e` — e2e_hanh_trinh

## Hành trình đầy đủ — đầu ra nguyên văn

```
Hành trình đầy đủ qua HTTP · http://127.0.0.1:8020
CV mẫu: 07_tran_thi_thu_ha.pdf (tên và số liệu đều là giả)
Gọi mô hình: 1 lượt cho bước đọc CV + 1 lượt hỏi trợ lý

[DB] MongoDB initialized successfully.
Tài khoản tạm (2 consultant + 1 manager): vừa tạo 3, dùng lại 0

   1. phiên c9a0d91b…
   2. CV 07_tran_thi_thu_ha.pdf → máy đọc 9 trường: ['birth_year', 'care_experience', 'education_level', 'experience_years', 'full_name', 'gender', 'japanese_level', 'major', 'phone']
   3. trợ lý: Mình đã đọc CV của bạn. Hồ sơ hiện ghi nhận tiếng Nhật N4, bằng cao đẳng, sinh năm 1999 và chuyên ngành Điều d…
   4. khách bổ sung ['phone'] + nguyện vọng → hồ sơ còn 9 trường
   5. đối chiếu: 5 đơn đạt, hạng 1 là DH-0001 (Tokyo)
      trợ lý: Phần trợ lý tư vấn đang bận, mình chưa trả lời được câu này. Bạn thử lại sau ít phút giúp mình, hoặc để lại tin nhắn cho nhân viên tư vấn nhé.…
   6. đăng ký DH-0001 → hồ sơ tuyển HS-A234C8
   7. yêu cầu HT-088142 · lịch TV-20261009-42AC · 2026-10-09 14:00
      bấm gửi lần hai → cùng yêu cầu, cùng lịch
   8. hai nhân viên tư vấn đăng nhập: e2e-tu-van-a@local.test, e2e-tu-van-b@local.test
   9. cả hai thấy HT-088142 trong hàng đợi hỗ trợ
   10. A đọc HT-088142: bàn giao 1315 ký tự, lịch TV-20261009-42AC
   11. A nhận yêu cầu · B nhận lại → 409 nêu tên A · B trả lời thay → 403
   12. cả hai thấy HS-A234C8 · A nhận · B nhận lại → 409 · chỉ A có trong việc của mình
   13. A đọc phiếu HS-A234C8 (có tên, đơn DH-0001, N4) · B đọc → 403
   13b. A đọc hồ sơ ứng viên UV-384FB7 và CV · B → bị chặn
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

Ra `252db53df338099e36546ab2cb90f76a6d4fbea2942e63242e1aef162fa11d97` nghĩa là bản commit đúng là bản đã nghiệm thu ở đây.
