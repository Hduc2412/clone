import ChatWidget from "@/components/ChatWidget";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";

/**
 * Khung chung của website khách hàng.
 *
 * Khung chat được nhúng ở đây nên nó xuất hiện trên mọi trang nội dung mà không
 * phải thêm vào từng trang. Thành phần `ChatWidget` thuộc phần do nhóm khác
 * phát triển: ở đây chỉ gọi nó ra, không sửa gì bên trong.
 */
export default function SiteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="flex-1">{children}</main>
      <SiteFooter />
      <ChatWidget />
    </div>
  );
}
