import type { Metadata } from "next";
import LoginForm from "@/components/portal/LoginForm";
import { Section } from "@/components/ui/primitives";

export const metadata: Metadata = {
  title: "Đăng nhập",
  description:
    "Ứng viên đã được cấp tài khoản đăng nhập bằng số điện thoại để theo dõi hồ sơ của mình.",
};

export default function PortalLoginPage() {
  return (
    <Section>
      <LoginForm />
    </Section>
  );
}
