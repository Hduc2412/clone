"use client";

/**
 * Mở đầu trang chủ — theo bản thiết kế "Hành trình Nhật Bản" (08/10).
 *
 * Ảnh Phú Sĩ toàn bề rộng, trôi rất chậm (25 giây một chiều). Chuyển động có **nút
 * dừng** vì nó là thứ người dùng không chọn: ai thấy chóng mặt hay mất tập trung thì
 * dừng được ngay, không phải đi tìm cài đặt hệ điều hành. Bật "giảm chuyển động" trong
 * hệ điều hành thì ảnh đứng yên từ đầu (`globals.css`).
 *
 * Chữ nằm trên lớp phủ xanh rêu đậm ở nửa trái — tương phản không phụ thuộc vùng ảnh
 * nào đang ở dưới.
 */
import Link from "next/link";
import { useState } from "react";

export default function HomeHero() {
  const [dung, setDung] = useState(false);

  return (
    <section className="relative isolate overflow-hidden bg-[#244545] text-white" aria-label="Giới thiệu">
      <div
        aria-hidden
        className="hero-anh absolute inset-0 bg-cover"
        style={{
          backgroundImage: "url('/nen/fuji-binh-minh.webp')",
          backgroundPosition: "center 58%",
          animationPlayState: dung ? "paused" : "running",
        }}
      />
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(90deg, rgba(12,37,36,.88), rgba(12,37,36,.5) 48%, rgba(12,37,36,.08) 80%), linear-gradient(0deg, rgba(22,58,56,.45), transparent 60%)",
        }}
      />
      <p
        aria-hidden
        className="absolute right-10 top-14 hidden text-3xl tracking-[0.3em] text-white/90 lg:block"
        style={{ writingMode: "vertical-rl" }}
      >
        富士山
        <span className="mt-6 block text-[10px] tracking-[0.35em] text-white/70">PHÚ SĨ · NHẬT BẢN</span>
      </p>

      <div className="relative mx-auto w-full max-w-container px-4 pb-16 pt-20 sm:px-6 md:pb-24 md:pt-24">
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#e6e4d9]">
          Một hành trình mới, một khởi đầu vững vàng
        </p>
        <h1 className="mt-4 text-4xl font-semibold leading-[1.12] tracking-tight md:text-6xl">
          Đến Nhật Bản.
          <span className="chu-nhan mt-1 block text-[#f2d9ad]">Bắt đầu từ bạn.</span>
        </h1>
        <p className="mt-6 max-w-xl text-base leading-7 text-[#f1f4ec] md:text-lg">
          Hiểu hồ sơ của mình. Tìm công việc phù hợp. Cùng chuẩn bị từng bước cho hành
          trình phía trước.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/tu-van"
            className="inline-flex min-h-[48px] items-center rounded-md bg-brand-600 px-6 font-semibold text-white transition-colors hover:bg-brand-700"
          >
            Khám phá cơ hội từ CV ↗
          </Link>
          <Link
            href="/don-hang"
            className="inline-flex min-h-[48px] items-center rounded-md border border-white/60 bg-white/5 px-6 font-semibold text-white backdrop-blur transition-colors hover:bg-white/15"
          >
            Xem đơn tuyển dụng
          </Link>
        </div>
        <p className="mt-9 flex items-center gap-3 text-sm text-[#e0e9df]">
          <span aria-hidden className="h-px w-8 bg-[#e5d0a4]" />
          Bạn tự chọn hướng đi. Chúng tôi giúp bạn hiểu rõ lựa chọn.
        </p>
      </div>

      <button
        type="button"
        onClick={() => setDung((d) => !d)}
        aria-pressed={dung}
        className="absolute bottom-4 right-4 rounded-full bg-[#203c39]/80 px-4 py-2 text-xs font-medium text-white backdrop-blur hover:bg-[#203c39]"
      >
        {dung ? "▶ Tiếp tục chuyển động" : "II Dừng chuyển động"}
      </button>
    </section>
  );
}
