import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Luồng đối chiếu hồ sơ gắn với phiên của từng người, không có gì để lập
      // chỉ mục và không nên xuất hiện trên kết quả tìm kiếm.
      disallow: ["/tu-van", "/chat"],
    },
    sitemap: "https://xklddieuduong.vn/sitemap.xml",
  };
}
