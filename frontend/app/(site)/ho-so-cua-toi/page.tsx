import type { Metadata } from "next";
import StatusTracker from "@/components/candidate/StatusTracker";
import PageHero from "@/components/site/PageHero";
import { Section } from "@/components/ui/primitives";

export const metadata: Metadata = {
  title: "Hồ sơ của tôi",
  description:
    "Xem trình độ đã khai, đơn đã đăng ký và hồ sơ của bạn đang ở bước nào trong quy trình tuyển dụng điều dưỡng Nhật Bản.",
};

export default function MyProfilePage() {
  return (
    <>
      <PageHero
        eyebrow="Hồ sơ của tôi"
        title="Hồ sơ của bạn đang ở đâu"
        lead="Xem lại trình độ đã khai, đơn đã đăng ký, và hồ sơ của bạn đang ở bước nào — cập nhật theo đúng trạng thái nhân viên đặt, không phải một dòng chờ chung chung."
      />
      <Section>
        <StatusTracker />
      </Section>
    </>
  );
}
