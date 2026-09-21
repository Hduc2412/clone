"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Appointment,
  CandidateProfile,
  JobOrder,
  QueuedRegistration,
  ScoreTotal,
  managementApi,
  Overview,
} from "@/lib/managementApi";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";

/**
 * Trung tâm điều hành.
 *
 * Trang này trước đây hiện bốn số của hệ thống cũ — lịch hẹn, khách hàng, hội
 * thoại, thông báo — và không nhắc gì tới chuỗi nghiệp vụ chính. Quản lý mở ra
 * buổi sáng thì không biết có bao nhiêu hồ sơ đang chờ người nhận, hay đơn nào
 * sắp hết hạn.
 *
 * Nay xếp theo đúng chuỗi: đơn hàng → ứng viên → hàng đợi → nhân viên. Mỗi con số
 * bấm được để đi thẳng tới màn hình xử lý, vì một con số không hành động được thì
 * chỉ để trang trí.
 */

const EMPTY_OVERVIEW: Overview = {
  appointments_total: 0,
  appointments_pending: 0,
  appointments_confirmed: 0,
  appointments_completed: 0,
  leads_total: 0,
  leads_new: 0,
  conversations_total: 0,
  messages_total: 0,
  notifications_unread: 0,
  staff_active: 0,
};

/** Đơn sắp hết hạn trong bao nhiêu ngày thì coi là cần để mắt. */
const SAP_HET_HAN_NGAY = 14;

export default function AdminDashboard() {
  const [overview, setOverview] = useState(EMPTY_OVERVIEW);
  const [orders, setOrders] = useState<JobOrder[]>([]);
  const [queue, setQueue] = useState<QueuedRegistration[]>([]);
  const [profiles, setProfiles] = useState<CandidateProfile[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [scores, setScores] = useState<ScoreTotal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Mỗi nguồn hỏng riêng lẻ không được làm trắng cả trang: quản lý vẫn cần
    // thấy những phần còn lấy được.
    const an = <T,>(p: Promise<T>, duPhong: T) => p.catch(() => duPhong);

    Promise.all([
      an(managementApi.overview(), EMPTY_OVERVIEW),
      an(managementApi.jobOrders(), [] as JobOrder[]),
      an(managementApi.registrationQueue(), { items: [], count: 0 }),
      an(managementApi.candidateProfiles(), [] as CandidateProfile[]),
      an(managementApi.appointments(), [] as Appointment[]),
      an(managementApi.scoreboard(), { items: [] as ScoreTotal[], rules: [] }),
    ])
      .then(([ov, don, hangDoi, hoSo, lich, bangDiem]) => {
        setOverview(ov);
        setOrders(don);
        setQueue(hangDoi.items);
        setProfiles(hoSo);
        setAppointments(lich);
        setScores(bangDiem.items);
      })
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  const homNay = new Date().toISOString().slice(0, 10);

  const donDangTuyen = orders.filter((o) => o.status === "open");
  const donHienTrenWeb = orders.filter(
    (o) => o.published && o.status === "open" && o.deadline >= homNay,
  );
  const donSapHetHan = donDangTuyen.filter((o) => {
    const conLai = Math.ceil(
      (new Date(`${o.deadline}T00:00:00`).getTime() - Date.now()) / 86_400_000,
    );
    return conLai >= 0 && conLai <= SAP_HET_HAN_NGAY;
  });
  const donQuaHan = orders.filter((o) => o.status === "open" && o.deadline < homNay);

  const chuaAiNhan = queue.filter((r) => !r.assigned_to).length;
  const hoSoDaXacNhan = profiles.filter((p) => p.status === "confirmed").length;
  const lichChoXuLy = appointments.filter((a) => a.status === "pending").length;

  const the = useMemo(
    () => [
      {
        nhan: "Hồ sơ chờ nhận",
        so: chuaAiNhan,
        phu:
          queue.length > chuaAiNhan
            ? `${queue.length - chuaAiNhan} hồ sơ đã có người phụ trách`
            : "Chưa ai nhận hồ sơ nào",
        mau: chuaAiNhan > 0 ? "bg-red-50 text-[#b51718]" : "bg-slate-100 text-slate-500",
        icon: "▤",
        toi: "/admin/queue",
        gap: chuaAiNhan > 0,
      },
      {
        nhan: "Đơn đang tuyển",
        so: donDangTuyen.length,
        phu: `${donHienTrenWeb.length} đơn đang hiện trên website`,
        mau: "bg-emerald-50 text-emerald-700",
        icon: "▣",
        toi: "/admin/job-orders",
        gap: false,
      },
      {
        nhan: "Đơn sắp hết hạn",
        so: donSapHetHan.length,
        // Đơn quá hạn mà vẫn để trạng thái đang tuyển là việc cần xử lý gấp hơn
        // đơn sắp hết hạn, nên nói thẳng là "thêm" để không ai tưởng hai con số
        // này là một.
        phu:
          donQuaHan.length > 0
            ? `Trong ${SAP_HET_HAN_NGAY} ngày tới · thêm ${donQuaHan.length} đơn đã quá hạn mà chưa đóng`
            : `Trong ${SAP_HET_HAN_NGAY} ngày tới`,
        mau:
          donSapHetHan.length > 0 || donQuaHan.length > 0
            ? "bg-amber-50 text-amber-700"
            : "bg-slate-100 text-slate-500",
        icon: "◷",
        toi: "/admin/job-orders",
        gap: donQuaHan.length > 0,
      },
      {
        nhan: "Hồ sơ ứng viên",
        so: profiles.length,
        phu: `${hoSoDaXacNhan} hồ sơ đã được ứng viên xác nhận`,
        mau: "bg-blue-50 text-blue-700",
        icon: "☺",
        toi: "/admin/profiles",
        gap: false,
      },
    ],
    [
      chuaAiNhan,
      queue.length,
      donDangTuyen.length,
      donHienTrenWeb.length,
      donSapHetHan.length,
      donQuaHan.length,
      profiles.length,
      hoSoDaXacNhan,
    ],
  );

  return (
    <>
      <PageHeader
        eyebrow="Trung tâm điều hành"
        title="Tổng quan hôm nay"
        description="Bốn con số đầu là việc cần làm ngay. Bấm vào con số để đi thẳng tới màn hình xử lý."
      />
      {error && <ErrorBanner message={error} />}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {the.map((t) => (
          <Link
            key={t.nhan}
            href={t.toi}
            className={`rounded-2xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md ${
              t.gap ? "border-red-200" : "border-slate-200"
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-slate-500">{t.nhan}</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight">
                  {loading ? "—" : t.so}
                </p>
              </div>
              <span
                className={`flex h-11 w-11 items-center justify-center rounded-xl text-xl font-semibold ${t.mau}`}
              >
                {t.icon}
              </span>
            </div>
            <p className="mt-4 text-xs text-slate-400">{t.phu}</p>
          </Link>
        ))}
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Khung
          tieuDe="Hồ sơ chờ nhận xử lý"
          phu="Ứng viên đã chọn đơn và đang đợi nhân viên gọi lại"
          toi="/admin/queue"
          rong={queue.length === 0 && !loading}
          khiRong={{
            title: "Hàng đợi đang trống",
            description: "Hồ sơ ứng viên đăng ký trên website sẽ xuất hiện tại đây.",
          }}
        >
          {queue.slice(0, 6).map((r) => (
            <div key={r.application_code} className="flex flex-wrap items-center gap-3 px-5 py-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-50 text-sm font-semibold text-[#cb1d1e]">
                {(r.customer_name ?? "?").slice(0, 1).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{r.customer_name}</p>
                <p className="mt-1 truncate text-xs text-slate-400">
                  {r.application_code}
                  {r.job_order_code ? ` · chọn đơn ${r.job_order_code}` : ""}
                </p>
              </div>
              <span
                className={`rounded-lg px-2.5 py-1 text-xs font-medium ${
                  r.assigned_to
                    ? "bg-slate-100 text-slate-600"
                    : "bg-red-50 text-[#b51718]"
                }`}
              >
                {r.assigned_to ?? "Chưa ai nhận"}
              </span>
            </div>
          ))}
        </Khung>

        <div className="space-y-6">
          <Khung
            tieuDe="Điểm nhân viên"
            phu="Tính theo từng sự kiện, truy ngược được"
            toi="/admin/staff-scores"
            rong={scores.length === 0 && !loading}
            khiRong={{
              title: "Chưa có điểm nào",
              description: "Điểm sinh ra khi nhân viên nhận và xử lý hồ sơ.",
            }}
          >
            {scores.slice(0, 5).map((s) => (
              <div key={s.staff_email} className="flex items-center justify-between px-5 py-3.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{s.staff_email}</p>
                  <p className="mt-0.5 text-xs text-slate-400">{s.events} sự kiện</p>
                </div>
                <span className="shrink-0 text-lg font-semibold text-slate-900">
                  {s.points}
                </span>
              </div>
            ))}
          </Khung>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Phần tư vấn tự động</h3>
            <dl className="mt-3 space-y-2 text-sm">
              <Dong nhan="Lịch chờ xác nhận" gia_tri={lichChoXuLy} toi="/admin/appointments" />
              <Dong nhan="Khách hàng đang quản lý" gia_tri={overview.leads_total} toi="/admin/leads" />
              <Dong nhan="Hội thoại đã lưu" gia_tri={overview.conversations_total} toi="/admin/conversations" />
              <Dong nhan="Nhân viên đang hoạt động" gia_tri={overview.staff_active} toi="/admin/users" />
            </dl>
          </div>
        </div>
      </section>
    </>
  );
}

function Khung({
  tieuDe,
  phu,
  toi,
  rong,
  khiRong,
  children,
}: {
  tieuDe: string;
  phu: string;
  toi: string;
  rong: boolean;
  khiRong: { title: string; description: string };
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <h3 className="font-semibold">{tieuDe}</h3>
          <p className="mt-1 text-xs text-slate-400">{phu}</p>
        </div>
        <Link href={toi} className="shrink-0 text-sm font-medium text-[#cb1d1e]">
          Xem tất cả
        </Link>
      </div>
      {rong ? (
        <div className="p-5">
          <EmptyState title={khiRong.title} description={khiRong.description} />
        </div>
      ) : (
        <div className="divide-y divide-slate-100">{children}</div>
      )}
    </div>
  );
}

function Dong({ nhan, gia_tri, toi }: { nhan: string; gia_tri: number; toi: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt>
        <Link href={toi} className="text-slate-600 hover:text-[#cb1d1e]">
          {nhan}
        </Link>
      </dt>
      <dd className="font-medium text-slate-900">{gia_tri}</dd>
    </div>
  );
}
