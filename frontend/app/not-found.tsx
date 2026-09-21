import ChatWidget from "@/components/ChatWidget";
import NotFoundContent from "@/components/site/NotFoundContent";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";

/**
 * Trang 404 cho địa chỉ không khớp route nào.
 *
 * Next chỉ dùng `not-found.tsx` trong nhóm `(site)` khi một trang **thuộc nhóm
 * đó** gọi `notFound()`. Gõ nhầm một địa chỉ bất kỳ thì nó tìm file này ở gốc;
 * thiếu file này, nó trả trang mặc định của Next — nền trắng, chữ tiếng Anh,
 * không có thanh điều hướng nào. Khách vào nhầm là mắc kẹt, không có đường về.
 *
 * Phải tự dựng lại khung website ở đây vì `(site)/layout.tsx` không bao trùm
 * trang này.
 */
export default function RootNotFound() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="flex-1">
        <NotFoundContent />
      </main>
      <SiteFooter />
      <ChatWidget />
    </div>
  );
}
