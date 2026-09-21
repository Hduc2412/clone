# Hệ thống quản lý nội bộ

Ứng dụng Next.js độc lập dành cho `admin`, `manager` và `consultant`. Ứng dụng
này không chứa giao diện chatbot khách hàng.

## Chạy local

```powershell
npm ci
npm run dev
```

Mặc định hệ thống quản lý chạy tại `http://localhost:3101` và gọi FastAPI tại
`http://localhost:8020`.

Nếu backend dùng địa chỉ khác, tạo `.env.local` từ `.env.example`. Muốn đổi cổng
của chính app này thì chạy `npm run dev -- -p 4001`; đặt `PORT` trong `.env.local`
không có tác dụng vì Next chọn cổng trước khi nạp file `.env`.

## Các trang

- `/login`: đăng nhập nội bộ.
- `/admin`: Dashboard.
- `/admin/appointments`: lịch hẹn và thông báo.
- `/admin/leads`: quản lý khách hàng/lead.
- `/admin/conversations`: lịch sử chatbot.
- `/admin/knowledge`: trạng thái cơ sở tri thức.
- `/admin/users`: người dùng nội bộ.

Mọi API dữ liệu nội bộ đều yêu cầu JWT do backend cấp.
