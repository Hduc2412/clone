/**
 * Ánh xạ mười ba trạng thái nội bộ của hồ sơ đăng ký thành các chặng ứng viên
 * hiểu được.
 *
 * Để ở một chỗ vì **hai màn hình cùng dùng**: trang công khai `/ho-so-cua-toi`
 * (nhận diện bằng mã phiên, dành cho người vừa đăng ký chưa có tài khoản) và hệ
 * khách hàng `/tai-khoan` (sau đăng nhập). Chép tay hai bản là chắc chắn có ngày
 * một bên hiện "Đang xem xét" còn bên kia hiện "Đã đăng ký" cho cùng một hồ sơ.
 *
 * Bảng gốc của mười ba trạng thái nằm ở `docs/handoff/APPLICATION_LIFECYCLE_PROPOSAL.md`.
 */

export const STAGES = [
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

export type StageKey = (typeof STAGES)[number]["key"];

const STAGE_OF: Record<string, StageKey> = {
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

/**
 * Trạng thái đóng không nằm trên đường tiến, nên hiện riêng.
 *
 * Mỗi mục đều kèm bước tiếp theo: một hồ sơ "chưa đạt" mà không nói làm gì tiếp
 * thì tàn nhẫn hơn là hữu ích.
 */
export const CLOSED_STATES: Record<
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

/** Vị trí trên đường tiến, hoặc -1 khi trạng thái nằm ngoài đường đó. */
export function stageIndex(status: string): number {
  const key = STAGE_OF[status];
  return key ? STAGES.findIndex((stage) => stage.key === key) : -1;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
