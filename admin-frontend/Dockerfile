# Hệ thống quản trị. Giống ảnh website, khác cổng và khác biến dựng.
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app

# Xem ghi chú ở `frontend/Dockerfile`: giá trị này nướng vào mã lúc dựng, đổi thì
# phải dựng lại ảnh.
ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8020
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3101 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 10001 -S admin && adduser -S admin -u 10001 -G admin

# Không chép `public/`: hệ thống quản trị không có thư mục đó, và `COPY` một
# đường dẫn không tồn tại làm hỏng cả lượt dựng.
COPY --from=builder --chown=admin:admin /app/.next/standalone ./
COPY --from=builder --chown=admin:admin /app/.next/static ./.next/static

USER admin
EXPOSE 3101
CMD ["node", "server.js"]
