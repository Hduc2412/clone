"use client";

import { ReactNode } from "react";
import { CatalogOption } from "@/lib/candidateApi";

/**
 * Ô nhập dùng chung cho biểu mẫu hồ sơ.
 *
 * Mọi ô đều **không bắt buộc trừ hai ô có đánh dấu**. Đây là quyết định nghiệp vụ
 * chứ không phải cẩu thả: bỏ trống cho ra "chưa rõ", mà chưa rõ thì không loại đơn
 * nào. Bắt điền hết chỉ khiến người dùng gõ bừa, và gõ bừa mới thật sự làm hỏng
 * kết quả đối chiếu.
 */

function Shell({
  label,
  hint,
  required,
  error,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-ink-800">
        {label}
        {required && <span className="ml-1 text-brand-600">*</span>}
      </span>
      {hint && <span className="mt-0.5 block text-xs text-slate-500">{hint}</span>}
      <div className="mt-1.5">{children}</div>
      {error && <span className="mt-1 block text-xs text-brand-600">{error}</span>}
    </label>
  );
}

const CONTROL =
  "w-full min-h-[44px] rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-ink-900 " +
  "placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100";

export function TextField({
  label,
  hint,
  required,
  error,
  value,
  onChange,
  placeholder,
  inputMode,
  maxLength,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  error?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  inputMode?: "text" | "numeric" | "tel";
  maxLength?: number;
}) {
  return (
    <Shell label={label} hint={hint} required={required} error={error}>
      <input
        type="text"
        className={CONTROL}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        inputMode={inputMode}
        maxLength={maxLength}
      />
    </Shell>
  );
}

export function SelectField({
  label,
  hint,
  required,
  error,
  value,
  onChange,
  options,
  emptyLabel = "Chưa rõ / chưa muốn khai",
}: {
  label: string;
  hint?: string;
  required?: boolean;
  error?: string;
  value: string;
  onChange: (value: string) => void;
  options: CatalogOption[];
  emptyLabel?: string;
}) {
  return (
    <Shell label={label} hint={hint} required={required} error={error}>
      <select
        className={CONTROL}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{emptyLabel}</option>
        {options.map((option) => (
          <option key={option.code} value={option.code}>
            {option.label}
          </option>
        ))}
      </select>
    </Shell>
  );
}

/**
 * Ba lựa chọn chứ không phải hộp đánh dấu hai trạng thái.
 *
 * Hộp đánh dấu không phân biệt được "đã hỏi và người ta trả lời không" với "chưa
 * hỏi". Bộ đối chiếu cần biết khác nhau: cái sau là chưa rõ và không được loại đơn.
 */
export function TriStateField({
  label,
  hint,
  value,
  onChange,
  yesLabel = "Có",
  noLabel = "Chưa có",
}: {
  label: string;
  hint?: string;
  value: boolean | undefined;
  onChange: (value: boolean | undefined) => void;
  yesLabel?: string;
  noLabel?: string;
}) {
  const choices: { key: string; label: string; next: boolean | undefined }[] = [
    { key: "yes", label: yesLabel, next: true },
    { key: "no", label: noLabel, next: false },
    { key: "unknown", label: "Chưa rõ", next: undefined },
  ];
  const current = value === true ? "yes" : value === false ? "no" : "unknown";

  return (
    <Shell label={label} hint={hint}>
      <div className="flex flex-wrap gap-2">
        {choices.map((choice) => (
          <button
            key={choice.key}
            type="button"
            onClick={() => onChange(choice.next)}
            aria-pressed={current === choice.key}
            className={`min-h-[44px] rounded-xl border px-4 text-sm transition-colors ${
              current === choice.key
                ? "border-brand-500 bg-brand-50 font-medium text-brand-700"
                : "border-slate-300 bg-white text-slate-600 hover:border-slate-400"
            }`}
          >
            {choice.label}
          </button>
        ))}
      </div>
    </Shell>
  );
}

export function NumberField({
  label,
  hint,
  error,
  value,
  onChange,
  placeholder,
  suffix,
}: {
  label: string;
  hint?: string;
  error?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  suffix?: string;
}) {
  return (
    <Shell label={label} hint={hint} error={error}>
      <div className="relative">
        <input
          type="text"
          inputMode="numeric"
          className={`${CONTROL} ${suffix ? "pr-14" : ""}`}
          value={value}
          onChange={(event) => onChange(event.target.value.replace(/[^\d]/g, ""))}
          placeholder={placeholder}
        />
        {suffix && (
          <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-sm text-slate-400">
            {suffix}
          </span>
        )}
      </div>
    </Shell>
  );
}
