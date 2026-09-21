"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApplicationCard } from "@/components/portal/PortalStages";
import { Button, Card } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import { PortalError, PortalOverview, cellValue, fetchOverview, logout } from "@/lib/portalApi";

/**
 * Màn hình chính của hệ khách hàng.
 *
 * Gọi đúng **một** endpoint gộp thay vì ba lượt riêng: phần lớn ứng viên mở
 * trang này bằng điện thoại, nhiều khi ở vùng sóng yếu, nên ba lượt gọi là ba
 * cơ hội để một lượt hỏng và màn hình hiện ra một nửa.
 */
export default function PortalDashboard() {
  const router = useRouter();
  const [data, setData] = useState<PortalOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchOverview()
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof PortalError && reason.status === 401) {
          router.replace("/tai-khoan/dang-nhap");
          return;
        }
        // 409 nghĩa là còn dùng mật khẩu nhân viên cấp, phải đổi trước đã.
        if (reason instanceof PortalError && reason.status === 409) {
          router.replace("/tai-khoan/doi-mat-khau");
          return;
        }
        setError(reason instanceof Error ? reason.message : "Không tải được hồ sơ.");
      })
      .finally(() => setLoading(false));
  }, [router]);

  const signOut = () => {
    logout()
      .catch(() => undefined)
      .finally(() => router.replace("/tai-khoan/dang-nhap"));
  };

  if (loading) {
    return <p className="text-sm text-slate-500">Đang tải hồ sơ của bạn…</p>;
  }

  if (error) {
    return (
      <Card className="p-6">
        <p className="text-sm text-red-600">{error}</p>
        <p className="mt-2 text-sm text-slate-600">
          Bạn thử tải lại trang, hoặc gọi {COMPANY.hotline} nếu vẫn không được.
        </p>
      </Card>
    );
  }

  if (!data) return null;

  const { profile, applications, account } = data;
  const summary: { label: string; value: string }[] = [];
  if (profile) {
    const japanese =
      profile.labels?.japanese_level || cellValue<string>(profile.fields, "japanese_level");
    const education =
      profile.labels?.education_level || cellValue<string>(profile.fields, "education_level");
    const birthYear = cellValue<number>(profile.fields, "birth_year");
    const region =
      profile.labels?.desired_region_group ||
      profile.labels?.desired_prefecture ||
      cellValue<string>(profile.preferences, "desired_prefecture");
    if (japanese) summary.push({ label: "Trình độ tiếng Nhật", value: String(japanese) });
    if (education) summary.push({ label: "Bằng cấp", value: String(education) });
    if (birthYear) summary.push({ label: "Năm sinh", value: String(birthYear) });
    if (region) summary.push({ label: "Nơi mong muốn", value: String(region) });
  }

  return (
    <div className="space-y-8">
      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
              Hồ sơ của bạn
            </p>
            <h2 className="mt-1 text-lg font-bold text-slate-900">
              {account.full_name || "Ứng viên"}
            </h2>
            <p className="mt-1 text-sm text-slate-500">{account.phone}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button href="/tai-khoan/doi-mat-khau" variant="outline">
              Đổi mật khẩu
            </Button>
            <Button variant="outline" onClick={signOut}>
              Đăng xuất
            </Button>
          </div>
        </div>

        {summary.length > 0 ? (
          <dl className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {summary.map((row) => (
              <div key={row.label}>
                <dt className="text-xs text-slate-500">{row.label}</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">{row.value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-5 text-sm leading-6 text-slate-600">
            Chưa có thông tin năng lực gắn với tài khoản này. Nhân viên sẽ bổ sung
            khi trao đổi với bạn.
          </p>
        )}
      </Card>

      <div>
        <h2 className="text-lg font-bold text-slate-900">Đơn bạn đã đăng ký</h2>
        {applications.length === 0 ? (
          <Card className="mt-4 p-6">
            <p className="text-sm leading-6 text-slate-600">
              Chưa có đơn nào gắn với tài khoản này. Bạn xem đơn đang tuyển rồi đối
              chiếu hồ sơ để chọn đơn phù hợp.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button href="/don-hang">Xem đơn đang tuyển</Button>
              <Button href="/tu-van" variant="outline">
                Đối chiếu hồ sơ
              </Button>
            </div>
          </Card>
        ) : (
          <div className="mt-4 space-y-5">
            {applications.map((item) => (
              <ApplicationCard key={item.application_code} item={item} />
            ))}
          </div>
        )}
      </div>

      <Card className="border-slate-200 bg-slate-50 p-5">
        <p className="text-xs leading-5 text-slate-500">
          Trạng thái trên đây là trạng thái thật nhân viên đang đặt cho hồ sơ của
          bạn, cập nhật ngay khi họ thay đổi. Có gì chưa rõ thì gọi{" "}
          {COMPANY.hotline} trong giờ làm việc.
        </p>
      </Card>
    </div>
  );
}
