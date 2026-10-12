/**
 * Chữ viết tắt trên ô tròn đại diện: hai tiếng cuối của tên, chỉ tính tiếng bắt đầu
 * bằng chữ cái (12/10).
 *
 * Trước đó mỗi màn tự tính: tên "… (tạm)" ra "C(" ở khung quản trị, "V(" ở màn Người
 * dùng (kiểm trình duyệt 12/10). Chữ cái = ký tự có hai dạng hoa/thường khác nhau, gồm
 * cả "Đ", "Ư"; không dùng `\p{L}` vì cấu hình biên dịch nhắm ES5.
 */
export function chuVietTat(ten: string | null | undefined): string {
  const chu = String(ten ?? "")
    .split(/\s+/)
    .filter((w) => w.length > 0 && w[0].toLowerCase() !== w[0].toUpperCase());
  if (!chu.length) return "?";
  return chu
    .slice(-2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}
