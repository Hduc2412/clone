import type { MetadataRoute } from "next";
import { NAV } from "@/content/site";
import { fetchJobOrders } from "@/lib/publicApi";

const BASE_URL = "https://xklddieuduong.vn";

/**
 * Dựng lại sitemap mỗi giờ thay vì đóng băng nó lúc `npm run build`.
 *
 * Mặc định Next coi route này là tĩnh và gọi `fetchJobOrders` **một lần duy nhất
 * lúc dựng ảnh**. Khi đóng gói Docker, lúc dựng ảnh thì backend chưa chạy: lời
 * gọi thất bại, danh sách rỗng, và sitemap gửi cho công cụ tìm kiếm vĩnh viễn
 * không có một trang đơn hàng nào — thứ mà người ta tìm nhiều nhất. Nó cũng
 * không tự sửa khi thêm đơn mới, vì file đã nằm sẵn trong ảnh.
 *
 * Dựng theo từng lượt gọi thay vì đặt `revalidate`: công cụ tìm kiếm đọc file
 * này vài lần một ngày, nên cái giá là vài lời gọi API, còn cái được là nó không
 * bao giờ sai. Đặt `revalidate` một giờ thì ngay sau mỗi lần triển khai vẫn có
 * một giờ sitemap rỗng — đúng lúc người ta hay nhìn vào nhất.
 *
 * Backend chết thì `fetchJobOrders` trả danh sách rỗng, sitemap còn các trang
 * tĩnh chứ không lỗi cả file.
 */
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages = ["/", ...NAV.map((item) => item.href)].map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: path === "/" ? 1 : 0.7,
  }));

  // Trang chi tiết đơn hàng thay đổi thường xuyên hơn và cũng là thứ người ta
  // tìm nhiều nhất, nên khai báo riêng thay vì để công cụ tìm kiếm tự dò.
  const orders = await fetchJobOrders({ limit: 100 });
  const orderPages = orders.map((order) => ({
    url: `${BASE_URL}/don-hang/${order.code}`,
    lastModified: new Date(),
    changeFrequency: "daily" as const,
    priority: 0.8,
  }));

  return [...staticPages, ...orderPages];
}
