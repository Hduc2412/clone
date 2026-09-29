"use client";

/**
 * Danh mục khóa học tiếng Nhật.
 *
 * Trước màn hình này, thêm một khóa nghĩa là sửa một file Python rồi chạy lệnh
 * trên máy chủ. Với một bảng mà **nhân viên trung tâm là người biết nội dung**, đó
 * là rào cản đặt sai chỗ: người biết thì không sửa được, người sửa được thì không
 * biết.
 *
 * ## Vì sao biểu mẫu đòi nguồn
 *
 * Mỗi ô số ở đây là một lời hứa với người đang tính chuyện vay tiền đi nước ngoài.
 * Một con số sai về học phí không phải lỗi hiển thị. Nên `source_url` hiện ngay
 * cạnh các ô tiền, và ô nào không có nguồn thì **để trống** — phần tư vấn đã biết
 * cách nói định tính khi thiếu số, còn một con số phỏng đoán thì không ai gỡ được.
 *
 * ## Vì sao nháp là mặc định
 *
 * Khóa đang khai dở mà lọt vào lộ trình thì ứng viên nhận một con đường học không
 * có giá tiền — tệ hơn là không nhận gì, vì họ tưởng mình đã biết đủ để quyết
 * định. Khai xong, đọc lại, rồi mới chuyển sang áp dụng.
 */

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorBanner, PageHeader } from "@/components/admin/AdminUI";
import { loadCurrentUser } from "@/lib/auth";
import { Course, CourseMeta, managementApi } from "@/lib/managementApi";

const TRONG: Omit<Course, "updated_at"> = {
  code: "",
  title: "",
  level_from: "chua_hoc",
  level_to: "N4",
  months_min: 6,
  months_max: null,
  tuition_vnd: null,
  package_total_vnd: null,
  format: null,
  curriculum: null,
  status: "draft",
  source_url: null,
  source_note: null,
};

function tien(gia_tri: number | null): string {
  if (gia_tri === null) return "chưa có";
  return `${gia_tri.toLocaleString("vi-VN")}đ`;
}

function thang(khoa: Course): string {
  if (khoa.months_max && khoa.months_max !== khoa.months_min) {
    return `${khoa.months_min}–${khoa.months_max} tháng`;
  }
  return `${khoa.months_min} tháng`;
}

/**
 * Lấy đúng phần thân của một khóa, bỏ `code` và `updated_at`.
 *
 * Viết ra từng ô thay vì destructuring-rồi-bỏ-biến: cách kia gọn hơn nhưng luật
 * lint từ chối biến không dùng, và quan trọng hơn là nó **âm thầm gửi thêm ô mới**
 * nếu sau này bảng có thêm trường. Máy chủ khai `extra="forbid"` nên lúc ấy sẽ 422,
 * mà thông báo lỗi chẳng gợi ý gì về nguyên nhân.
 */
function thanPayload(khoa: Course): Omit<Course, "code" | "updated_at"> {
  return {
    title: khoa.title,
    level_from: khoa.level_from,
    level_to: khoa.level_to,
    months_min: khoa.months_min,
    months_max: khoa.months_max,
    tuition_vnd: khoa.tuition_vnd,
    package_total_vnd: khoa.package_total_vnd,
    format: khoa.format,
    curriculum: khoa.curriculum,
    status: khoa.status,
    source_url: khoa.source_url,
    source_note: khoa.source_note,
  };
}

/** Ô số: chuỗi rỗng thành `null`, không thành 0. Hai thứ khác nhau hẳn. */
function doSo(gia_tri: string): number | null {
  const sach = gia_tri.trim();
  if (!sach) return null;
  const so = Number(sach.replace(/[^\d]/g, ""));
  return Number.isFinite(so) ? so : null;
}

export default function CoursesPage() {
  const [items, setItems] = useState<Course[]>([]);
  const [meta, setMeta] = useState<CourseMeta | null>(null);
  const [form, setForm] = useState<Omit<Course, "updated_at"> | null>(null);
  const [suaCode, setSuaCode] = useState<string | null>(null);
  const [quanLy, setQuanLy] = useState(false);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState("");
  const [nhan, setNhan] = useState("");

  const tai = useCallback(() => {
    setDangTai(true);
    setLoi("");
    managementApi
      .courses()
      .then((payload) => setItems(payload.items))
      .catch((ly_do) => setLoi(ly_do.message))
      .finally(() => setDangTai(false));
  }, []);

  useEffect(tai, [tai]);

  useEffect(() => {
    managementApi.courseMeta().then(setMeta).catch(() => undefined);
    loadCurrentUser()
      .then((user) => setQuanLy(user.role === "admin" || user.role === "manager"))
      .catch(() => undefined);
  }, []);

  const moTaoMoi = () => {
    // Mã khóa gợi ý theo số lớn nhất đang có +1. Chỉ là gợi ý — máy chủ vẫn chặn
    // trùng mã bằng index, nên hai người mở cùng lúc thì người sau nhận 409 thay
    // vì ghi đè lặng lẽ.
    const so = items
      .map((k) => Number(k.code.replace(/\D/g, "")))
      .filter((n) => Number.isFinite(n));
    const ke_tiep = (so.length ? Math.max(...so) : 0) + 1;
    setSuaCode(null);
    setForm({ ...TRONG, code: `KH-${String(ke_tiep).padStart(4, "0")}` });
  };

  const moSua = (khoa: Course) => {
    setSuaCode(khoa.code);
    setForm({ ...khoa });
  };

  const luu = async () => {
    if (!form) return;
    setLoi("");
    setNhan("");
    try {
      if (suaCode) {
        await managementApi.updateCourse(suaCode, thanPayload(form as Course));
        setNhan(`Đã lưu ${suaCode}.`);
      } else {
        await managementApi.createCourse(form);
        setNhan(`Đã thêm ${form.code}.`);
      }
      setForm(null);
      setSuaCode(null);
      tai();
    } catch (ly_do) {
      // Thông báo của máy chủ nói rõ sai ở đâu ("khóa phải nâng trình độ lên…"),
      // nên hiện nguyên văn thay vì viết lại một câu chung chung.
      setLoi((ly_do as Error).message);
    }
  };

  const xoa = async (khoa: Course) => {
    setLoi("");
    setNhan("");
    try {
      await managementApi.deleteCourse(khoa.code);
      setNhan(`Đã xóa ${khoa.code}.`);
      tai();
    } catch (ly_do) {
      setLoi((ly_do as Error).message);
    }
  };

  const doiTrangThai = async (khoa: Course) => {
    setLoi("");
    try {
      await managementApi.updateCourse(khoa.code, {
        ...thanPayload(khoa),
        status: khoa.status === "published" ? "draft" : "published",
      });
      tai();
    } catch (ly_do) {
      setLoi((ly_do as Error).message);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Tư vấn học"
        title="Khóa học tiếng Nhật"
        description="Bảng này là nguồn duy nhất cho lộ trình học mà hệ thống tư vấn cho ứng viên chưa đủ trình độ. Mỗi ô số phải truy được về nguồn; ô nào chưa có nguồn thì để trống."
        action={
          quanLy ? (
            <button
              onClick={() => (form ? setForm(null) : moTaoMoi())}
              className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white"
            >
              {form ? "Đóng biểu mẫu" : "Thêm khóa"}
            </button>
          ) : undefined
        }
      />

      {loi && <ErrorBanner message={loi} />}
      {nhan && (
        <p className="mb-4 rounded-xl bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800 ring-1 ring-emerald-200">
          {nhan}
        </p>
      )}

      {form && meta && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            luu();
          }}
          className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <h2 className="text-base font-bold text-slate-900">
            {suaCode ? `Sửa khóa ${suaCode}` : "Thêm khóa mới"}
          </h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {!suaCode && (
              <O label="Mã khóa">
                <input
                  required
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  placeholder="KH-0002"
                  className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-red-400"
                />
              </O>
            )}

            <O label="Tên khóa" rong>
              <input
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Học tiếng Nhật tại trung tâm"
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-red-400"
              />
            </O>

            <O label="Nhận người ở trình độ">
              <select
                value={form.level_from}
                onChange={(e) => setForm({ ...form, level_from: e.target.value })}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              >
                {meta.levels.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </O>

            <O label="Dạy tới trình độ">
              <select
                value={form.level_to}
                onChange={(e) => setForm({ ...form, level_to: e.target.value })}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              >
                {meta.levels.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </O>

            <O label="Số tháng tối thiểu">
              <input
                required
                type="number"
                min={1}
                max={60}
                value={form.months_min}
                onChange={(e) =>
                  setForm({ ...form, months_min: Number(e.target.value) || 1 })
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              />
            </O>

            <O label="Số tháng tối đa" ghi_chu="Để trống nếu đúng một con số">
              <input
                type="number"
                min={1}
                max={60}
                value={form.months_max ?? ""}
                onChange={(e) =>
                  setForm({ ...form, months_max: doSo(e.target.value) })
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              />
            </O>

            <O label="Học phí (đồng)" ghi_chu="Chưa có nguồn thì để trống">
              <input
                value={form.tuition_vnd ?? ""}
                onChange={(e) =>
                  setForm({ ...form, tuition_vnd: doSo(e.target.value) })
                }
                placeholder="35000000"
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              />
            </O>

            <O
              label="Tổng chi phí chương trình (đồng)"
              ghi_chu="Học phí là một chặng của tổng này"
            >
              <input
                value={form.package_total_vnd ?? ""}
                onChange={(e) =>
                  setForm({ ...form, package_total_vnd: doSo(e.target.value) })
                }
                placeholder="90000000"
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              />
            </O>

            <O label="Trạng thái" ghi_chu="Nháp thì không lọt ra phần tư vấn">
              <select
                value={form.status}
                onChange={(e) =>
                  setForm({ ...form, status: e.target.value as Course["status"] })
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              >
                {meta.statuses.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </O>

            <O label="Đường dẫn nguồn" rong>
              <input
                value={form.source_url ?? ""}
                onChange={(e) =>
                  setForm({ ...form, source_url: e.target.value || null })
                }
                placeholder="https://xklddieuduong.vn/?product=..."
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
              />
            </O>
          </div>

          <O label="Hình thức học" rong>
            <textarea
              rows={2}
              value={form.format ?? ""}
              onChange={(e) => setForm({ ...form, format: e.target.value || null })}
              placeholder="Học tập trung tại trung tâm, sáng và chiều. Có ký túc xá."
              className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
            />
          </O>

          <O label="Giáo trình" rong>
            <input
              value={form.curriculum ?? ""}
              onChange={(e) =>
                setForm({ ...form, curriculum: e.target.value || null })
              }
              placeholder="Minna no Nihongo Sơ cấp, hết 50 bài"
              className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
            />
          </O>

          <O
            label="Ghi chú nguồn"
            rong
            ghi_chu="Ô nào lấy từ đâu. Con số không có nguồn thì sau này không ai kiểm được."
          >
            <textarea
              rows={2}
              value={form.source_note ?? ""}
              onChange={(e) =>
                setForm({ ...form, source_note: e.target.value || null })
              }
              className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none"
            />
          </O>

          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white"
            >
              Lưu
            </button>
            <button
              type="button"
              onClick={() => {
                setForm(null);
                setSuaCode(null);
              }}
              className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600"
            >
              Hủy
            </button>
          </div>
        </form>
      )}

      {dangTai && <p className="text-sm text-slate-500">Đang tải…</p>}

      {!dangTai && items.length === 0 && (
        <EmptyState
          title="Chưa có khóa học nào"
          description="Không có khóa thì ứng viên chưa đủ trình độ chỉ nhận được câu nói định tính, không có số tháng và học phí."
        />
      )}

      <div className="space-y-3">
        {items.map((khoa) => (
          <article
            key={khoa.code}
            className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-slate-500">{khoa.code}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${
                      khoa.status === "published"
                        ? "bg-emerald-50 text-emerald-800 ring-emerald-200"
                        : "bg-slate-50 text-slate-600 ring-slate-200"
                    }`}
                  >
                    {khoa.status === "published" ? "Đang áp dụng" : "Nháp"}
                  </span>
                </div>
                <h3 className="mt-1.5 text-base font-bold text-slate-900">
                  {khoa.title}
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  {khoa.level_from === "chua_hoc" ? "Chưa học" : khoa.level_from} →{" "}
                  <b>{khoa.level_to}</b> · {thang(khoa)} · học phí{" "}
                  {tien(khoa.tuition_vnd)}
                  {khoa.package_total_vnd !== null && (
                    <span className="text-slate-500">
                      {" "}
                      (một chặng trong tổng {tien(khoa.package_total_vnd)})
                    </span>
                  )}
                </p>
                {khoa.tuition_vnd === null && (
                  <p className="mt-1 text-xs text-amber-700">
                    Chưa có học phí — phần tư vấn sẽ nói định tính, không nêu con số.
                  </p>
                )}
                {khoa.source_url && (
                  <a
                    href={khoa.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-block text-xs text-[#cb1d1e] hover:underline"
                  >
                    Nguồn →
                  </a>
                )}
              </div>

              {quanLy && (
                <div className="flex shrink-0 flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => doiTrangThai(khoa)}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {khoa.status === "published" ? "Chuyển về nháp" : "Đưa vào áp dụng"}
                  </button>
                  <button
                    type="button"
                    onClick={() => moSua(khoa)}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Sửa
                  </button>
                  {khoa.status === "draft" && (
                    <button
                      type="button"
                      onClick={() => xoa(khoa)}
                      className="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-50"
                    >
                      Xóa
                    </button>
                  )}
                </div>
              )}
            </div>

            {khoa.format && (
              <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-700">
                {khoa.format}
              </p>
            )}
            {khoa.source_note && (
              <p className="mt-2 text-xs leading-5 text-slate-500">
                <b>Nguồn từng ô:</b> {khoa.source_note}
              </p>
            )}
          </article>
        ))}
      </div>
    </>
  );
}

function O({
  label,
  children,
  ghi_chu,
  rong = false,
}: {
  label: string;
  children: React.ReactNode;
  ghi_chu?: string;
  rong?: boolean;
}) {
  return (
    <label
      className={`mt-4 block text-sm font-medium text-slate-600 sm:mt-0 ${
        rong ? "sm:col-span-2 lg:col-span-3" : ""
      }`}
    >
      {label}
      <div className="mt-2">{children}</div>
      {ghi_chu && <p className="mt-1 text-xs font-normal text-slate-400">{ghi_chu}</p>}
    </label>
  );
}
