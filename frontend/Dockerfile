# Website khách hàng.
#
# Ba tầng: cài thư viện, dựng bản production, rồi chép sang một ảnh chỉ chứa thứ
# chạy được. Ảnh cuối không có `node_modules` đầy đủ, không có mã nguồn TypeScript.
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app

# Địa chỉ backend bị **nướng vào mã JavaScript lúc dựng**, không đọc lúc chạy:
# `NEXT_PUBLIC_*` là biến của trình duyệt, mà trình duyệt thì không thấy biến môi
# trường của container. Đổi địa chỉ này nghĩa là phải dựng lại ảnh, không phải
# sửa `docker-compose.yml` rồi khởi động lại.
ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8020
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3100 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 10001 -S web && adduser -S web -u 10001 -G web

# Ba dòng chép này phải đủ cả ba. Thiếu `public` là mất bộ ảnh nền Nhật Bản;
# thiếu `.next/static` là trang vẫn lên nhưng không có CSS lẫn JavaScript, nhìn
# như một trang HTML trần.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=web:web /app/.next/standalone ./
COPY --from=builder --chown=web:web /app/.next/static ./.next/static

USER web
EXPOSE 3100
CMD ["node", "server.js"]
