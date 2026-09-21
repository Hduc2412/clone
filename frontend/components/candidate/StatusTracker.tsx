"use client";

import { useEffect, useState } from "react";
import { Badge, Button, Card } from "@/components/ui/primitives";
import { COMPANY } from "@/content/site";
import {
  CandidateProfile,
  MyRegistration,
  fetchMyRegistrations,
  fetchProfile,
  valueOf,
} from "@/lib/candidateApi";
import { peekSessionId } from "@/lib/journeySession";

/**
 * Trang ứng viên tự theo dõi hồ sơ của mình.
 *
 * Trước đây đăng ký xong là hồ sơ thành hộp đen: trang tư vấn chỉ nói "chờ nhân
 * viên liên hệ", bất kể nhân viên đã đẩy hồ sơ tới bước nào. Backend có đủ mười
 * ba trạng thái và trả về đúng trạng thái hiện tại, nhưng không màn hình nào cho
 * ứng viên thấy. Người vừa gửi hồ sơ xong thì sốt ruột nhất, mà lại không biết
 * hỏi ai ngoài gọi điện.
 *
 * Trang này gộp mười ba trạng thái nội bộ thành năm chặng ứng viên hiểu được, và
 * hiển thị đúng chặng đang tới. Không bịa thêm: chặng hiện ra là trạng thái thật
 * nhân viên đặt, chỉ đổi sang thứ ngôn ngữ người đọc kiểm chứng được.
 *
 * Giới hạn thành thật, nói rõ trên trang: nhận diện bằng phiên lưu trong trình
 * duyệt này. Xóa dữ liệu duyệt hoặc đổi máy thì mất đường vào — tra cứu bằng số
 * điện thoại cần một lớp xác thực riêng, chưa làm.
 */

// Năm chặng ứng viên nhìn thấy, theo thứ tự tiến. Mỗi chặng gộp vài trạng thái
// nội bộ: ứng viên không cần phân biệt "thu giấy tờ" với "sơ tuyển", họ cần biết
// "đang được xem xét".
const STAGES = [
  {
    key: "registered",
    label: "Đã đăng ký",
    note: "Hồ sơ của bạn đã vào hàng đợi, đang chờ nhân viên nhận và gọi lại.",
  },
  {
    key: "reviewing",
    label: "Đang xem xét",
    note: "Nhân viên đang đối chiếu hồ sơ và giấy tờ của bạn với yêu cầu của đơn.",
  },
  {
    key: "qualified",
    label: "Đủ điều kiện sơ bộ",
    note: "Hồ sơ đạt vòng sơ tuyển. Bước tiếp theo là chuẩn bị và phỏng vấn.",
  },
  {
    key: "accepted",
    label: "Đã trúng tuyển",
    note: "Bạn đã qua phỏng vấn. Nhân viên đang cùng bạn hoàn tất thủ tục xuất cảnh.",
  },
  {
    key: "departed",
    label: "Đã xuất cảnh",
    note: "Chúc bạn mạnh khỏe và công tác tốt tại Nhật Bản.",
  },
] as const;

const STAGE_OF: Record<string, (typeof STAGES)[number]["key"]> = {
  draft: "registered",
  collecting_documents: "reviewing",
  screening: "reviewing",
  eligible: "qualified",
  training: "qualified",
  waiting_interview: "qualified",
  passed: "accepted",
  visa_processing: "accepted",
  ready_departure: "accepted",
  departed: "departed",
};

// Trạng thái đóng không nằm trên đường tiến. Hiện riêng, trung thực, kèm bước
// tiếp theo — một hồ sơ "chưa đạt" mà không nói làm gì tiếp thì tàn nhẫn hơn là
// hữu ích.
const CLOSED: Record<
  string,
  { label: string; tone: "warning" | "neutral"; note: string }
> = {
  rejected: {
    label: "Chưa đạt lần này",
    tone: "warning",
    note: "Đơn này chưa phù hợp. Gọi nhân viên để nghe rõ lý do và tìm đơn khác — chưa đạt một đơn không có nghĩa là hết cơ hội.",
  },
  withdrawn: {
    label: "Bạn đã rút hồ sơ",
    tone: "neutral",
    note: "Bạn đã rút khỏi đơn này. Muốn đăng ký đơn khác thì vào lại phần đối chiếu hồ sơ.",
  },
  cancelled: {
    label: "Đơn đăng ký đã hủy",
    tone: "neutral",
    note: "Đăng ký này đã được hủy. Nếu không phải do bạn yêu cầu, hãy gọi nhân viên để hỏi lại.",
  },
};

function stageIndex(status: string): number {
  const key = STAGE_OF[status];
  return key ? STAGES.findIndex((stage) => stage.key === key) : -1;
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function ProgressTracker({ status }: { status: string }) {
  const current = stageIndex(status);
  return (
    <ol className="mt-4 space-y-4">
      {STAGES.map((stage, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <li key={stage.key} className="flex gap-3">
            <span
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                active
                  ? "bg-brand-600 text-white"
                  : done
                    ? "bg-brand-100 text-brand-700"
                    : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? "✓" : index + 1}
            </span>
            <div className="min-w-0">
              <p
                className={`text-sm font-medium ${
                  active
                    ? "text-slate-900"
                    : done
                      ? "text-slate-600"
                      : "text-slate-400"
                }`}
              >
                {stage.label}
                {active && (
                  <span className="ml-2 align-middle">
                    <Badge tone="brand">Bước hiện tại</Badge>
                  </span>
                )}
              </p>
              {active && (
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  {stage.note}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function RegistrationCard({ item }: { item: MyRegistration }) {
  const closed = CLOSED[item.status];
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-base font-semibold text-slate-900">
            {item.job_order_title || item.job_order_code}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            Mã đơn {item.job_order_code} · Mã hồ sơ {item.application_code}
            {item.created_at && ` · Đăng ký ${formatDate(item.created_at)}`}
          </p>
        </div>
        {closed && <Badge tone={closed.tone}>{closed.label}</Badge>}
      </div>

      {closed ? (
        <p className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
          {closed.note}
        </p>
      ) : (
        <ProgressTracker status={item.status} />
      )}
    </Card>
  );
}

export default function StatusTracker() {
  const [loading, setLoading] = useState(true);
  const [hasSession, setHasSession] = useState(true);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [registrations, setRegistrations] = useState<MyRegistration[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const session = peekSessionId();
    if (!session) {
      setHasSession(false);
      setLoading(false);
      return;
    }
    Promise.all([
      fetchProfile(session).catch(() => null),
      fetchMyRegistrations(session)
        .then((data) => data.items)
        .catch(() => [] as MyRegistration[]),
    ])
      .then(([loadedProfile, loadedRegistrations]) => {
        setProfile(loadedProfile);
        setRegistrations(loadedRegistrations);
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "Không tải được hồ sơ."),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-sm text-slate-500">Đang tải hồ sơ của bạn…</p>;
  }

  if (!hasSession || (!profile && registrations.length === 0)) {
    return (
      <Card className="p-6">
        <h2 className="text-base font-bold text-slate-900">
          Chưa có hồ sơ trên thiết bị này
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Trang này hiện hồ sơ bạn đã nhập trên chính trình duyệt này. Nếu bạn
          từng nhập trên máy khác, hoặc đã xóa dữ liệu duyệt, thì hồ sơ không hiện
          ở đây — hãy gọi {COMPANY.hotline} để nhân viên tra giúp.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button href="/tu-van">Nhập hồ sơ và đối chiếu</Button>
          <Button href={COMPANY.hotlineHref} variant="outline">
            Gọi {COMPANY.hotline}
          </Button>
        </div>
      </Card>
    );
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

  const fullName = valueOf<string>(profile?.fields, "full_name");
  const summary: { label: string; value: string }[] = [];
  if (profile) {
    const japanese =
      profile.labels?.japanese_level ||
      valueOf<string>(profile.fields, "japanese_level");
    const education =
      profile.labels?.education_level ||
      valueOf<string>(profile.fields, "education_level");
    const region =
      profile.labels?.desired_region_group ||
      profile.labels?.desired_prefecture ||
      valueOf<string>(profile.preferences, "desired_prefecture");
    const birthYear = valueOf<number>(profile.fields, "birth_year");
    if (japanese) summary.push({ label: "Trình độ tiếng Nhật", value: String(japanese) });
    if (education) summary.push({ label: "Bằng cấp", value: String(education) });
    if (birthYear) summary.push({ label: "Năm sinh", value: String(birthYear) });
    if (region) summary.push({ label: "Nơi mong muốn", value: String(region) });
  }

  return (
    <div className="space-y-8">
      {profile && (
        <Card className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                Hồ sơ của bạn
              </p>
              <h2 className="mt-1 text-lg font-bold text-slate-900">
                {fullName || "Ứng viên"}
              </h2>
            </div>
            <Badge tone={profile.status === "confirmed" ? "success" : "warning"}>
              {profile.status === "confirmed"
                ? "Đã xác nhận"
                : "Chưa xác nhận xong"}
            </Badge>
          </div>

          {summary.length > 0 && (
            <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {summary.map((row) => (
                <div key={row.label}>
                  <dt className="text-xs text-slate-500">{row.label}</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-900">
                    {row.value}
                  </dd>
                </div>
              ))}
            </dl>
          )}

          <div className="mt-6 flex flex-wrap gap-3">
            <Button href="/tu-van" variant="outline">
              Xem lại kết quả đối chiếu
            </Button>
            {profile.status !== "confirmed" && (
              <Button href="/tu-van">Hoàn tất và xác nhận hồ sơ</Button>
            )}
          </div>
        </Card>
      )}

      <div>
        <h2 className="text-lg font-bold text-slate-900">
          Đơn bạn đã đăng ký
        </h2>
        {registrations.length === 0 ? (
          <Card className="mt-4 p-6">
            <p className="text-sm leading-6 text-slate-600">
              Bạn chưa đăng ký đơn nào. Vào phần đối chiếu để xem đơn phù hợp rồi
              chọn đơn muốn ứng tuyển.
            </p>
            <div className="mt-5">
              <Button href="/tu-van">Xem đơn phù hợp với bạn</Button>
            </div>
          </Card>
        ) : (
          <div className="mt-4 space-y-5">
            {registrations.map((item) => (
              <RegistrationCard key={item.application_code} item={item} />
            ))}
          </div>
        )}
      </div>

      <Card className="border-slate-200 bg-slate-50 p-5">
        <p className="text-xs leading-5 text-slate-500">
          Trang này nhận ra bạn bằng dữ liệu lưu trên chính trình duyệt này, không
          phải bằng đăng nhập. Đổi máy hoặc xóa dữ liệu duyệt thì hồ sơ không hiện
          ở đây; khi đó gọi {COMPANY.hotline} để nhân viên tra bằng số điện thoại
          của bạn.
        </p>
      </Card>
    </div>
  );
}
