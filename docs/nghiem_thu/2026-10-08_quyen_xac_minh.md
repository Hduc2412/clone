# Biên bản — Quyền, thông tin đã xác minh, cửa xác nhận, ngữ cảnh trợ lý (08/10/2026, chiều)

## 1. Môi trường và chốt an toàn

- Database thử `xkld_kiem_thu_0710`, kho tệp `F:/DoAnTotNghiep/_tam/kiem_thu_0710/storage`.
- Máy chủ thử chạy với `ADVISOR_ENABLED=false`, `LLM_EXPLANATIONS_ENABLED=false`, proxy ra ngoài trỏ cổng chết.
- Trước mỗi lần ghi: tiến trình phải đọc `settings.mongodb_db_name == xkld_kiem_thu_0710` **và** máy
  chủ phải trả tên đơn `DH-0001` có dấu `[KIỂM THỬ]` (chỉ database thử có dấu này). Không đạt thì dừng.
- Tài khoản nhân viên tạm (`tq-*`, `e2e-*`) tạo trong database thử, xóa đúng những cái đã tạo.
- **Database thật sau đợt** — không đổi: `candidate_profiles` 342, `advisor_turns` 197,
  `recruitment_applications` 85, `support_requests` 83, `recommendation_logs` 294, `staff_users` 2,
  `audit_logs` 679, `managed_leads` 87, `sessions` 224, `consultation_appointments` 80.
  `backend/storage/cv` 25 tệp, 0 tệp mới.

## 2. Tái hiện trên máy chủ thật — trước và sau khi sửa

Kịch bản `backend/scripts/tai_hien_quyen.py`, gọi đúng API giao diện gọi, bằng tài khoản `consultant` thật.

| Mã | Phép đo | Trước | Sau |
|---|---|---|---|
| HT-1 | B liệt kê yêu cầu A đang giữ qua `?status=dang_xu_ly` | LỖI (lộ SĐT, lời nhắn, bàn giao) | ĐÚNG |
| HT-2 | B gọi thẳng chi tiết yêu cầu A đang giữ | LỖI (200, đủ dữ liệu) | ĐÚNG (403) |
| HT-3 | Hàng đợi chờ nhận trả đủ bản ghi cho consultant | LỖI | ĐÚNG (bản tối thiểu) |
| HT-4 | Chi tiết yêu cầu chưa ai nhận | LỖI | ĐÚNG (bản tối thiểu) |
| HT-5/6 | Consultant đọc hội thoại của khách không liên quan | LỖI | ĐÚNG (lọc / 403) |
| HT-7 | Consultant tạo khách và giao cho người khác | LỖI (201) | ĐÚNG (403) |
| HT-8 | `internal_note` lọt ra API phía khách | ĐÚNG | ĐÚNG |
| HT-9 | Consultant đọc `internal_note` qua API nội bộ | ghi nhận | ghi nhận — **chờ quyết định** |
| HT-10 | Hàng đợi đăng ký trả họ tên + SĐT cho consultant | LỖI | ĐÚNG |
| HT-11 | Consultant đọc phiếu tóm tắt hồ sơ chưa ai nhận | LỖI (200) | ĐÚNG (403) |
| XM-1 | Khách sửa giá trị nhân viên đã xác minh | LỖI (bỏ qua im lặng) | ĐÚNG (giữ giá trị, lưu đề xuất, báo khách) |
| XM-2 | Nhân viên đổi giá trị đã xác minh: nhãn cũ có bám không | ĐÚNG | ĐÚNG (+ lịch sử nhãn) |
| XN-1 | API tư vấn theo đơn cho hồ sơ chưa xác nhận | LỖI (200, đủ bảng) | ĐÚNG (409 `ho_so_chua_xac_nhan`) |
| XN-2 | API lý do chi tiết cho hồ sơ chưa xác nhận | LỖI | ĐÚNG (409) |
| XN-3 | API lý do chi tiết sau khi sửa trình độ | LỖI (kết quả phiên bản cũ) | ĐÚNG |
| KN-1 | Tiến độ học vào ngữ cảnh trợ lý, "đang học" ≠ đã có | — | ĐÚNG |
| KN-2 | Kết quả đối chiếu theo phiên bản hồ sơ mới sau khi nhân viên sửa | — | ĐÚNG |
| KN-3 | Ngữ cảnh có chặng hồ sơ đăng ký đúng chặng khách thấy | — | ĐÚNG |
| KN-4 | Ngữ cảnh không lộ email nhân viên, ghi chú nội bộ, trạng thái nội bộ | — | ĐÚNG |
| KN-5 | Đề xuất của khách đóng sau khi nhân viên sửa đúng ô đó | — | ĐÚNG |

Kết quả: trước 13 lỗi / 16 phép đo; sau **0 lỗi / 21 phép đo**. Tệp: `2026-10-08_tai_hien_quyen_truoc_sua.json`,
`2026-10-08_tai_hien_quyen_sau_sua.json`.

Hai lần đo đầu của kịch bản có phép đo hỏng (đăng ký thử bị từ chối vì chưa xem danh sách đơn; một lần bị
giới hạn tần suất 429 do chạy liên tiếp) — đã sửa kịch bản / khởi động lại máy chủ thử, không tính các lần ấy.

**Mâu thuẫn với kết quả kiểm trước:** E2E bước 9–10 và ca `test_ai_cung_doc_duoc_phieu_cua_ho_so_chua_ai_nhan`,
`test_chua_ai_nhan_thi_ai_tra_loi_cung_duoc` cố ý khẳng định "ai cũng đọc được việc chưa ai nhận". Đã đổi theo quy
tắc mới (bản tối thiểu trước khi nhận) và ghi rõ trong ca kiểm.

## 3. Kiểm thử tự động

| Bộ | Kết quả |
|---|---|
| Backend `unittest discover` | 1294 ca, OK (32 ca mới qua route thật ở `tests/test_quyen_va_xac_minh.py`) |
| Website `node --test` | 78 ca, OK |
| Admin `node --test` | 35 ca, OK |
| `tsc` hai app, `next build` hai app | sạch |
| Đột biến mới (`dot_bien --khong-ghi-db`) | 14/14 bắt được |
| E2E hành trình `--khai-tay` trên database thử | 0 chỗ hỏng; gồm gửi lại không tạo trùng (cùng yêu cầu, cùng lịch), chuyển A → B; bước đọc CV **không đo** |

## 4. Trình duyệt (bản dựng thật, database thử)

Giới hạn: điều khiển và đọc bằng sự kiện DOM; ảnh là ảnh khung nhìn thật. Chưa phải kiểm thao tác chuột.

- `/tu-van/don/DH-0001` với hồ sơ thử đặt về chưa xác nhận: hiện thẻ mời xác nhận, không bảng, không báo lỗi.
- Cùng trang với hồ sơ đã xác nhận: dòng chi phí "+5/10 (bạn chưa nêu ngân sách, đơn chưa công bố chi phí —
  điểm trung lập…)".
- Quản trị đăng nhập consultant tạm: hàng đợi hỗ trợ và hàng đợi hồ sơ chỉ tên viết tắt, không SĐT, không
  nút "Xem phiếu"; trang hội thoại chỉ 2/7 phiên thử — đúng 2 phiên có số đặt lịch trùng 2 khách mà B phụ trách
  (2 khách đó được tạo trong lượt chạy **trước khi sửa** HT-7).
- Ảnh: `anh_2026-10-08/6_…`, `7_…`, `8_…`.
- Phát hiện: chữ website có chân (serif) do lệch mã băm lớp phông giữa HTML và CSS (xem `docs/thiet_ke/…/index.html`).

## 5. Mô hình thật — ngân sách 8 lượt

Công bố trước khi gọi: 9 ca xếp theo ưu tiên, tối đa 8 lượt HTTP, một model `gemini-3.7-flash`, tắt dự phòng,
0 lượt đọc CV, không thử lại. Lượt 1 và 2 đều `ReadTimeout` → dừng. **9/9 CHƯA ĐO ĐƯỢC**, dùng 2/8.
Tệp: `2026-10-08_tu_van_mo_hinh_that_dot2.json`. Trong ngày đã có 2 lần đo, cả hai dừng vì hết giờ chờ (12 giây).

## 6. Còn mở (lúc chiều 08/10 — hai mục đầu đã xử lý ở §7)

- ~~`internal_note` của đơn: mọi nhân viên đăng nhập đọc được — chưa đổi, chờ quyết định.~~ → §7.1
- ~~Người giữ yêu cầu hỗ trợ chưa tự có quyền đọc hồ sơ ứng viên/CV (bản bàn giao đã có tóm tắt).~~ → §7.1
- `application.japanese_level` trên hồ sơ đăng ký là bản chụp lúc đăng ký, sửa tay được, không đồng bộ với
  hồ sơ năng lực.
- Màn quản trị chưa có giao diện cho "đề xuất chờ" và "tiến độ học" (API đã có) — nằm trong mockup chờ duyệt.

## 7. Bản 2 (08/10 tối – 09/10): quyết định của chủ đồ án và ba điểm kiểm thêm

Số liệu dưới đây do chính đợt này đo; các số bên triển khai trước báo lại chưa được kiểm độc lập thì không dùng.

### 7.1 Quyết định đã áp

| Quyết định | Đã làm | Bằng chứng |
|---|---|---|
| `internal_note`: chỉ Admin/Manager đọc; thông tin tư vấn cần thì để trường riêng | Thêm `consultant_note` (mọi nhân viên đọc, không ra API công khai); `internal_note` bị gỡ khỏi bản trả cho consultant | JO-1 ĐÚNG; HT-9 (lúc chiều "GHI NHẬN") nay được JO-1 thay |
| "Đã đạt N4" tại trung tâm → "Hoàn thành chương trình N4 tại trung tâm — chưa xác minh chứng chỉ"; không tự coi tương đương chứng chỉ của đơn | Ghi tiến độ học **không** đổi `japanese_level`; nhãn riêng `chuong_trinh` ở API, thẻ hồ sơ, trang xác nhận và khối ngữ cảnh trợ lý | ca `test_quyen_va_xac_minh`; đột biến "hoàn thành chương trình bị ghi thành trình độ đối chiếu" bị bắt |
| Người giữ yêu cầu hỗ trợ đọc hồ sơ/CV **chỉ khi khách đồng ý bàn giao**; quyền theo người giữ hiện tại | Ô đồng ý trong biểu mẫu (mặc định không tích); quyền chỉ đọc, không sửa; chuyển việc thì người cũ mất quyền | HT-14, HT-15 ĐÚNG |
| Hàng đợi: tên viết tắt, chưa SĐT/CV/hội thoại | Bản tối thiểu cho việc chưa ai nhận | HT-3, HT-4, HT-10 ĐÚNG |
| Chờ AI 30 giây/lượt, ngân sách 8, dừng sau hai lỗi dịch vụ liên tiếp | `.env`: `ADVISOR_TIMEOUT_SECONDS` 12 → 30, thêm `ADVISOR_AGENT_TIMEOUT_SECONDS=30`; bộ đo in và ghi lại ngưỡng thực dùng | `thoi_gian_cho` trong tệp dot3: 30 / 30 |

### 7.2 Ba điểm kiểm thêm

1. **Quyền hội thoại không còn nối qua số điện thoại.** Nối bằng phiên rõ ràng: phiên chat chung mã với phiên
   hồ sơ / đăng ký / yêu cầu hỗ trợ (cookie đã ký), cộng lịch hẹn nhân viên được giao. HT-12 (hai khách trùng số:
   A chỉ thấy phiên của khách mình) và HT-13 (chuyển A → B: A mất quyền, B có quyền) ĐÚNG.
2. **Nhân viên ghi chưa chắc là đã xác minh.** Ô chỉ khóa khi `verification = verified` **và** căn cứ là bản gốc
   hoặc tra cứu chính thức. Ô nhân viên nhập không căn cứ thì khách sửa được, hệ thống ghi thông báo cho nhân viên
   (XM-3 ĐÚNG). Ô đã xác minh có căn cứ: giữ giá trị, lưu đề xuất, báo khách (XM-1 ĐÚNG).
3. **Phông chữ — giả thuyết cũ bị bác.** Giả thuyết "build rồi chạy dev trên cùng `.next`" **không** tái hiện được:
   - bản production dựng vào thư mục riêng (`NEXT_DIST_DIR=.next-kiem-prod`): mã lớp HTML và CSS khớp
     (`__variable_021202`), trình duyệt tải 13/13 phông, `body` là Be Vietnam Pro — đo lại 09/10 trên bản dựng mới nhất;
   - dev ở thư mục mới: khớp; build rồi dev trong cùng một thư mục **mới**: vẫn khớp;
   - chỉ thư mục `.next` cũ lệch (HTML `83907a`, CSS `021202`); mã cũ nằm trong `.next/server/vendor-chunks/next.js`
     và bộ nhớ đệm webpack bản client-production đề ngày 05/10. **Cơ chế gây lệch chưa xác định.**
   - Đã thêm giá trị dự phòng `var(--font-sans, system-ui)` để thiếu biến phông thì vẫn ra chữ không chân.
     Thư mục `.next` cũ **chưa xóa**; muốn hết lệch thì dựng lại nó.

### 7.3 Tái hiện trên máy chủ thật (database thử)

`2026-10-08_tai_hien_quyen_ban2.json`: **27 phép đo — 26 ĐÚNG, 1 GHI NHẬN (HT-9, xem 7.1), 0 LỖI.**
Các phép đo mới: HT-12…15, XM-3, JO-1. E2E hành trình `--khai-tay` trên database thử: 0 chỗ hỏng
(một lần đỏ do giới hạn tần suất 429 sau nhiều lượt chạy liền, khởi động lại máy chủ thử thì xanh — không tính lần đỏ đó).

### 7.4 Mô hình thật — dot3 (30 giây/lượt, ngân sách 8)

Công bố trước: 10 ca xếp ưu tiên (ba ca mới đứng đầu: `tien_do`, `chuong_trinh`, `chua_xac_nhan`), một model
`gemini-3.7-flash`, tắt dự phòng, 0 lượt đọc CV, không thử lại.

- Dùng 8/8 lượt: 200, 200, 200, 200, 200, **503**, 200, **ReadTimeout**. Hai lỗi không liền nhau nên luật dừng không bật;
  dừng vì hết ngân sách.
- Chấm lúc chạy: 5 ĐẠT, 1 HỎNG, 4 CHƯA ĐO ĐƯỢC (`huong_hoc` 503, `nhieu_y` hết giờ chờ, `chen_lenh` và
  `ngoai_pham_vi` hết lượt).
- Ca HỎNG (`chuong_trinh`) là **bộ chấm bắt nhầm**: câu trả lời nói đúng "hoàn thành khóa học **chưa** đồng nghĩa với việc
  đủ điều kiện tiếng Nhật của đơn", bộ chấm chỉ tìm cụm từ, không xét phủ định. Đã sửa bộ chấm.
- **Chấm lại ngoại tuyến** câu trả lời đã lưu bằng bộ chấm đã sửa (không gọi mô hình):
  `2026-10-08_tu_van_mo_hinh_that_dot3_cham_lai.json` — **6 ĐẠT, 0 HỎNG, 4 CHƯA ĐO ĐƯỢC**; tệp ghi kèm SHA-256 của tệp
  gốc. Đây là **chấm lại**, không phải một lượt đo mới.
- Bộ chấm nay có ca kiểm riêng (`tests/test_bo_cham_tu_van.py`, 9 ca) và 2 đột biến trong `dot_bien.py`, cả hai bị bắt.
  Lần đầu một đột biến **lọt** (ca kiểm chỉ đòi "có lỗi nào đó", luật khác che mất); đã siết ca kiểm đúng điểm hỏng.
- Giới hạn: đạt ở đây nghĩa là câu trả lời không phạm các mẫu lỗi đã định. **Chưa chứng minh trợ lý tư vấn đúng bằng dữ
  liệu tiến độ của khách** — dữ liệu mẫu ghép hồ sơ và tiến độ chưa nhất quán (hồ sơ mẫu chưa khai năm sinh/bằng cấp
  trong khi khối tiến độ ghi đã đủ điều kiện sơ bộ). Bộ `nghiem_thu_agent` vẫn **CHƯA ĐO**.

### 7.5 Giao diện theo bản thiết kế 08/10

Hướng hình thức: `_design/nhat-ban-20261008` của chủ đồ án; nghiệp vụ giữ của bản triển khai.

- Màu: đỏ trầm `#aa4339` thay `#cb1d1e` qua `tailwind.config.ts` (không còn mã màu rải rác); chữ/viền xanh rêu–ngà.
- Trang chủ: ảnh Phú Sĩ trôi chậm, **có nút dừng chuyển động**; hệ điều hành bật giảm chuyển động thì ảnh đứng yên.
- Phòng tư vấn theo đơn: hai cột — bảng đối chiếu (đứng yên, không trượt, không gập) và thẻ "Tư vấn dựa trên hồ sơ" có
  khung hỏi thêm; cột phải là thẻ hồ sơ (nhãn tiếng Nhật lấy nguyên của máy chủ) và thẻ điểm nguyện vọng (cùng luật:
  không đạt thì không điểm, chưa nêu nguyện vọng thì không số, điểm trung lập không phải điểm mạnh). Cột phải dính khi
  cuộn trên máy tính; màn hẹp thì xuống dưới.
- Bước khai hồ sơ `/tu-van`: ba trang gửi CV → làm rõ → xác nhận. **Chỉ sang trang khi khách bấm**; đọc xong CV không tự
  trượt; thiếu họ tên/trình độ thì không sang trang xác nhận; sang trang thì tiêu điểm tới tiêu đề trang mới; ba trang
  luôn được dựng (ẩn trang không xem) nên quay lại không gọi lại lượt mở đầu của trợ lý.

Kiểm trên trình duyệt (bản production thư mục riêng, database thử, đã thấy dấu `[KIỂM THỬ]` trước khi mở):
1280 và 390 px, không cuộn ngang; cột phải `position: sticky` đúng 96 px; tiêu điểm đúng tiêu đề trang ở cả hai đường
vào (bấm "Tiếp" và "Sửa hồ sơ" từ màn kết quả). **Giới hạn:** bấm qua công cụ tự động hóa trình duyệt, chưa phải chuột
người thật; chụp cả trang bị lặp khung nên chụp từng khung nhìn; không bấm "Xác nhận hồ sơ" (không ghi thêm dữ liệu).

Sửa ngay trong lúc kiểm: dòng trạng thái lặp ("Bạn đã xác nhận · Đã xác nhận"); vào từ "Sửa hồ sơ" thì tiêu điểm nằm ở
`BODY`; trang xác nhận ghi "Tỉnh mong muốn: Chưa cung cấp" dù hồ sơ có vùng Kantō (nay "Nơi mong muốn: Vùng Kantō").

Ảnh (bản dựng thật): `anh_2026-10-08/9_…` hai cột 1280; `10_…` cột phải dính khi cuộn; `11_…` 390 px (chụp **trước**
khi sửa dòng trạng thái); `12_…` trang làm rõ (chụp lúc đang trượt nên mờ); `13_…` trang xác nhận (chụp **trước** khi
sửa dòng vùng); `14_…` trang xác nhận 390 px sau khi sửa.

### 7.6 Kiểm thử tự động (09/10)

| Bộ | Kết quả |
|---|---|
| Backend `unittest discover` | 1316 ca OK (gồm 9 ca mới `test_bo_cham_tu_van`) |
| Website `node --test` | 83/83 |
| Admin `node --test` | 35/35 |
| `tsc` hai app; `next build` website | sạch. Một lần build bị Windows dừng mã 0xC0000409 ngay sau bước biên dịch, chạy lại thì qua — nguyên nhân chưa rõ |
| Đột biến mới | bản 2: 8/8 (sau khi siết một ca); bộ chấm: 2/2 (sau khi siết một ca); thử tay: bỏ cờ `scoreRanked` ở thẻ điểm → 2 ca website đỏ |

Một ca backend dò mã nguồn (`test_hai_man_hinh_khong_tu_suy_tu_score`) đỏ sau khi tách logic điểm; sửa **mã** để điều
kiện hiện số ghi tường minh `scoreRanked !== false`, không nới ca kiểm.

### 7.6b `consultant_note` trên màn quản trị (09/10)

Phát hiện khi rà lại: trường `consultant_note` lập ra cho consultant nhưng **không hiện ở đâu** trên màn quản trị — chỉ
có trong biểu mẫu sửa, mà biểu mẫu chỉ hiện cho Admin/Manager (API sửa cũng chỉ nhận hai vai trò này). Ghi chú cũ của
tôi "biểu mẫu vẫn hiện ô `internal_note` trống cho consultant" là **sai**: consultant không thấy biểu mẫu.

Đã thêm khối chỉ đọc trên trang chi tiết đơn: "Thông tin cho tư vấn viên" cho mọi nhân viên; "Ghi chú nội bộ" chỉ khi
người xem là Admin/Manager (nội dung lấy từ phản hồi máy chủ, máy chủ đã gỡ khóa `internal_note` với consultant).

Kiểm (bản production, database thử, hai tài khoản tạm `tq-ui-*`, ghi chú thử đặt vào DH-0001 qua API rồi trả về giá trị
cũ, tài khoản đã xóa — còn 0):

| Người xem | API có khóa `internal_note` | Trang hiện ghi chú tư vấn | Trang hiện ghi chú nội bộ | Biểu mẫu sửa |
|---|---|---|---|---|
| consultant | không | có | không | không |
| manager | có | có | có | có |

Ảnh: `anh_2026-10-08/15_…` (consultant), `16_…` (manager). Đổi vai bằng gọi thẳng `/auth/login` trong trang (nút "Thoát"
nằm ngoài khung nhìn, công cụ không bấm được).

### 7.7 Còn mở

- ~~Nhập Excel đơn hàng chưa có cột `consultant_note`.~~ → §8 Phase 2
- ~~Consultant chưa đọc được điều kiện, lương, chi phí của đơn trên màn quản trị.~~ → §8 Phase 1
- ~~Màn quản trị chưa đổi theo hướng hình thức mới.~~ → §8 Phase 5
- ~~Thư mục `.next` cũ của website vẫn lệch mã phông, chưa dựng lại.~~ → §8 Phase 4
- `nghiem_thu_agent` CHƯA ĐO (Phase 6). ~~Dữ liệu mẫu của bộ đo tiến độ chưa nhất quán.~~ → §8 Phase 3
- Database thật 09/10: không đổi (`candidate_profiles` 342, `advisor_turns` 197, `recruitment_applications` 85,
  `support_requests` 83, `recommendation_logs` 294, `staff_users` 2, `audit_logs` 679, `managed_leads` 87, `sessions` 224,
  `consultation_appointments` 80); `backend/storage/cv` 25 tệp.

## 8. Làm theo phase (12/10)

Thứ tự đã chốt: (1) consultant đọc nội dung đơn → (2) cột `consultant_note` khi nhập Excel → (3) dữ liệu mẫu bộ đo
tiến độ → (4) phông chữ, dựng lại `.next` cũ sau khi chép bằng chứng → (5) màn quản trị theo hướng giao diện mới →
(6) đo `nghiem_thu_agent` bằng mô hình thật (tối đa 8 lượt, công bố phân bổ trước).

### Phase 1 — consultant đọc nội dung đơn (xong)

- `components/admin/JobOrderSummary.tsx` (mới): bản chỉ đọc, tách **điều kiện bắt buộc** (loại ứng viên) khỏi **thông tin
  tham khảo** (lương, chi phí, phụ cấp, lịch — không loại ai); trường trống ghi "Chưa có thông tin"; nhãn lấy từ
  `order.labels`; không đọc `internal_note`.
- Trang chi tiết đơn: Admin/Manager thấy biểu mẫu sửa như cũ; vai trò khác thấy bản chỉ đọc. Chờ biết vai trò rồi mới vẽ.
- Kiểm tự động: `tests/jobOrderSummary.test.cjs` 6 ca (chọn bản theo vai trò; thứ tự nhóm; lương nằm ở nhóm tham khảo;
  không in `internal_note` dù dữ liệu lỡ mang theo; định dạng). Đột biến "cho cả manager thấy bản chỉ đọc" → 1 ca đỏ.
  Admin 41/41, `tsc` sạch, `next build` sạch.
- Kiểm trên bản production (database thử, đã thấy `[KIỂM THỬ]`; tài khoản tạm `tq-ui-*` đã xóa, còn 0; ghi chú DH-0001 đã
  trả giá trị cũ): đọc DOM thấy đủ hai nhóm, lương "195.000 ¥ – 215.000 ¥ / tháng" ở nhóm tham khảo, không có ghi chú nội
  bộ, không có biểu mẫu. Lúc làm Phase 1 công cụ trình duyệt báo tab "chưa vẽ" nên chưa chụp được; ảnh chụp sau ở Phase 5:
  `anh_2026-10-08/24_…`.
- Môi trường: sau khi máy khởi động lại, dịch vụ MongoDB (khởi động tự động) đang dừng; đã bật lại bằng `Start-Service`.

### Phase 2 — cột "Thông tin cho tư vấn viên" khi nhập Excel (xong)

- Bộ nhập (`app/services/job_order_import.py`) thêm cột không bắt buộc "Thông tin cho tư vấn viên" → `consultant_note`;
  file mẫu tải từ màn quản trị có cột này.
- **Rủi ro tìm thấy khi làm:** hai trường ghi chú được phép xóa về rỗng, nên dòng cập nhật mang `None` là xóa thật. Thêm
  cột theo cách thường thì nhập một file làm trước 12/10 để cập nhật đơn sẽ **xóa sạch** ghi chú tư vấn viên đã nhập
  trên màn quản trị (cùng lỗ với "Ghi chú nội bộ" nếu file thiếu cột đó). Đã chốt: file **không có cột** thì không đụng
  giá trị đang lưu; có cột mà ô trống thì xóa (ý người sửa file).
- Kiểm tự động: 5 ca mới trong `tests/test_job_order_import.py` (gồm ca chứng minh tầng dữ liệu giữ `None` — lý do cần
  chốt); đột biến "bỏ chốt" bị bắt 1/1. Backend 1321/1321.
- Kiểm trên máy chủ thử, chỉ chạy thử (`dry_run`), tài khoản manager tạm đã xóa:

  | File | Có khóa `consultant_note` | Có khóa `internal_note` |
  |---|---|---|
  | cũ, không có hai cột ghi chú | không (giữ giá trị đang lưu) | không |
  | mới, ô có giá trị | có, đúng giá trị | có |
  | mới, ô trống | có, `None` (xóa có chủ ý) | có |

  Lần chạy đầu cho kết quả cũ vì máy chủ thử bật **trước** khi sửa mã — khởi động lại rồi mới tính; script kiểm lúc đầu đọc
  nhầm sheet hướng dẫn nên báo "file mẫu không có cột" — sửa script, đọc đúng sheet `DonHang` thì có.
- File chủ `Tailieu/DonHang/MauDonHang_ChuDe.xlsx`: **không sửa** (băm trước/sau như nhau); đọc thử không thiếu cột bắt
  buộc, hiện 0 dòng dữ liệu. `Tailieu/DonHang/HUONG_DAN.md`: thêm mục cột mới và quy tắc giữ/xóa; sửa mục "Ghi chú nội
  bộ" cho đúng phạm vi đọc từ 08/10.

### Phase 3 — dữ liệu mẫu của hai ca tiến độ (xong; chưa gọi mô hình)

- **Mâu thuẫn cũ (dot3):** ca `tien_do` ghép khối hồ sơ chung (tiếng Nhật "Chưa học", chưa khai năm sinh/bằng cấp, kết
  luận "chưa đạt") với khối tiến độ viết tay "N4 — có chứng chỉ, đã đối chứng" + "Đủ điều kiện sơ bộ"; ca `chuong_trinh`
  ghép cùng hồ sơ "Chưa học" với "N5 tự khai". Mô hình nhận hai bản trái nhau về cùng một người.
- **Nay:** `tests/hau_kiem_mau.cac_khoi_tien_do(ma)` — mỗi ca **một hồ sơ**, mọi khối sinh từ nó bằng mã thật:
  khối hồ sơ (`context_builder`), khối tiến độ (`tien_do.render`, chặng lấy từ `CHANG_CUA_TRANG_THAI`), khối đối chiếu
  (engine + `advice.build`), khối đơn (`order_context`), khối đơn khác (engine trên DH-0001 + DH-0016).
  - `tien_do`: N4 nhân viên đối chứng bản gốc, đang học lên N3, sinh 1999, Cao đẳng, đăng ký DH-0001 trạng thái
    `eligible` → "Đủ điều kiện sơ bộ"; đối chiếu: **đạt** đủ điều kiện bắt buộc (khớp với chặng).
  - `chuong_trinh`: N5 tự khai, hoàn thành chương trình N4 tại trung tâm (KH-0001) chưa xác minh chứng chỉ; đối chiếu:
    **chưa đạt** tiếng Nhật N4, các mục khác đạt; chưa đăng ký.
  - Các ca khác vẫn dùng bộ khối chung (hồ sơ "Chưa học"), bộ ấy tự nhất quán.
- Bộ đo `scripts/danh_gia_tu_van_that.py` bỏ hai khối viết tay, lấy bộ khối mới cho hai ca này.
- **Lỗi thật tìm thấy khi dựng lại:** `app/consultation/order_context.py` tra yêu cầu giới tính của đơn bằng bảng giới
  tính của **ứng viên** (`GENDER_LABELS`, chỉ có nam/nữ) → mọi đơn "không yêu cầu giới tính" đưa cho mô hình dòng
  `Giới tính: khong_yeu_cau` (mã máy). Áp cho phòng tư vấn theo đơn thật, không chỉ dữ liệu mẫu. Đã đổi sang
  `GENDER_PREF_LABELS`; ca kiểm mới + đột biến bị bắt 1/1.
- Kiểm tự động: `tests/test_bo_cham_tu_van.py` thêm 6 ca nhất quán (không khối hồ sơ/đối chiếu nào còn "Chưa học"; chặng
  khớp kết luận; tuổi 27 do engine tính từ năm sinh; không lọt mã máy; bộ đo đưa đúng bộ khối cho mô hình — thay lời gọi
  mô hình bằng bản giả ghi lại đầu vào). Backend 1327/1327.
- Giới hạn: đây là chuẩn bị dữ liệu. Mô hình **chưa** được gọi lại trên bộ khối mới — đo ở Phase 6.

### Phase 4 — phông chữ (xong)

**Bằng chứng giữ lại trước khi dựng lại:** chép nguyên `.next` cũ (144 MB) sang
`_tam/bang_chung_phong_0810/next-cu`. Mã băm cũ `83907a` nằm ở `cache/webpack/client-production/{0,2,3,14}.pack`,
`cache/webpack/server-production/0.pack` và `server/vendor-chunks/next.js` (đầu ra dev); mã đúng `021202` ở
`static/css/app/layout.css` và `static/chunks/app/layout.js` (`_tam/bang_chung_phong_0810/noi_chua_ma_bam.txt`).

**Dựng lại `.next` mặc định, dùng lại bộ nhớ đệm cũ:**

| Chế độ | Mã trong HTML | Mã trong CSS | Phông nạp |
|---|---|---|---|
| `next build` + `next start` | `021202` | `021202` | — |
| `next dev` trên cùng `.next` (sau build) | `021202` | `021202` | 13/13, `body` = Be Vietnam Pro |

Lệch mã **không tái hiện được** nữa, kể cả khi dùng lại đúng bộ nhớ đệm có mã cũ. Kết luận giữ nguyên: nguyên nhân gốc
**chưa xác định**; dựng lại thì hết; bằng chứng còn trong `_tam/`.

**Lỗi mới thấy trên ảnh chụp (đã sửa):** dòng nhấn nghiêng "Bắt đầu từ bạn." hiện thành "Bă´t đâ`u" (ảnh `17_…`). Mã nguồn
đúng dạng NFC (`ắ` U+1EAF, `ầ` U+1EA7); nguyên nhân là **Georgia trên Windows thiếu chữ hai dấu**, trình duyệt tách
thành chữ gốc + dấu rời. Chữ một dấu ("Chọn đúng hướng.") không lỗi nên trước đó không thấy. Đổi `.chu-nhan`, chữ "DC"
ở logo và chữ viết tắt ở thẻ hồ sơ sang **Gelasio** (Google Fonts, cùng số đo với Georgia, có bộ tiếng Việt) nạp qua
`next/font`, Georgia chỉ còn là dự phòng (ảnh `18_…` dev, `19_…` bản production). Ca kiểm `tests/phongChu.test.cjs`
(không chỗ nào để Georgia đứng đầu; phông có chân nạp kèm bộ tiếng Việt) — đột biến đặt lại Georgia → đỏ.

Bản production: HTML/CSS cùng `021202` (Be Vietnam Pro) và `7eca95` (Gelasio); trình duyệt nạp 13 mặt Be Vietnam Pro,
4 mặt Gelasio. Website 85/85, `tsc` sạch.

**Rủi ro ghi nhận:** `next build` tải phông từ Google lúc dựng. Một lần dựng hỏng trong `next/font` (URL tệp phông không
đọc được đuôi); gọi lại đúng các hàm ấy bên ngoài thì mọi URL đều `.woff2`, dựng lại lần hai thì qua. Máy dựng không có
mạng thì `next build` sẽ hỏng — cần lưu ý khi đóng gói Docker.

### Phase 5 — màn quản trị theo hướng hình thức 08/10 (xong)

Theo `_design/nhat-ban-20261008/nhan-vien.png`: nền ngà, chữ xanh rêu, thanh bên sáng, đỏ trầm cho hành động.

- **Token màu** trong `admin-frontend/tailwind.config.ts`, cùng bộ với website (`brand`, `slate` xanh rêu, `reu`, `kem`,
  `ink`). Thay toàn bộ mã màu rải rác: `#cb1d1e` 49 chỗ, `#171b22` 9, `#a81718`/`#b51718` 4, nền 2; viền khi chọn ô nhập
  `focus:border-red-400` 24 chỗ → `brand-400`. **Giữ** `red-*` của Tailwind cho ô báo lỗi — màu lỗi không trùng màu nút.
- **Phông**: Be Vietnam Pro + Gelasio qua `next/font` (trước đó màn quản trị dùng phông hệ thống); số lớn ở trang tổng quan
  và dòng nhấn "Đúng bước tiếp theo." dùng Gelasio.
- **Thanh bên sáng**, dấu "DC", mục đang mở nền xanh nhạt, `aria-current="page"`. Trang đăng nhập nền ngà.
- **Lỗi thật sửa cùng lúc:** thanh bên không cuộn được — 16 mục cao hơn màn hình ≤ ~900 px, khối tài khoản bị đẩy ra ngoài,
  **nút "Thoát" không bấm được** (đúng lý do lần kiểm trước công cụ không bấm được "Thoát"). Thêm `min-h-0 overflow-y-auto`.
  Đo ở 1280×800: nút "Thoát" ở y 742–766, trong khung; danh sách mục cuộn được.
- **Lỗi nhỏ:** chữ viết tắt ở khối tài khoản lấy cả dấu ngoặc ("Kiểm giao diện consultant (tạm)" → "C("). Nay chỉ lấy tiếng
  bắt đầu bằng chữ cái (→ "DC"); không dùng `\p{L}` vì cấu hình biên dịch nhắm ES5.
- Kiểm tự động: `tests/giaoDienQuanTri.test.cjs` 4 ca (thẻ `<nav>` có `overflow-y-auto` + `min-h-0`, soi bằng bộ phân tích
  TypeScript; không còn mã màu cũ; ô báo lỗi dùng `red-*` không dùng `brand-*`; phông nạp kèm bộ tiếng Việt). Đột biến bỏ
  cuộn → đỏ. Admin 45/45, `tsc` sạch, `next build` sạch.
- Kiểm trên bản production (database thử, đã thấy `[KIỂM THỬ]`; đăng nhập **bằng biểu mẫu** — điền ô và bấm nút qua công cụ
  tự động hóa, không gọi thẳng API; tài khoản tạm đã xóa, còn 0; ghi chú DH-0001 đã trả về giá trị cũ): đăng nhập, tổng quan,
  hàng đợi hỗ trợ (vẫn bản tối thiểu: tên viết tắt, không SĐT, không lời nhắn), chi tiết đơn của consultant; 390 px: thanh
  bên ẩn (`translateX(-288px)`), không cuộn ngang. Ảnh `20_…`–`24_…`.
- Chưa làm: các trang quản trị còn lại chỉ đổi màu và phông qua token, chưa dựng lại bố cục riêng từng trang theo bản thiết kế.

### Phase 6 — đo mô hình thật

**Chuẩn bị (không gọi mô hình):** `nghiem_thu_agent` trước đây chỉ đếm **ca** (`--gioi-han`), không đếm yêu cầu HTTP, không
dừng khi 429 hay hai lỗi liên tiếp, và để model dự phòng bật. Nay đi qua `NganSach` như `danh_gia_tu_van_that`
(`--ngan-sach`, tắt dự phòng mặc định). Kiểm bằng proxy ra ngoài trỏ cổng chết (không yêu cầu nào rời máy), trần 3: hai
lượt `ConnectError` → dừng, lượt thứ ba không gọi, bảng kết quả không đổi. Tìm thêm khi chạy bộ kiểm thử: `NganSach.gan()`
vá `httpx` cho cả tiến trình mà không trả lại, và `main()` tắt model dự phòng mà không trả lại — ca kiểm thử gọi `main()`
để lại cả hai cho các ca sau (5 ca đỏ khi chạy cả bộ, xanh khi chạy riêng). Thêm `NganSach.go()` và trả cấu hình trong
`finally`; 2 ca kiểm mới. Backend 1330/1330. Bảng kết quả cũ đo bằng prompt cũ (`35e724`), prompt hiện tại `13c8f3` →
6 ca CHƯA ĐO.

**Công bố trước khi gọi (12/10/2026 10:40):** model `gemini-3.8-flash` (đúng `ADVISOR_MODEL` của ứng dụng),
**tắt dự phòng**; cả đợt **tối đa 8 lượt HTTP**: `nghiem_thu_agent` 6 ca (FACT-01…04, TIEM-01, TIEM-02), trần 6;
`danh_gia_tu_van_that` 2 ca tiến độ (`tien_do`, `chuong_trinh` — dữ liệu Phase 3), trần 2. 0 lượt đọc CV, không thử lại,
chờ 30 giây/lượt, nghỉ 10 giây giữa hai lượt. Gặp 429 hoặc hai lỗi dịch vụ liên tiếp thì dừng; bộ đầu dừng vì lý do ấy thì
không chạy bộ sau. Ca thiếu kết quả ghi CHƯA ĐO ĐƯỢC, không tính là đạt.

**Kết quả (12/10):** bộ `nghiem_thu_agent` dùng **2/8** lượt: lượt 1 `ReadTimeout` (quá 30 giây), lượt 2 **503** "This model
is currently experiencing high demand". Hai lỗi dịch vụ liên tiếp → **dừng theo luật**; FACT-03…TIEM-02 không gọi. Theo
luật đã công bố, **không chạy** bộ `danh_gia_tu_van_that` và **không thử lại**. Nhật ký lượt gọi:
`2026-10-12_nghiem_thu_agent_ngan_sach.json`. Bảng kết quả `tests/fixtures/tu_van/ket_qua_agent.json` không đổi (ca không
gọi được không ghi).

| Bộ | Ca | Kết quả |
|---|---|---|
| `nghiem_thu_agent` | FACT-01…04, TIEM-01, TIEM-02 | **6/6 CHƯA ĐO ĐƯỢC** |
| `danh_gia_tu_van_that` (ca tiến độ, dữ liệu Phase 3) | `tien_do`, `chuong_trinh` | **CHƯA ĐO** — không chạy vì bộ trước dừng |

Không có kết luận nào về chất lượng của Agent hay của trợ lý trên bộ khối tiến độ mới từ đợt này. Còn 6 lượt trong ngân sách
của đợt, chưa dùng; đo lại cần chủ đồ án đồng ý mở đợt mới (dịch vụ báo quá tải).

## 9. Hạn nộp và chỉ tiêu của đơn (12/10)

**Yêu cầu:** đơn hết hạn thì ẩn và báo Admin gỡ; đếm chỉ tiêu, đủ thì ẩn với trạng thái "đã hoàn thành chỉ tiêu"; đăng ký
không đổi gì, chỉ cập nhật khi nhân viên xác nhận thành công; số chỉ tiêu còn lại đưa vào khung chat; cảnh báo sắp hết hạn
10 ngày. **Chủ đồ án chốt:** trừ khi hồ sơ "Trúng tuyển"; người đã tính rút/hủy thì trả chỉ tiêu, báo Admin, **không** tự mở
lại; số còn lại hiện ở khung chat **và** trang đơn.

**Có sẵn từ trước:** đơn quá hạn đã tự ẩn khỏi website (lọc lúc đọc). `increment_hired` (tăng số đã tuyển, tự chuyển "Đủ số
lượng") đã viết nhưng **không chỗ nào gọi** — `hired_count` luôn 0.

**Đã làm:**
- `services/chi_tieu.py`: "Trúng tuyển" trừ một chỉ tiêu, mỗi hồ sơ chỉ tính một lần (dấu `chi_tieu` đặt nguyên tử); rút/hủy
  sau khi đã tính → trả lại, báo Admin; hồ sơ không gắn đơn thì bỏ qua; lỗi không làm hỏng thao tác đổi trạng thái hồ sơ.
  Nối vào cả hai chỗ đổi trạng thái hồ sơ (biểu mẫu và ghi kết quả sơ tuyển).
- Nhãn `filled`: "Đủ số lượng" → **"Đã hoàn thành chỉ tiêu"**. Tự đủ chỉ tiêu nay **tắt công khai** như khi đổi tay (lỗi do
  kiểm sống bắt được — xem dưới).
- `services/het_han_don.py`: quét lúc khởi động và mỗi 30 phút; mỗi đơn, mỗi hạn nộp **một** thông báo; không tự đổi trạng
  thái. Admin đổi trạng thái đơn → thông báo của đơn ấy tắt. Thông báo về đơn chỉ Admin/Manager thấy và tắt được.
- Bản công khai có `con_lai` (chỉ tiêu còn trống), **không** lộ `hired_count` thô. Trang chi tiết và thẻ đơn: "Còn X/Y".
  Khối đơn cho trợ lý theo đơn: "Chỉ tiêu: còn X/Y người".
- Khung chat: mô tả đơn có "còn X/Y chỉ tiêu"; khối mới nói tình trạng các đơn khách nhắc mã (`DH-0003`, `dh 0003`…) hoặc
  đơn khách đang xem — đủ chỉ tiêu / hết hạn / đóng / tạm dừng; hỏi theo nơi thì kể cả đơn ở đó vừa ngừng nhận trong 30 ngày.
  **Đơn nháp không bao giờ được nhắc.**
- Màn quản trị: khối "Đơn cần xử lý" trên trang tổng quan (Admin/Manager): đơn quá hạn chưa gỡ (lấy thẳng từ danh sách đơn,
  có nút "Gỡ đơn (chuyển Hết hạn)") và thông báo chỉ tiêu chưa đọc. Ngưỡng "sắp hết hạn" 14 → **10** ngày.

**Kiểm:** 21 ca mới (`tests/test_chi_tieu.py`), 4 đột biến bị bắt 4/4. Backend 1351/1351, website 85/85, admin 45/45, `tsc` và
`next build` hai app sạch. Kiểm sống trên máy chủ thử (`2026-10-12_chi_tieu_het_han.json`), 14 phép đo:

| Mã | Phép đo | Kết quả |
|---|---|---|
| CT-1/2 | đơn mới (chỉ tiêu 1) hiện công khai "còn 1/1", không lộ số đã tuyển; khung chat nói "còn 1/1" | ĐÚNG |
| CT-3 | trúng tuyển → "Đã hoàn thành chỉ tiêu", tắt công khai | **lần 1 LỖI** (`published` vẫn bật) → sửa → ĐÚNG |
| CT-4…7 | tự ẩn (404); Admin có thông báo; consultant không thấy; khung chat nói "đã đủ chỉ tiêu" | ĐÚNG |
| CT-8…10 | rút → trả chỉ tiêu (0/1), đơn vẫn ẩn, Admin có thông báo | ĐÚNG |
| HH-1…4 | đơn quá hạn: báo đúng một lần, tự ẩn, khung chat nói "hết hạn nộp", gỡ → thông báo tắt | ĐÚNG |

Trình duyệt (bản production, đăng nhập bằng biểu mẫu): trang đơn hiện "Còn 5/5 người" (sau khi bộ nhớ đệm 60 giây của website
làm mới — đơn đủ chỉ tiêu có thể còn hiện tối đa khoảng một phút); khối "Đơn cần xử lý" hiện đúng; bấm "Gỡ đơn" với DH-0017 →
"Hết hạn", tắt công khai, lịch sử ghi tên người bấm, thông báo tắt — rồi **trả DH-0017 về như cũ** (đơn mẫu cố ý quá hạn).
Ảnh `25_…`, `26_…`. Dữ liệu thử (2 đơn, 1 hồ sơ, thông báo, sự kiện, 2 tài khoản) đã xóa.

**Lưu ý vận hành:** lần đầu máy chủ chạy với database thật, bộ quét sẽ tạo thông báo cho các đơn **đang** quá hạn mà chưa gỡ
(mỗi đơn một cái). Database thật chưa chạy bản này; số đếm 10 bảng không đổi.

## 10. Nhập Excel: giữ chức năng, sửa lỗi mất dữ liệu, đo tải (12/10)

Chủ đồ án quyết định **giữ** nhập Excel (đơn đến từ nhiều nguồn) và hỏi file nhiều dữ liệu có gây quá tải không.

**Sửa:**
1. **Cập nhật bằng file thiếu cột không còn xóa dữ liệu.** Mọi cột không bắt buộc vắng trong file thì giữ nguyên giá trị
   đang lưu (mở rộng chốt của hai cột ghi chú ở Phase 2). Đo lại ca tái hiện DH-0001: trước sửa ghi đè 13 trường + tắt công
   khai; sau sửa chỉ ghi 9 trường có trong file. Đơn thêm mới vẫn dùng mặc định; cột có mặt mà ô trống vẫn xóa (ý người sửa).
2. **Quá 500 dòng thì từ chối cả file, nói rõ** ("hơn 500 dòng… hàng N… chia thành nhiều file"). Trước đó dòng 501+ bị **bỏ
   im lặng**. Dừng đọc ngay ở dòng dữ liệu thứ 501, không đọc tới cuối file.
3. **Đọc file ở luồng riêng** (`run_in_threadpool`): openpyxl chạy đồng bộ; đọc trên vòng sự kiện thì cả khung chat và
   website đứng theo trong lúc đọc.

**Đo tải trên máy chủ thử** (đơn thử trạng thái Nháp, tên "[KIỂM THỬ TẢI]", đã xóa hết):

| Việc | Thời gian | Người khác gọi API cùng lúc |
|---|---|---|
| file 500 dòng (40 KB) — chạy thử | 0,17–0,46 s | chậm nhất 176–291 ms |
| ghi thật 500 đơn mới | 1,5–2,2 s | chậm nhất 169–340 ms |
| cập nhật 500 đơn | 1,35–1,85 s | chậm nhất 185–394 ms |
| 501 dòng | từ chối ngay (HTTP 400) | — |
| 600 dòng dữ liệu + 200.000 dòng rỗng có tô màu (đọc trực tiếp) | từ chối sau 0,24 s | — |
| 3 dòng + 400.000 dòng rỗng có tô màu (1,7 MB) — chạy thử | 8,4 s | 17 lần trả lời, chậm nhất 547 ms (lúc rảnh 373 ms) |

Hai lượt số đo 500 dòng khác nhau vì lượt sau chạy khi máy đang bận dựng file nặng. Một lần chạy script đo file nặng đã vô ý
chạy lại cả bài đo 500 dòng (import script kia chạy luôn hàm chính) — trên database thử, đã tự dọn.

**Kết luận:** giới hạn 5 MB/file và 500 dòng/lần đủ chặn quá tải; file đúng chuẩn 500 dòng xử lý trong khoảng 2 giây, máy chủ
vẫn phục vụ người khác. File lạ (định dạng trên hàng trăm nghìn dòng rỗng) chậm vài giây **cho riêng người nhập**.

Kiểm tự động: 6 ca mới, 3 đột biến nhập Excel bị bắt 3/3. Backend 1357/1357. Database thật không đổi.

**Cập nhật cùng ngày — nâng trần dòng:** chủ đồ án chốt giới hạn chính là dung lượng file (5 MB); trần dòng nâng **500 → 2.000
dòng/lần** (mã, chữ trên màn nhập Excel, `Tailieu/DonHang/HUONG_DAN.md`). Đo trên máy chủ thử (đơn Nháp "[KIỂM THỬ TẢI]",
đã xóa: 2.000 đơn, 4.000 sự kiện, 1 tài khoản):

| Việc | 2.000 dòng (144 KB) | Người khác gọi API cùng lúc |
|---|---|---|
| chạy thử | 0,86 s, phản hồi 2 MB | chậm nhất 400 ms |
| ghi thật 2.000 đơn mới | **11,5 s** | 27 lần trả lời, chậm nhất 290 ms |
| cập nhật 2.000 đơn | 11,5 s | chậm nhất 388 ms |
| 2.001 dòng | từ chối (HTTP 400), báo hàng 2002 | — |

Ước tính trước khi đo là ~8 giây — thực đo chậm hơn (11,5 s). Bảng xem trước hiện mọi dòng (4 cột); **chưa** thử tải file
2.000 dòng lên màn quản trị trên trình duyệt.

## 11. Việc còn lại sau khi đẩy `87e1e04` (12/10)

Năm việc rà ra sau lần đẩy trước. Mọi kiểm có ghi dữ liệu chạy trên `xkld_kiem_thu_0710`, chốt trước khi ghi (tên database
của tiến trình + tiêu đề DH-0001 có "[KIỂM THỬ]"); tài khoản tạm và dữ liệu sinh ra đều đã xoá/trả lại.

### 11.1 Thông báo theo phạm vi người xem

Trước đó mọi nhân viên đều thấy **toàn bộ** thông báo của hệ thống. Kiểm ra năm lỗi:

| Lỗi | Hậu quả | Sửa |
|---|---|---|
| Đếm chưa đọc tính trên cả hệ thống | consultant thấy số của người khác trên chuông | `GET /notifications/unread-count` đếm theo phạm vi |
| API trả họ tên đầy đủ ở việc chưa ai nhận / của người khác | lộ tên khách cho người không phụ trách | ngoài phạm vi của mình chỉ còn chữ viết tắt (`ban_toi_thieu`) |
| Thông báo yêu cầu hỗ trợ rơi vào nhánh lịch hẹn khi bấm "đã đọc" | không đánh dấu đọc được | thêm nhánh `support_request`; người khác phụ trách → 403 |
| consultant thấy "Bạn được giao…" của người khác (thấy trên trình duyệt) | hiểu nhầm là việc của mình | thông báo bàn giao chỉ hiện cho đúng người được giao |
| Đánh dấu đã đọc xong, số trên chuông 30 giây sau mới đổi | tưởng bấm không ăn | trang thông báo phát sự kiện, khung quản trị tải lại số ngay |

Phạm vi consultant: lịch hẹn của mình; hồ sơ và yêu cầu hỗ trợ của mình hoặc chưa ai nhận; thông báo về đơn chỉ quản lý thấy.
Thêm trang `/admin/notifications` (chỉ chưa đọc / xem cả đã đọc, đánh dấu từng mục, đánh dấu tất cả).

Kiểm sống (máy chủ thử, 2 tài khoản tạm): consultant 92 → **53** sau khi lọc thông báo bàn giao; manager 162 = cả hệ thống;
TB-1…TB-5 đúng 5/5 (TB-5 lần đầu báo LỖI vì **công thức kiểm của tôi** — một mã yêu cầu có 2 thông báo; đo trực tiếp thì
đúng). Trả lại 162 thông báo chưa đọc như cũ. Ảnh `27_…`. Kiểm tự động: 8 ca backend, 5 ca quản trị; 2 đột biến bị bắt 2/2.

Kèm: chữ viết tắt trên thẻ (website `OrderAdvicePanel`, khung quản trị) chỉ lấy từ chữ cái — "Nguyễn Thị Hoa (tạm)" từng ra
"N(", nay "TH"; chuỗi không có chữ cái ra "?".

### 11.2 Phông tự phục vụ

Rủi ro ghi ở Phase 4 (dựng cần mạng tới Google) đã gỡ: bỏ `next/font/google` ở cả hai app; 24 tệp `.woff2` (544 KB, Be Vietnam
Pro + Gelasio, có bộ tiếng Việt) nằm trong `public/fonts` kèm giấy phép OFL; `app/phong-chu.css` khai `@font-face`. Trình duyệt
nạp phông từ chính máy chủ, **0** yêu cầu tới Google (ảnh `28_…`). Trong `.next` vẫn còn chuỗi `fonts.googleapis.com` — đó là
mã của Next.js, không phải yêu cầu của ứng dụng. **Chưa** thử dựng khi tắt hẳn mạng.

### 11.3 Màn "đề xuất của khách" và "tiến độ học"

API có từ 08/10 nhưng chưa màn hình nào dùng: ô nhân viên đã đối chứng có căn cứ thì khách sửa thành **đề xuất chờ nhân viên**;
trước 12/10 đề xuất ấy chỉ hiện ở danh sách mâu thuẫn chung, kể cả khi đã xử lý, và in "undefined" vì đề xuất không có trích dẫn.
Nay khối "Khách đề xuất sửa — chờ bạn xem" ở cột phải hồ sơ ứng viên:

- "Giữ giá trị nhân viên" — bắt ghi lý do ≥ 3 ký tự; "Sửa theo khách" — mở biểu mẫu sửa.
- Khách sửa ô nhân viên nhập **chưa** xác minh thì đã áp dụng — chỉ hiện một dòng để biết.
- Ghi tiến độ học: đang học / tạm dừng / đã hoàn thành; hoàn thành ghi "Hoàn thành chương trình … — chưa xác minh chứng chỉ",
  **không** đổi trình độ dùng để đối chiếu.

Kiểm trình duyệt (bản dựng thật, consultant tạm được giao đúng hồ sơ UV-F21497 trên database thử; đề xuất N4 → N3 dựng bằng
đúng hai hàm đường thật dùng — `danh_dau_xac_thuc` và `o_bi_giu` + `ghi_de_xuat`):

| Bước | Kết quả |
|---|---|
| Bấm "Giữ" khi chưa ghi lý do | hiện lời nhắc, không gọi API (ảnh `29_…`) |
| Ghi lý do, bấm "Giữ" | "Đã giữ giá trị nhân viên và đóng đề xuất.", khối đề xuất biến mất |
| Hoàn thành chương trình, kết quả N3 | "Hoàn thành chương trình N3 tại trung tâm — chưa xác minh chứng chỉ"; trình độ vẫn N4; phiên bản 1 → 2 (ảnh `30_…`) |

Ba điều thấy khi kiểm:

1. **Bố cục (đã sửa):** ô lý do và hai nút xếp ngang trong cột hẹp → ô lý do còn "Lý do gi". Nay ô lý do một dòng, nút xuống dưới.
2. **Công cụ, không phải lỗi:** điền ô bằng `fill` của công cụ trình duyệt thì chữ hiện trong ô nhưng React không nhận (giá trị
   trong React vẫn rỗng) → bấm "Giữ" vẫn báo thiếu lý do. Gõ phím thật (`type`) thì nhận đúng. Tôi đã tưởng là lỗi của mã và sửa,
   rồi kiểm lại trên bản dựng cũ bằng gõ phím thật thấy chạy đúng — đã **bỏ** phần sửa ấy. Bài học: kiểm ô có điều khiển bằng
   gõ phím thật.
3. **Do cách dựng dữ liệu:** cột trái ghi trình độ "Ứng viên xác nhận" trong khi khối tiến độ ghi "nhân viên đã đối chứng" — vì
   tôi chỉ gắn nhãn đối chứng mà giữ nguồn cũ. Đường sơ tuyển thật đổi nguồn thành `staff` nên không lệch như vậy.

Trả lại: hồ sơ khớp bản gốc từng byte; xoá 2 nhật ký thao tác và tài khoản tạm. Kiểm tự động: 3 ca quản trị; 4 đột biến trong
`dot_bien.py` bị bắt 4/4 (bỏ yêu cầu lý do, đang học vẫn gửi kết quả, không gửi phiên bản, lẫn đề xuất đã xử lý).

### 11.4 Trình độ ở hồ sơ tuyển dụng đi theo hồ sơ năng lực

`recruitment_applications.japanese_level` là bản chụp lúc đăng ký và **không ai cập nhật**: buổi sơ tuyển ghi trình độ mới vào
hồ sơ năng lực, đổi trạng thái hồ sơ tuyển dụng, nhưng hàng đợi và danh sách hồ sơ tuyển dụng vẫn hiện trình độ ngày đăng ký —
hai màn hình nói hai điều khác nhau về cùng một người.

Sửa ở cửa ghi hồ sơ (`candidate_profiles.apply_changes`) — mọi đường sửa (sơ tuyển, nhân viên, khách, đọc CV, trợ lý) đều đi
qua đây: trình độ đổi thì cập nhật nhãn ở các hồ sơ tuyển dụng **đang mở** gắn hồ sơ ấy. Hồ sơ đã đóng giữ nguyên (sự thật lúc
đóng). Lỗi đồng bộ chỉ ghi log, không biến lần lưu hồ sơ thành lỗi 500.

Kiểm sống (manager tạm, database thử): ghi sơ tuyển qua API thật cho HS-0F674B (giữ nguyên trạng thái để không động chỉ tiêu),
tra cứu trực tuyến, N2 → hồ sơ năng lực N2, hồ sơ tuyển dụng **N4 → N2**, danh sách hiện N2. Trả lại hồ sơ năng lực, hồ sơ tuyển
dụng (khớp bản gốc), xoá 1 sự kiện, 2 nhật ký, tài khoản tạm. Kiểm tự động: 6 ca; 2 đột biến bị bắt 2/2.

### 11.5 Tổng kết kiểm thử (12/10)

| Bộ | Kết quả |
|---|---|
| Backend | 1371/1371 |
| Quản trị | 53/53, `tsc` sạch, dựng sạch |
| Website | 85/85, `tsc` sạch, dựng sạch |
| Database thật | 10 bảng `[342, 197, 85, 83, 294, 2, 679, 87, 224, 80]`, `storage/cv` 25 tệp — không đổi |
