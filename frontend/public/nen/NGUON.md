# Nguồn ảnh nền

Ba ảnh dùng làm phông nền trang chủ. Cả ba lấy từ Wikimedia Commons và đều có
giấy phép cho phép dùng lại, kể cả cho mục đích thương mại.

| File | Nội dung | Tác giả | Giấy phép | Trang gốc |
|---|---|---|---|---|
| `fuji-binh-minh.webp` | Núi Phú Sĩ lúc bình minh, tháng 3/2025 | Romain Guy | **CC0** (không bắt buộc ghi công) | [Commons](https://commons.wikimedia.org/wiki/File:Sunrise_with_Mount_Fuji_-_March_2025.jpg) |
| `fuji-hoa-anh-dao.webp` | Núi Phú Sĩ mùa hoa anh đào, tháng 4 | SRP1998 | **CC BY-SA 4.0** (phải ghi công) | [Commons](https://commons.wikimedia.org/wiki/File:Mount_Fuji_April_Cherry_Blossom.jpg) |
| `ho-kawaguchi.webp` | Hồ Kawaguchi nhìn về núi Phú Sĩ | Midori | **CC BY 3.0** (phải ghi công) | [Commons](https://commons.wikimedia.org/wiki/File:Lake_Kawaguchiko_Sakura_Mount_Fuji_4.JPG) |

Phần ghi công hiển thị ở chân trang website, theo đúng yêu cầu của hai giấy phép
CC BY và CC BY-SA.

## Đã xử lý lại thế nào

Ảnh gốc từ 3872×2592 tới 7924×6556, dung lượng 1,5–2,5 MB mỗi tấm. Không dùng
thẳng được: phần lớn ứng viên vào bằng mạng di động.

Các bước xử lý, chạy bằng Pillow:

1. Cắt về tỷ lệ 16:9, lấy phần giữa nhưng lệch lên trên một phần ba để giữ trọn
   đỉnh núi.
2. Xuất hai kích thước: `1920×1080` cho màn hình lớn và `960×540` cho điện thoại.
3. Nén WebP chất lượng 72, `method=6`.

Kết quả:

| Bản | Dung lượng |
|---|---|
| 1920px | 181–297 KB |
| 960px | 45–93 KB |

Trình duyệt tự chọn bản phù hợp qua `srcset`, nên máy điện thoại không tải bản
lớn. Chỉ tấm đầu tải ngay, hai tấm sau đặt `loading="lazy"`.

## Muốn thay ảnh khác

Giữ đúng tên file và tỷ lệ 16:9 thì không phải sửa mã nguồn. Nhớ cập nhật bảng
giấy phép ở trên và phần ghi công ở chân trang — dùng ảnh có giấy phép bắt buộc
ghi công mà không ghi là vi phạm, và đây là đồ án nộp lên trường.
