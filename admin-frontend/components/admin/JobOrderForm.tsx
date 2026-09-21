"use client";

import { FormEvent, ReactNode, useState } from "react";
import { CatalogOption, JobOrder, JobOrderMeta } from "@/lib/managementApi";

/**
 * Biểu mẫu đơn tuyển dụng, dùng chung cho tạo mới và sửa.
 *
 * Bố cục tách hai nhóm có chủ ý: **điều kiện bắt buộc** là những ô quyết định
 * ứng viên bị loại hay không, **thông tin tham khảo** chỉ để hiển thị và xếp
 * hạng. Nhân viên nhập liệu phải nhìn thấy ranh giới đó, vì nhập sai một ô ở
 * nhóm trên có thể loại oan cả một nhóm hồ sơ, còn nhóm dưới thì không.
 */

type Payload = Record<string, unknown>;

function text(value: FormDataEntryValue | null): string | null {
  const result = String(value ?? "").trim();
  return result === "" ? null : result;
}

function num(value: FormDataEntryValue | null): number | null {
  const raw = text(value);
  if (raw === null) return null;
  const parsed = Number(raw.replace(/[.,\s]/g, ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function decimal(value: FormDataEntryValue | null): number {
  const raw = text(value);
  if (raw === null) return 0;
  const parsed = Number(raw.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function list(value: FormDataEntryValue | null): string[] {
  const raw = text(value);
  if (raw === null) return [];
  return raw
    .split(/[;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function buildJobOrderPayload(form: FormData, includeStatus: boolean): Payload {
  const payload: Payload = {
    title: text(form.get("title")),
    employer_name: text(form.get("employer_name")),
    employer_type: text(form.get("employer_type")),
    program: text(form.get("program")),
    prefecture: text(form.get("prefecture")),
    city: text(form.get("city")),
    quota: num(form.get("quota")),
    deadline: text(form.get("deadline")),
    requirements: {
      japanese_required: text(form.get("japanese_required")),
      education_required: text(form.get("education_required")),
      experience_min: decimal(form.get("experience_min")),
      age_min: num(form.get("age_min")),
      age_max: num(form.get("age_max")),
      gender_pref: text(form.get("gender_pref")) || "khong_yeu_cau",
    },
    reference: {
      salary_min: num(form.get("salary_min")),
      salary_max: num(form.get("salary_max")),
      allowances: list(form.get("allowances")),
      cost_total_vnd: num(form.get("cost_total_vnd")),
      interview_date: text(form.get("interview_date")),
      departure_expected: text(form.get("departure_expected")),
      highlights: list(form.get("highlights")),
    },
    description: text(form.get("description")),
    internal_note: text(form.get("internal_note")),
  };
  if (includeStatus) {
    payload.status = text(form.get("status")) || "draft";
    payload.published = form.get("published") === "on";
  }
  return payload;
}

export default function JobOrderForm({
  meta,
  initial,
  mode,
  onSubmit,
  submitting,
}: {
  meta: JobOrderMeta;
  initial?: JobOrder;
  mode: "create" | "edit";
  onSubmit: (payload: Payload) => void;
  submitting: boolean;
}) {
  const [region, setRegion] = useState(initial?.region_group ?? "");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(buildJobOrderPayload(new FormData(event.currentTarget), mode === "create"));
  };

  const requirements = initial?.requirements;
  const reference = initial?.reference;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Section
        title="Nhận diện đơn hàng"
        description="Thông tin để nhân viên và ứng viên nhận ra đây là đơn nào."
      >
        <Field label="Tên đơn" required className="md:col-span-2">
          <input name="title" required defaultValue={initial?.title} className={INPUT} />
        </Field>
        <Field label="Cơ sở tiếp nhận" required>
          <input
            name="employer_name"
            required
            defaultValue={initial?.employer_name}
            className={INPUT}
          />
        </Field>
        <Field label="Loại hình cơ sở" required>
          <Select name="employer_type" options={meta.employer_types} value={initial?.employer_type} required />
        </Field>
        <Field label="Diện chương trình" required>
          <Select name="program" options={meta.programs} value={initial?.program} required />
        </Field>
        <Field label="Tỉnh tại Nhật Bản" required hint={region ? `Vùng: ${regionLabel(meta, region)}` : "Vùng tự suy ra từ tỉnh"}>
          <select
            name="prefecture"
            required
            defaultValue={initial?.prefecture ?? ""}
            onChange={(event) => {
              const found = meta.prefectures.find((item) => item.code === event.target.value);
              setRegion(found?.region_group ?? "");
            }}
            className={INPUT}
          >
            <option value="">Chọn tỉnh</option>
            {meta.prefectures.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Thành phố">
          <input name="city" defaultValue={initial?.city ?? ""} className={INPUT} />
        </Field>
        <Field label="Số lượng tuyển" required>
          <input
            name="quota"
            type="number"
            min={1}
            required
            defaultValue={initial?.quota ?? 1}
            className={INPUT}
          />
        </Field>
      </Section>

      <Section
        title="Điều kiện bắt buộc"
        description="Mỗi ô ở đây sinh ra đúng một dòng đạt hoặc không đạt khi hệ thống đối chiếu hồ sơ. Sai một ô có thể loại oan ứng viên đủ điều kiện."
        tone="hard"
      >
        <Field label="Tiếng Nhật tối thiểu" required>
          <Select
            name="japanese_required"
            options={meta.japanese_levels}
            value={requirements?.japanese_required}
            required
          />
        </Field>
        <Field label="Bằng cấp tối thiểu" hint="Để trống nếu không yêu cầu">
          <Select
            name="education_required"
            options={meta.education_levels}
            value={requirements?.education_required ?? ""}
            placeholder="Không yêu cầu"
          />
        </Field>
        <Field label="Kinh nghiệm tối thiểu (năm)">
          <input
            name="experience_min"
            type="number"
            min={0}
            step="0.5"
            defaultValue={requirements?.experience_min ?? 0}
            className={INPUT}
          />
        </Field>
        <Field label="Tuổi từ">
          <input
            name="age_min"
            type="number"
            min={16}
            max={70}
            defaultValue={requirements?.age_min ?? ""}
            className={INPUT}
          />
        </Field>
        <Field label="Tuổi đến">
          <input
            name="age_max"
            type="number"
            min={16}
            max={70}
            defaultValue={requirements?.age_max ?? ""}
            className={INPUT}
          />
        </Field>
        <Field label="Yêu cầu giới tính">
          <Select
            name="gender_pref"
            options={meta.gender_prefs}
            value={requirements?.gender_pref ?? "khong_yeu_cau"}
          />
        </Field>
        <Field label="Hạn nộp hồ sơ" required hint="Quá hạn thì đơn tự rời khỏi website">
          <input
            name="deadline"
            type="date"
            required
            defaultValue={initial?.deadline}
            className={INPUT}
          />
        </Field>
      </Section>

      <Section
        title="Thông tin tham khảo"
        description="Dùng để hiển thị và xếp hạng theo nguyện vọng. Không bao giờ dùng để loại ứng viên."
      >
        <Field label="Lương từ (JPY/tháng)">
          <input name="salary_min" type="number" min={0} defaultValue={reference?.salary_min ?? ""} className={INPUT} />
        </Field>
        <Field label="Lương đến (JPY/tháng)">
          <input name="salary_max" type="number" min={0} defaultValue={reference?.salary_max ?? ""} className={INPUT} />
        </Field>
        <Field label="Tổng chi phí ước tính (VND)">
          <input
            name="cost_total_vnd"
            type="number"
            min={0}
            defaultValue={reference?.cost_total_vnd ?? ""}
            className={INPUT}
          />
        </Field>
        <Field label="Ngày phỏng vấn dự kiến">
          <input
            name="interview_date"
            type="date"
            defaultValue={reference?.interview_date ?? ""}
            className={INPUT}
          />
        </Field>
        <Field label="Dự kiến xuất cảnh" hint="Ví dụ 2027-03">
          <input
            name="departure_expected"
            defaultValue={reference?.departure_expected ?? ""}
            className={INPUT}
          />
        </Field>
        <Field label="Phụ cấp" hint="Mỗi mục một dòng" className="md:col-span-2">
          <textarea
            name="allowances"
            rows={3}
            defaultValue={(reference?.allowances ?? []).join("\n")}
            className={INPUT}
          />
        </Field>
        <Field label="Điểm nổi bật" hint="Mỗi mục một dòng" className="md:col-span-2">
          <textarea
            name="highlights"
            rows={3}
            defaultValue={(reference?.highlights ?? []).join("\n")}
            className={INPUT}
          />
        </Field>
        <Field label="Mô tả công việc" className="md:col-span-3">
          <textarea
            name="description"
            rows={4}
            defaultValue={initial?.description ?? ""}
            className={INPUT}
          />
        </Field>
      </Section>

      <Section
        title="Nội bộ"
        description="Phần này không bao giờ hiển thị cho khách, kể cả trên trang chi tiết đơn hàng."
      >
        <Field label="Ghi chú nội bộ" className="md:col-span-3">
          <textarea
            name="internal_note"
            rows={3}
            defaultValue={initial?.internal_note ?? ""}
            className={INPUT}
          />
        </Field>
        {mode === "create" && (
          <>
            <Field label="Trạng thái khi tạo" hint="Các trạng thái khác đổi sau, để lưu được lịch sử">
              <select name="status" defaultValue="draft" className={INPUT}>
                <option value="draft">Nháp</option>
                <option value="open">Đang tuyển</option>
              </select>
            </Field>
            <Field label="Công khai trên website">
              <label className="mt-2 flex items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" name="published" />
                Hiện đơn này cho khách
              </label>
            </Field>
          </>
        )}
      </Section>

      <div className="flex justify-end gap-3">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-xl bg-[#cb1d1e] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {submitting ? "Đang lưu..." : mode === "create" ? "Tạo đơn tuyển dụng" : "Lưu thay đổi"}
        </button>
      </div>
    </form>
  );
}

const INPUT =
  "mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-red-400";

function regionLabel(meta: JobOrderMeta, code: string): string {
  return meta.regions.find((item) => item.code === code)?.label ?? code;
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
  required,
  className,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <label className={`block text-sm font-medium text-slate-600 ${className ?? ""}`}>
      {label}
      {required && <span className="ml-1 text-[#cb1d1e]">*</span>}
      {children}
      {hint && <p className="mt-1 text-xs font-normal text-slate-400">{hint}</p>}
    </label>
  );
}

function Select({
  name,
  options,
  value,
  required,
  placeholder,
}: {
  name: string;
  options: CatalogOption[];
  value?: string | null;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <select name={name} required={required} defaultValue={value ?? ""} className={INPUT}>
      <option value="">{placeholder ?? "Chọn"}</option>
      {options.map((option) => (
        <option key={option.code} value={option.code}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
