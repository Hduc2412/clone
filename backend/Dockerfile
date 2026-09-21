# Backend FastAPI.
#
# Dùng Python 3.12 chứ không phải 3.14 đang chạy trên máy phát triển. PyMuPDF và
# một vài thư viện nhị phân khác có sẵn wheel cho 3.12; với 3.14 thì tùy thời
# điểm, và một ảnh Docker phải dựng lại được sau nhiều tháng chứ không chỉ hôm
# nay.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# `curl` để healthcheck của compose gọi được. Không cài thêm gì nữa: các thư
# viện đọc PDF và Excel đều có wheel dựng sẵn, không cần trình biên dịch.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Chép riêng danh sách thư viện trước phần mã nguồn. Sửa một dòng code thì lớp
# cài đặt vẫn nằm trong bộ nhớ đệm, dựng lại mất vài giây thay vì vài phút.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# CV ứng viên gửi lên nằm ở đây. Khai thành volume trong compose, nếu không thì
# xóa container là mất hết bản gốc mà nhân viên cần đối chiếu.
RUN mkdir -p storage \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app
USER app

EXPOSE 8020

# Không gọi `python main.py`: khối đó bật `reload=True` cho lúc phát triển, và
# `API_HOST` mặc định là 127.0.0.1 — trong container thì không ai ngoài chính nó
# gọi vào được.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8020"]
