import type { Metadata } from "next";
import PortalDashboard from "@/components/portal/PortalDashboard";
import PageHero from "@/components/site/PageHero";
import { Section } from "@/components/ui/primitives";

export const metadata: Metadata = {
  title: "Hệ thống khách hàng",
  description:
    "Ứng viên đã có tài khoản đăng nhập để xem trình độ đã khai, đơn đã đăng ký và hồ sơ đang ở bước nào.",
};

export default function PortalHomePage() {
  return (
    <>
      <PageHero
        eyebrow="Hệ thống khách hàng"
        title="Hồ sơ của bạn đang ở đâu"
        lead="Trạng thái ở đây là trạng thái thật nhân viên đang đặt cho hồ sơ của bạn, đổi tới đâu bạn thấy tới đó."
      />
      <Section>
        <PortalDashboard />
      </Section>
    </>
  );
}
