import type { Metadata } from "next";
import ChangePasswordForm from "@/components/portal/ChangePasswordForm";
import { Section } from "@/components/ui/primitives";

export const metadata: Metadata = {
  title: "Đổi mật khẩu",
  description: "Đặt mật khẩu riêng cho tài khoản hệ thống khách hàng.",
};

export default function PortalChangePasswordPage() {
  return (
    <Section>
      <ChangePasswordForm />
    </Section>
  );
}
