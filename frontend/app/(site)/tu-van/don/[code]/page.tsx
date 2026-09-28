import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import OrderConsultationRoom from "@/components/candidate/OrderConsultationRoom";
import PhotoBackdrop from "@/components/site/PhotoBackdrop";
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
      <section className="relative overflow-hidden">
        <PhotoBackdrop variant="soft" />
        <div className="relative mx-auto max-w-4xl px-4 py-12 md:px-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#cb1d1e]">
            Phòng tư vấn theo đơn
          </p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight text-slate-900 md:text-4xl">
            Bạn có hợp đơn này không
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-slate-600">
            {order.title} · {order.employer_name} · Mã đơn {order.code}
          </p>
          <Link
            href={`/don-hang/${order.code}`}
            className="mt-4 inline-block text-sm font-medium text-[#cb1d1e] hover:underline"
          >
            ← Xem lại chi tiết đơn
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-4 pb-20 md:px-6">
        <OrderConsultationRoom orderCode={order.code} />
      </section>
    </>
  );
}
