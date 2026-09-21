"use client";

import { FormEvent, ReactNode, useState } from "react";
import {
  CandidateProfile,
  CandidateProfileMeta,
  CandidateProfilePatch,
  CatalogOption,
} from "@/lib/managementApi";

/**
 * Biểu mẫu nhân viên sửa hồ sơ ứng viên.
 *
 * Đây là chốt "quyết định cuối vẫn thuộc về người": máy đọc CV sai chính tả tên
 * riêng, nghe nhầm mức tiếng Nhật, hay ứng viên khai vội một con số — nhân viên
 * phải sửa được ngay trên màn hình đang xem, chứ không phải ghi ra giấy rồi nhờ
 * người khác vào cơ sở dữ liệu.
 *
 * Hai điều ràng buộc cách viết biểu mẫu này:
 *
 * - **Ô để trống nghĩa là giữ nguyên, không phải xóa.** Tầng gộp dữ liệu bỏ qua
 *   giá trị rỗng để một lần đọc CV thiếu trường không quét sạch thứ ứng viên đã
 *   tự khai. Hệ quả ở đây là không xóa trắng một ô được, nên phải nói thẳng ra
 *   thay vì để người dùng bấm lưu rồi tưởng đã xóa.
 * - **Gửi lại đúng giá trị đang có thì không có gì xảy ra.** Nhờ vậy bấm lưu mà
 *   chỉ sửa một ô sẽ không biến cả hồ sơ thành "nhân viên nhập" và làm mất dấu
 *   những dòng đọc từ CV kèm trích dẫn nguyên văn.
 */

const INPUT =
  "mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-red-400";

function text(form: FormData, name: string): string | null {
  const value = String(form.get(name) ?? "").trim();
  return value === "" ? null : value;
}

function whole(form: FormData, name: string): number | null {
  const raw = text(form, name);
  if (raw === null) return null;
  const parsed = Number(raw.replace(/[.,\s]/g, ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function decimal(form: FormData, name: string): number | null {
  const raw = text(form, name);
  if (raw === null) return null;
  const parsed = Number(raw.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

/** Ba trạng thái: có, không, và chưa hỏi. Hộp đánh dấu chỉ diễn tả được hai. */
function tristate(form: FormData, name: string): boolean | null {
  const raw = text(form, name);
  if (raw === null) return null;
  return raw === "co";
}

export function buildProfilePatch(
  form: FormData,
  expectedVersion: number,
): CandidateProfilePatch {
  return {
    fields: {
      full_name: text(form, "full_name"),
      birth_year: whole(form, "birth_year"),
      gender: text(form, "gender"),
      education_level: text(form, "education_level"),
      major: text(form, "major"),
      japanese_level: text(form, "japanese_level"),
      experience_years: decimal(form, "experience_years"),
      care_experience: tristate(form, "care_experience"),
      phone: text(form, "phone"),
    },
    preferences: {
      desired_prefecture: text(form, "desired_prefecture"),
      desired_region_group: text(form, "desired_region_group"),
      desired_employer_type: text(form, "desired_employer_type"),
      salary_expectation_jpy: whole(form, "salary_expectation_jpy"),
      budget_vnd: whole(form, "budget_vnd"),
      reason: text(form, "reason"),
      notes: text(form, "notes"),
    },
    expected_version: expectedVersion,
  };
}

/** Giá trị hiện tại của một ô, đưa thẳng vào `defaultValue` của thẻ nhập. */
function current(
  section: Record<string, { value: unknown }>,
  key: string,
): string {
  const value = section?.[key]?.value;
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "co" : "khong";
  return String(value);
}

export default function ProfileEditForm({
  profile,
  meta,
  onSubmit,
  onCancel,
  saving,
}: {
  profile: CandidateProfile;
  meta: CandidateProfileMeta;
  onSubmit: (patch: CandidateProfilePatch) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(buildProfilePatch(new FormData(event.currentTarget), profile.version));
  };

  const fields = profile.fields || {};
  const preferences = profile.preferences || {};

  // Vùng đi theo tỉnh chứ không đứng riêng. Để hai ô rời nhau thì đổi tỉnh mà
  // quên đổi vùng sẽ cho ra một hồ sơ tự mâu thuẫn — muốn Fukuoka nhưng vùng
  // ghi Kantō — và bộ xếp hạng sẽ cộng 25 điểm cho những đơn ở sai đầu nước
  // Nhật. Chọn tỉnh rồi thì ô vùng khóa lại và không gửi đi, để máy chủ tự suy.
  const [prefecture, setPrefecture] = useState(
    current(preferences, "desired_prefecture"),
  );
  const derivedRegion = meta.prefectures.find(
    (item) => item.code === prefecture,
  )?.region_group;
  const derivedRegionLabel = meta.regions.find(
    (item) => item.code === derivedRegion,
  )?.label;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <p className="rounded-xl bg-sky-50 px-4 py-3 text-xs leading-5 text-sky-800">
        Ô để trống nghĩa là <strong>giữ nguyên giá trị cũ</strong>, không phải xóa
        nó đi. Muốn bỏ một giá trị sai thì nhập đè giá trị đúng. Những ô không
        đụng tới vẫn giữ nguyên nguồn và đoạn trích từ CV.
      </p>

      <Section
        title="Năng lực"
        description="Những ô này quyết định ứng viên đạt hay không đạt điều kiện bắt buộc của từng đơn. Sửa sai một ô có thể loại oan, hoặc giới thiệu một đơn ứng viên không thể trúng."
        tone="hard"
      >
        <Field label="Họ và tên">
          <input
            name="full_name"
            maxLength={100}
            defaultValue={current(fields, "full_name")}
            className={INPUT}
          />
        </Field>
        <Field label="Năm sinh" hint="Dùng để tính tuổi tại ngày đối chiếu">
          <input
            name="birth_year"
            type="number"
            min={1950}
            max={2015}
            defaultValue={current(fields, "birth_year")}
            className={INPUT}
          />
        </Field>
        <Field label="Giới tính">
          <Select name="gender" options={meta.genders} value={current(fields, "gender")} />
        </Field>
        <Field label="Bằng cấp">
          <Select
            name="education_level"
            options={meta.education_levels}
            value={current(fields, "education_level")}
          />
        </Field>
        <Field label="Chuyên ngành">
          <input
            name="major"
            maxLength={100}
            defaultValue={current(fields, "major")}
            className={INPUT}
          />
        </Field>
        <Field
          label="Trình độ tiếng Nhật"
          hint="Tiêu chí loại nhiều hồ sơ nhất. “Chưa học” cũng là một câu trả lời hợp lệ."
        >
          <Select
            name="japanese_level"
            options={meta.japanese_levels}
            value={current(fields, "japanese_level")}
          />
        </Field>
        <Field label="Số năm kinh nghiệm">
          <input
            name="experience_years"
            type="number"
            min={0}
            max={50}
            step="0.5"
            defaultValue={current(fields, "experience_years")}
            className={INPUT}
          />
        </Field>
        <Field label="Kinh nghiệm chăm sóc">
          <Select
            name="care_experience"
            options={[
              { code: "co", label: "Có" },
              { code: "khong", label: "Không" },
            ]}
            value={current(fields, "care_experience")}
            placeholder="Chưa rõ"
          />
        </Field>
        <Field label="Số điện thoại" hint="Nhập dạng nào cũng được, hệ thống tự chuẩn hóa">
          <input
            name="phone"
            defaultValue={current(fields, "phone")}
            className={INPUT}
          />
        </Field>
      </Section>

      <Section
        title="Nguyện vọng"
        description="Chỉ tham gia xếp hạng, không bao giờ loại đơn. Nhập sai ở đây thì thứ tự gợi ý lệch đi, nhưng không ai bị mất đơn."
      >
        <Field label="Tỉnh mong muốn" hint="Nêu tỉnh là đủ, vùng tự suy ra">
          <select
            name="desired_prefecture"
            value={prefecture}
            onChange={(event) => setPrefecture(event.target.value)}
            className={INPUT}
          >
            <option value="">Giữ nguyên</option>
            {meta.prefectures.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Vùng mong muốn"
          hint={
            prefecture
              ? "Suy ra từ tỉnh đã chọn, không sửa riêng được"
              : "Dùng khi ứng viên chỉ nói được vùng, chưa chọn tỉnh nào"
          }
        >
          {prefecture ? (
            <input
              disabled
              value={derivedRegionLabel ?? "—"}
              className={`${INPUT} bg-slate-50 text-slate-500`}
            />
          ) : (
            <Select
              name="desired_region_group"
              options={meta.regions}
              value={current(preferences, "desired_region_group")}
            />
          )}
        </Field>
        <Field label="Loại cơ sở mong muốn">
          <Select
            name="desired_employer_type"
            options={meta.employer_types}
            value={current(preferences, "desired_employer_type")}
          />
        </Field>
        <Field label="Lương mong muốn (JPY/tháng)">
          <input
            name="salary_expectation_jpy"
            type="number"
            min={0}
            defaultValue={current(preferences, "salary_expectation_jpy")}
            className={INPUT}
          />
        </Field>
        <Field label="Ngân sách (VNĐ)">
          <input
            name="budget_vnd"
            type="number"
            min={0}
            defaultValue={current(preferences, "budget_vnd")}
            className={INPUT}
          />
        </Field>
        <Field label="Lý do tham gia" className="md:col-span-2 xl:col-span-3">
          <textarea
            name="reason"
            rows={2}
            maxLength={500}
            defaultValue={current(preferences, "reason")}
            className={INPUT}
          />
        </Field>
        <Field
          label="Ghi chú"
          className="md:col-span-2 xl:col-span-3"
          hint="Hoàn cảnh riêng ứng viên nói qua điện thoại mà biểu mẫu không có ô nào đựng"
        >
          <textarea
            name="notes"
            rows={3}
            maxLength={1000}
            defaultValue={current(preferences, "notes")}
            className={INPUT}
          />
        </Field>
      </Section>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded-xl bg-[#cb1d1e] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          {saving ? "Đang lưu…" : "Lưu thay đổi"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
        >
          Hủy
        </button>
        <span className="text-xs text-slate-400">
          Đang sửa trên phiên bản {profile.version}. Nếu người khác vừa lưu hồ sơ
          này thì hệ thống báo lỗi thay vì ghi đè phần họ sửa.
        </span>
      </div>
    </form>
  );
}

function Section({
  title,
  description,
  tone,
  children,
}: {
  title: string;
  description: string;
  tone?: "hard";
  children: ReactNode;
}) {
  return (
    <section
      className={`rounded-2xl border bg-white p-5 shadow-sm ${
        tone === "hard" ? "border-amber-300" : "border-slate-200"
      }`}
    >
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">{description}</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{children}</div>
    </section>
  );
}

function Field({
  label,
  hint,
  className,
  children,
}: {
  label: string;
  hint?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <label className={`block text-sm font-medium text-slate-600 ${className ?? ""}`}>
      {label}
      {children}
      {hint && <p className="mt-1 text-xs font-normal text-slate-400">{hint}</p>}
    </label>
  );
}

function Select({
  name,
  options,
  value,
  placeholder,
}: {
  name: string;
  options: CatalogOption[];
  value: string;
  placeholder?: string;
}) {
  return (
    <select name={name} defaultValue={value} className={INPUT}>
      <option value="">{placeholder ?? "Giữ nguyên"}</option>
      {options.map((option) => (
        <option key={option.code} value={option.code}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
