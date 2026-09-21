"use client";

/**
 * Gửi CV để hệ thống điền hộ biểu mẫu.
 *
 * Đặt ở **đầu bước nhập hồ sơ**, không phải một bước riêng. Gửi CV là đường tắt
 * để đỡ phải gõ, chứ không phải một thủ tục bắt buộc — ai không có file vẫn khai
 * tay bình thường và không phải bấm qua một màn hình trống.
 *
 * Sau khi đọc xong, giao diện nói rõ **máy đọc được gì** và **không nhận gì, vì
 * sao**. Điền âm thầm vào biểu mẫu rồi im lặng là cách nhanh nhất để ứng viên
 * bấm "xem đơn phù hợp" mà không kiểm tra lại — trong khi cả hệ thống được xây
 * trên nguyên tắc ngược lại: máy đọc thì người phải xác nhận.
 */
import { useRef, useState } from "react";
import { Badge, Button, Card } from "@/components/ui/primitives";
import {
  ApiError,
  CandidateProfile,
  UploadResult,
  uploadDocument,
} from "@/lib/candidateApi";

const FIELD_LABELS: Record<string, string> = {
  full_name: "họ tên",
  birth_year: "năm sinh",
  gender: "giới tính",
  education_level: "bằng cấp",
  major: "chuyên ngành",
  japanese_level: "trình độ tiếng Nhật",
  experience_years: "số năm kinh nghiệm",
  care_experience: "kinh nghiệm chăm sóc",
  phone: "số điện thoại",
};

function label(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

export default function CvUpload({
  sessionId,
  onProfileRead,
}: {
  sessionId: string;
  onProfileRead: (profile: CandidateProfile) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const pick = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const payload = await uploadDocument(sessionId, file);
      setResult(payload);
      if (payload.profile) onProfileRead(payload.profile);
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Không gửi được file, bạn thử lại giúp em.",
      );
    } finally {
      setBusy(false);
      // Xoá lựa chọn cũ để chọn lại đúng file đó vẫn kích hoạt sự kiện.
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const accepted = result?.accepted_fields ?? [];
  const rejected = Object.entries(result?.rejected ?? {});

  return (
    <Card className="border-dashed border-slate-300 bg-slate-50/60 p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-ink-900">
            Có sẵn CV? Gửi lên để đỡ phải gõ
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Nhận file PDF, Word hoặc ảnh chụp. Hệ thống đọc rồi điền sẵn vào biểu
            mẫu bên dưới — bạn vẫn xem lại và sửa được trước khi đối chiếu.
          </p>
        </div>
        <div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.jpg,.jpeg,.png,.webp,.heic"
            className="hidden"
            onChange={(event) => pick(event.target.files?.[0])}
          />
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
          >
            {busy ? "Đang đọc file…" : "Chọn file CV"}
          </Button>
        </div>
      </div>

      {error && (
        <p className="mt-4 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-700">{result.message}</p>

          {accepted.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-500">Đã điền:</span>
              {accepted.map((key) => (
                <Badge key={key} tone="success">
                  {label(key)}
                </Badge>
              ))}
            </div>
          )}

          {rejected.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-slate-500">
                Có mục hệ thống đọc ra nhưng không dám nhận, bạn tự khai giúp em:
              </p>
              <ul className="mt-1.5 space-y-1 text-xs text-slate-600">
                {rejected.map(([key, reason]) => (
                  <li key={key}>
                    <span className="font-medium text-ink-900">{label(key)}</span> —{" "}
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="mt-3 text-xs leading-5 text-slate-500">
            Bạn xem lại các ô bên dưới giúp em nhé. Máy đọc có thể đọc sai, nên chỉ
            khi bạn xác nhận thì hệ thống mới đem hồ sơ đi đối chiếu.
          </p>
        </div>
      )}
    </Card>
  );
}
