# Nội dung và cấu trúc website khách hàng

Khảo sát trang thật của doanh nghiệp, `xklddieuduong.vn`, ngày 14/09/2026, để lấy
làm căn cứ dựng website trong đồ án.

Đây cũng chính là trang mà crawler của phần chatbot đang thu thập tri thức, nên
những gì viết ở đây giải thích luôn vài hiện tượng bên phần tri thức.

---

## 1. Thông tin doanh nghiệp lấy được

| Mục | Nội dung |
|---|---|
| Tên công ty | Công ty Đầu tư Phát triển Nhân lực Quốc tế DC |
| Hotline | 0971.716.939 |
| Văn phòng Hà Nội | Tầng 6, Tòa nhà Hữu Nghị, 188 Lê Quang Đạo, Từ Liêm |
| Văn phòng TP. Hồ Chí Minh | Khu đô thị Vạn Phúc, Thủ Đức |
| Văn phòng Bến Tre | 201C2 Phan Đình Phùng |
| Kênh liên hệ | Điện thoại và Zalo |

Số hotline khớp đúng giá trị mặc định `support_phone` đang có trong
`app/core/config.py`, nên cấu hình hiện tại không sai.

Chuyên mục trên trang thật, tám mục:

```
Công ty DC – Trung tâm học        Lớp học – Kí túc xá
Hỏi đáp về Điều dưỡng             Học viên – Xuất cảnh
Quy trình – Chi phí đơn           Đón tiếp – Học viên (tại Nhật)
Mọi người – Đăng ký               Phỏng vấn – Đơn hàng
```

---

## 2. Hiện trạng trang thật, và vì sao nó quan trọng

Trang chạy trên WooCommerce, nhưng **mỗi "sản phẩm" thực chất là một bài đăng hình
ảnh** chứ không phải một đơn hàng. Ba điều quan sát được:

**Nội dung nằm trong ảnh, không nằm trong chữ.** Phần lớn trang là ảnh chụp giấy
phép, ảnh văn phòng, ảnh học viên. Chữ trên trang rất ít. Đây chính là lý do phần
thu thập tri thức phải dùng nhận dạng chữ trong ảnh, và cũng là lý do hai mươi hai
trên ba mươi hai đoạn tri thức bị lẫn rác — không phải lỗi thuật toán, mà vì nguồn
vốn là ảnh.

**Không có đơn hàng có cấu trúc.** Chuyên mục "Đơn hàng" mở ra chỉ thấy giấy phép và
ảnh chi nhánh. Mỗi mục hiển thị đúng hai thứ: tên và dòng "Giá: liên hệ". Không có
tỉnh, không có yêu cầu tiếng Nhật, không có hạn nộp, không có bộ lọc.

**Chi phí không công bố.** Mọi nơi đều là "liên hệ".

**Trọng tâm của trang là chứng minh uy tín.** Giấy phép xuất khẩu lao động, xác nhận
của Sở Nội vụ các tỉnh, ảnh giám đốc tuyển sinh, ảnh cơ sở. Trong ngành này khách
hàng sợ bị lừa, nên doanh nghiệp nào cũng dồn diện tích trang cho phần đó.

### Điều này nói gì về đồ án

Khoảng trống trên trang thật gần như trùng khít với phần đồ án đang làm:

| Trang thật | Hệ thống của đồ án |
|---|---|
| Đơn hàng chỉ có tên và "liên hệ" | Đơn hàng có đầy đủ điều kiện bắt buộc và thông tin tham khảo, lọc được theo tỉnh, vùng, loại hình, chương trình, trình độ tiếng |
| Muốn biết mình có hợp không thì phải gọi điện | Nhập hồ sơ rồi đối chiếu, ra lý do từng tiêu chí đạt hay không đạt |
| Thông tin nằm trong ảnh, đọc bằng mắt | Dữ liệu có cấu trúc, truy vấn được |
| Hỏi ngoài giờ thì chờ sáng hôm sau | Trả lời liên tục |

Nói cách khác, website của đồ án không phải bản sao đẹp hơn của trang cũ. Nó bổ sung
đúng thứ trang cũ không có.

---

## 3. Nguyên tắc khi lấy trang thật làm tham khảo

**Mượn cách tổ chức thông tin, không chép nội dung.** Chuyên mục và thứ tự thông tin
phản ánh đúng thứ tự câu hỏi của ứng viên, nên đáng học. Còn chữ và ảnh là tài sản
của doanh nghiệp, viết lại bằng lời của mình.

**Không bịa con số.** Trang thật không công bố chi phí. Mọi con số về chi phí, lương,
thời gian trên website của đồ án phải hoặc lấy từ tài liệu doanh nghiệp cung cấp,
hoặc ghi rõ là số tham khảo. Nguyên tắc này giống hệt nguyên tắc của chatbot: không
có căn cứ thì nói là chưa có thông tin.

**Không dựng giấy phép giả.** Phần uy tín để sẵn chỗ, doanh nghiệp tự điền ảnh thật.
Bản demo dùng ảnh giữ chỗ có ghi rõ là ảnh minh họa.

---

## 4. Sơ đồ trang đề xuất

```
/                        Trang chủ
/gioi-thieu              Về công ty và chương trình điều dưỡng Nhật Bản
/dieu-kien               Điều kiện tham gia
/chi-phi                 Chi phí và hỗ trợ tài chính
/quy-trinh               Quy trình bảy bước
/dao-tao                 Lớp học tiếng Nhật và ký túc xá
/don-hang                Danh sách đơn hàng đang tuyển     ← trang thật không có
/don-hang/[ma-don]       Chi tiết một đơn hàng             ← trang thật không có
/tu-van                  Luồng tư vấn: hồ sơ, đối chiếu, chọn đơn, đặt lịch  ← điểm khác biệt lớn nhất
/cau-hoi-thuong-gap      Hỏi đáp
/lien-he                 Liên hệ và ba văn phòng
```

Mười một trang, ánh xạ gần một một với tám chuyên mục của trang thật, cộng thêm ba
trang mà trang thật không có.

### Nội dung từng trang

| Trang | Khối nội dung | Nguồn dữ liệu |
|---|---|---|
| Trang chủ | Mở đầu kèm hai nút "Xem đơn hàng phù hợp" và "Gọi tư vấn" · Bốn thẻ số liệu chương trình · Ba đơn hàng nổi bật · Bảy bước quy trình rút gọn · Khối uy tín (giấy phép, ba văn phòng) · Năm câu hỏi thường gặp · Khối để lại số điện thoại | Đơn hàng lấy từ API công khai, phần còn lại là nội dung tĩnh |
| Giới thiệu | Công ty, ba văn phòng, ba diện chương trình EPA, Tokutei Ginou, Thực tập sinh | Tĩnh |
| Điều kiện | Bảng tiêu chí, yêu cầu, ghi chú · Nút "Chưa chắc đủ điều kiện? Thử đối chiếu hồ sơ" dẫn sang `/tu-van` | Tĩnh |
| Chi phí | Bảng các khoản và thời điểm đóng · Ghi rõ đây là số tham khảo, nhân viên xác nhận lại | Tĩnh, chờ doanh nghiệp cung cấp |
| Quy trình | Bảy bước dạng dòng thời gian, mỗi bước ghi thời lượng | Tĩnh |
| Đào tạo | Lớp học tiếng Nhật, ký túc xá, sinh hoạt học viên | Tĩnh |
| Đơn hàng | Bộ lọc theo tỉnh, vùng, loại hình cơ sở, chương trình, trình độ tiếng · Lưới thẻ đơn · Trạng thái rỗng có hướng dẫn | `GET /public/job-orders` |
| Chi tiết đơn | Tách rõ hai khối "Điều kiện bắt buộc" và "Thông tin tham khảo" · Nút "Kiểm tra hồ sơ của tôi với đơn này" | `GET /public/job-orders/{code}` |
| Tư vấn | Nhập hồ sơ theo bước, xác nhận, xem đơn phù hợp kèm lý do từng tiêu chí, chọn đơn, đặt lịch | `/public/profiles`, `/public/matches` |
| Hỏi đáp | Nhóm theo chủ đề, mỗi câu có nút hỏi thêm trong khung chat | Tĩnh, đồng bộ taxonomy với chatbot |
| Liên hệ | Ba văn phòng, bản đồ, biểu mẫu gọi lại | Tĩnh |

Khung chat của nhóm kia nhúng ở góc phải mọi trang, không sửa gì bên trong nó.

---

## 5. Khối uy tín

Trang thật dành phần lớn diện tích cho phần này, nên website của đồ án cũng phải có,
nếu không sẽ trông như một trang rao vặt.

Thiết kế thành một khối có chỗ trống sẵn: giấy phép hoạt động dịch vụ đưa người lao
động đi làm việc ở nước ngoài, xác nhận của cơ quan quản lý, ảnh ba văn phòng, ảnh
lớp học, số học viên đã xuất cảnh. Doanh nghiệp điền ảnh thật vào sau.

Trong bản demo, mỗi ô để ảnh giữ chỗ kèm dòng chữ "ảnh minh họa" để người xem không
hiểu nhầm. Không dựng giấy tờ giả, kể cả để demo.

---

## 6. Hướng thiết kế

Ưu tiên điện thoại, vì phần lớn ứng viên truy cập bằng điện thoại và thường vào buổi
tối. Chữ đủ lớn, nút đủ to để bấm bằng ngón tay.

Giữ màu đỏ thương hiệu `#cb1d1e` đang dùng trong hệ thống quản trị để hai phần trông
như một sản phẩm. Đưa màu vào cấu hình Tailwind thay vì viết cứng rải rác như hiện nay.

Đổi phông chữ sang một phông có dấu tiếng Việt đầy đủ. Phông Geist đang khai báo
trong `frontend/app/layout.tsx` không hỗ trợ tốt tiếng Việt, và dù sao cũng đang bị
`globals.css` ghi đè nên hiện không có tác dụng gì.

Trang danh sách đơn hàng là trang quan trọng nhất về mặt kỹ thuật, vì nó là thứ trang
thật không làm được. Bộ lọc phải chạy bằng tham số trên đường dẫn để chia sẻ được kết
quả lọc cho người khác.

---

## 7. Việc cần doanh nghiệp cung cấp

| Nội dung | Dùng cho trang |
|---|---|
| Bảng chi phí thật và thời điểm đóng từng khoản | Chi phí, trang chủ |
| Mô tả bảy bước quy trình kèm thời lượng | Quy trình, trang chủ |
| Điều kiện tham gia chính thức | Điều kiện |
| Ảnh giấy phép và ảnh ba văn phòng | Khối uy tín |
| Thông tin lớp học tiếng Nhật và ký túc xá | Đào tạo |
| Danh sách câu hỏi thường gặp | Hỏi đáp |

Chưa có thì dùng nội dung tạm có đánh dấu rõ, và ghi lại trong mục này để không quên
thay trước khi bảo vệ.
