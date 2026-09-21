import type { Metadata } from "next";
import ForgotPasswordForm from "@/components/portal/ForgotPasswordForm";
import { Section } from "@/components/ui/primitives";

export const metadata: Metadata = {
  title: "Quên mật khẩu",
  description:
    "Gửi yêu cầu để nhân viên đặt lại mật khẩu tài khoản hệ thống khách hàng.",
};

export default function ForgotPasswordPage() {
  return (
    <Section>
      <ForgotPasswordForm />
    </Section>
  );
}
