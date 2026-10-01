# Chạy toàn hệ thống bằng Docker

Bộ đóng gói này dựng cả sáu dịch vụ bằng một lệnh, để người chấm hoặc người tiếp
nhận dự án không phải cài Python, Node, MongoDB và Qdrant từng thứ một.

| Dịch vụ | Ảnh | Cổng ra ngoài |
|---|---|---|
| `nginx` | `nginx:1.27-alpine` | 80 (website), 8080 (quản trị) |
| `website` | dựng từ `frontend/` | không mở, đi qua nginx |
| `admin` | dựng từ `admin-frontend/` | không mở, đi qua nginx |
| `backend` | dựng từ `backend/` | 8020 |
| `mongodb` | `mongo:7` | không mở |
| `qdrant` | `qdrant/qdrant` | 6333, 6334 |

Backend **có** mở cổng ra ngoài, khác với hai app Next. Lý do ở §4.

---

## 1. Trước lần chạy đầu

### 1.1. Tạo `backend/.env`

```bash
cp backend/.env.example backend/.env
```

Rồi điền ba giá trị bắt buộc — thiếu thì backend chết ngay lúc khởi động chứ
không chạy tiếp với cấu hình rỗng:

| Biến | Lấy ở đâu |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `INITIAL_ADMIN_PASSWORD_HASH` | `python -m app.auth.create_password_hash` |

Ba biến `MONGODB_URI`, `QDRANT_URL`, `CORS_ORIGINS` trong file đó viết cho máy
phát triển; `docker-compose.yml` đã đè lên bằng giá trị đúng cho mạng container,
không cần sửa.

### 1.2. Volume Qdrant

`docker-compose.yml` khai `qdrant_data` là volume **external**, nghĩa là dùng lại
volume đang có chứ không tạo mới. Máy nào chưa từng chạy Qdrant thì tạo trước:

```bash
docker volume create qdrant_data
```

Rồi nạp kho tri thức bằng `ingestion/embedder.py` như cũ. Bỏ qua bước này thì hệ
thống vẫn lên, nhưng khung chat từ chối mọi câu hỏi vì kho rỗng — và triệu chứng
nhìn hệt như lỗi mô hình.

### 1.3. Dừng dịch vụ đang chiếm cổng

Compose mở ra ngoài ba cổng: **8020** (backend), **6333/6334** (Qdrant), **80 và
8080** (nginx). Cái nào đang bị chiếm thì compose báo lỗi bind.

```bash
docker stop qdrant          # nếu đang chạy Qdrant rời, nó giữ 6333
```

Backend chạy tay lúc phát triển cũng giữ 8020 — `pkill` không diệt được uvicorn
trên Windows, dùng PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8020 -State Listen | ForEach-Object {
  Stop-Process -Id $_.OwningProcess -Force
}
```

**Không cần dừng MongoDB trên máy.** `mongodb` trong compose không khai `ports:`
— nó chỉ nói chuyện trong mạng nội bộ của compose, nên không tranh 27017 với
MongoDB cài sẵn. Hai database chạy song song và **không thấy nhau**: dữ liệu bạn
tạo lúc chạy dev nằm ở MongoDB của máy, dữ liệu trong Docker nằm ở volume
`xkld-chatbot_mongo_data`. Vì vậy stack Docker lên là một hệ **trống**, phải nạp
dữ liệu mẫu ở §2.

---

## 2. Chạy

```bash
docker compose up -d --build
docker compose ps
```

Chờ cho tới khi `backend` ở trạng thái `healthy` — hai app Next được cấu hình chờ
đúng mốc đó rồi mới khởi động.

| Địa chỉ | Là gì |
|---|---|
| <http://localhost> | Website khách hàng |
| <http://localhost:8080> | Hệ thống quản trị |
| <http://localhost:8020/docs> | Tài liệu API tự sinh |

Nạp 19 đơn tuyển dụng mẫu:

```bash
docker compose exec backend python -m scripts.seed_job_orders
```

Chạy bộ kiểm thử ngay trong container:

```bash
docker compose exec backend python -m unittest discover -s tests -t .
```

Kết quả đúng là `OK (skipped=7)` — **bảy ca bỏ qua là bình thường, không phải lỗi.**
Ảnh backend chỉ chép `backend/`, còn bảy ca ấy soi file ngoài thư mục đó (nguồn
frontend, `.gitignore`) để canh một quy tắc của cả kho mã: không để lọt số điện
thoại hay địa chỉ thật. Trong container không có gì để soi, nên chúng tự bỏ qua
kèm lý do thay vì báo đỏ — một ca đỏ vì thiếu file trông y như một ca đỏ vì quy
tắc bị vi phạm, mà hai thứ ấy đòi hai phản ứng khác hẳn nhau.

Chạy trên máy thật thì không ca nào bỏ qua: `Ran 987 tests ... OK`. Đó mới là
lượt chạy kiểm được cả bảy quy tắc kia.

Dừng và xóa container, **giữ nguyên dữ liệu**:

```bash
docker compose down
```

Xóa cả dữ liệu MongoDB và CV đã tải lên (Qdrant không bị đụng vì volume của nó
khai external):

```bash
docker compose down -v
```

---

## 3. Ba chỗ dễ vấp

### 3.1. Đổi địa chỉ backend thì phải dựng lại ảnh

`NEXT_PUBLIC_BACKEND_URL` là biến của **trình duyệt**, được nướng thẳng vào mã
JavaScript lúc `npm run build`. Trình duyệt của khách không đọc được biến môi
trường của container, nên sửa `docker-compose.yml` rồi `restart` sẽ không có tác
dụng gì. Phải dựng lại:

```bash
PUBLIC_BACKEND_URL=https://api.ten-mien-that.vn docker compose build website admin
docker compose up -d
```

### 3.2. Chuỗi băm mật khẩu và dấu `$`

Mặc định Compose nội suy `$` trong file env. Chuỗi băm quản trị có dạng
`pbkdf2_sha256$600000$muối$băm`, nên ba đoạn sau dấu `$` bị hiểu thành tên biến
và biến mất. Tài khoản quản trị đầu tiên khi đó được tạo với chuỗi băm hỏng, và
triệu chứng duy nhất là "sai mật khẩu" với mật khẩu đúng.

`docker-compose.yml` đã khai `format: raw` để tắt nội suy. Kiểm lại bất cứ lúc
nào:

```bash
docker compose config | grep INITIAL_ADMIN_PASSWORD_HASH
```

Giá trị in ra phải khớp với trong `backend/.env`, chỉ khác là mỗi `$` hiện thành
`$$` — đó là cách Compose thoát ký tự khi in, giá trị thật vào container vẫn đúng.

### 3.3. Cả hai app Next đều phục vụ `/_next/*`

Đó là lý do nginx mở hai cổng thay vì một cổng với `/admin` trỏ sang app kia. Gộp
chung thì hai vùng đường dẫn tĩnh chồng lên nhau và app khớp trước sẽ nuốt CSS
của app còn lại.

---

## 4. Vì sao backend mở cổng còn hai app Next thì không

Trình duyệt của ứng viên gọi thẳng vào backend: mọi lời gọi API đều xuất phát từ
JavaScript chạy trên máy khách, không phải từ container Next. Nên backend bắt
buộc phải có đường vào từ ngoài.

Hai app Next thì ngược lại — chỉ nginx cần nói chuyện với chúng, và nginx nằm
cùng mạng nội bộ của compose. Mở thêm cổng cho chúng chỉ tạo một lối vào thứ hai
bỏ qua nginx.

Cách gọn hơn là để nginx proxy luôn `/api/*` về backend, khi đó mọi thứ cùng một
gốc và không cần CORS. Chưa làm vì nó đổi giá trị `NEXT_PUBLIC_BACKEND_URL` giữa
lúc chạy dev và lúc chạy Docker, tức là hai cấu hình phải nhớ thay vì một. Với
quy mô đồ án thì cái giá đó lớn hơn cái lợi.
