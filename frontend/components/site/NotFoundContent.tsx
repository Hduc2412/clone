import PhotoBackdrop from "@/components/site/PhotoBackdrop";
import { Button, Container } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";

/**
 * Nội dung trang không tìm thấy.
 *
 * Tách riêng vì Next cần **hai** trang 404 khác nhau và cả hai phải giống nhau:
 *
 * - `app/(site)/not-found.tsx` — cho các trang trong nhóm gọi `notFound()`, ví
 *   dụ mở một mã đơn không có thật.
 * - `app/not-found.tsx` — cho địa chỉ không khớp route nào. Thiếu file này thì
 *   Next trả trang mặc định của nó: nền trắng, chữ tiếng Anh, **không có thanh
 *   điều hướng nào để quay lại**. Khách gõ nhầm địa chỉ là mắc kẹt ở đó.
 *
 * Để một chỗ rồi hai nơi cùng gọi, thay vì chép nội dung hai lần rồi sửa lệch.
 */
export default function NotFoundContent() {
  return (
    <section className="relative overflow-hidden">
      <PhotoBackdrop variant="soft" />
      <Container className="relative py-24 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-600">
          Không tìm thấy
        </p>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-900">
          Trang này không còn nữa
        </h1>
        <p className="mx-auto mt-4 max-w-lg text-base leading-7 text-slate-600">
          Có thể đơn hàng bạn tìm đã hết hạn nộp hoặc đã tuyển đủ người. Xem danh
          sách đơn đang tuyển, hoặc gọi {COMPANY.hotline} để được tư vấn đơn phù
          hợp.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button href="/don-hang">Xem đơn đang tuyển</Button>
          <Button href="/" variant="outline">
            Về trang chủ
          </Button>
        </div>
      </Container>
    </section>
  );
}
