import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import OrderConsultationRoom from "@/components/candidate/OrderConsultationRoom";
import { fetchJobOrder } from "@/lib/publicApi";

/**
 * Phòng tư vấn cho một đơn cụ thể.
 *
 * Tách khỏi `/tu-van` — trang kia trả lời *"tôi hợp đơn nào"* bằng cách đối chiếu
 * cả danh mục rồi xếp hạng. Trang này trả lời câu hẹp hơn và thường là câu người
 * ta thật sự đang có: *"tôi có hợp **đơn này** không"*, vì họ vừa đọc xong đúng
 * đơn ấy.
 *
 * Hai cửa dùng chung một bộ đối chiếu, không có engine thứ hai.
 *
 * Phần vỏ trang dựng trên máy chủ để lấy tên đơn thật cho tiêu đề và cho thẻ
 * chia sẻ; phần tư vấn là client vì nó cần cookie phiên và dữ liệu riêng của
 * từng người.
 */

export async function generateMetadata({
  params,
}: {
  params: { code: string };
}): Promise<Metadata> {
  const order = await fetchJobOrder(params.code);
  if (!order) return { title: "Không tìm thấy đơn" };
  return {
    title: `Tư vấn đơn ${order.code} | Điều dưỡng Nhật Bản DC`,
    description: `Đối chiếu hồ sơ của bạn với đơn ${order.title} và biết rõ đạt hay chưa đạt ở từng điều kiện.`,
  };
}

export default async function Page({ params }: { params: { code: string } }) {
  const order = await fetchJobOrder(params.code);
  if (!order) notFound();

  return (
    <>
      {/* Dải đầu theo bản thiết kế 08/10: ảnh Phú Sĩ mờ dưới lớp ngà, chữ đậm bên trái. */}
      <section
        className="relative border-b border-slate-200 bg-cover"
        style={{
          backgroundImage:
            "linear-gradient(90deg, #efeee5 40%, rgba(239,238,229,.87)), url('/nen/fuji-binh-minh-nho.webp')",
          backgroundPosition: "center 45%",
        }}
      >
        <div className="relative mx-auto max-w-container px-4 py-7 sm:px-6 md:py-8">
          <Link
            href={`/don-hang/${order.code}`}
            className="text-sm font-medium text-slate-600 hover:text-brand-600"
          >
            ← Xem lại chi tiết đơn
          </Link>
          <p className="mt-4 text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600 sm:text-[11px]">
            Phòng tư vấn của bạn · Đơn {order.code}
          </p>
          <h1 className="mt-3 text-3xl font-medium leading-tight tracking-tight text-slate-900 md:text-[38px]">
            Hiểu hồ sơ.{" "}
            <span className="chu-nhan mt-1 block sm:mt-0 sm:inline">Chọn đúng hướng.</span>
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            {order.title} · {order.employer_name}
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-container px-4 pb-20 pt-6 sm:px-6">
        <OrderConsultationRoom orderCode={order.code} />
      </section>
    </>
  );
}
