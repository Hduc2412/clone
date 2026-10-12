"use client";

/**
 * Hai việc trên hồ sơ ứng viên mà API đã có từ 08/10 nhưng chưa màn hình nào làm (12/10).
 *
 * 1. **Đề xuất của khách chờ nhân viên.** Ô nhân viên đã xác minh có căn cứ thì khách không
 *    sửa thẳng được; khách sửa thành một đề xuất. Nhân viên chọn:
 *    - "Giữ giá trị nhân viên" — phải ghi lý do; đóng đề xuất, không đổi gì.
 *    - "Sửa theo khách" — mở biểu mẫu sửa; lưu xong máy chủ tự đóng đề xuất.
 * 2. **Tiến độ học tiếng Nhật.** Đang học / tạm dừng / đã hoàn thành. Hoàn thành chỉ ghi
 *    "Hoàn thành chương trình … — chưa xác minh chứng chỉ"; **không** đổi trình độ dùng để
 *    đối chiếu (quyết định 08/10). Trình độ đối chiếu chỉ đổi qua kết quả sơ tuyển có căn cứ.
 */
import { FormEvent, useState } from "react";
import type { CandidateProfile, CandidateProfileMeta, HocTap, ProfileConflict } from "@/lib/managementApi";
import { managementApi } from "@/lib/managementApi";

export const DE_XUAT = "khac_gia_tri_nhan_vien";
export const CHO = "cho_nhan_vien";
export const KHACH_DA_SUA = "khach_sua_o_nhan_vien_nhap";

export function deXuatDangCho(p: CandidateProfile): ProfileConflict[] {
  return (p.consultation_profile?.conflicts ?? []).filter((c) => c.kind === DE_XUAT && c.trang_thai === CHO);
}

export function khachDaSua(p: CandidateProfile): ProfileConflict[] {
  return (p.consultation_profile?.conflicts ?? []).filter((c) => c.kind === KHACH_DA_SUA);
}

function giaTri(v: unknown): string {
  if (v === null || v === undefined || v === "") return "(trống)";
  return String(v);
}

const NHAN_TRANG_THAI: Record<HocTap["trang_thai"], string> = {
  dang_hoc: "Đang học",
  tam_dung: "Tạm dừng",
  da_hoan_thanh: "Đã hoàn thành chương trình",
};

export default function DeXuatVaHocTap({
  profile,
  meta,
  nhanTruong,
  onDaDoi,
  onSuaTheoKhach,
}: {
  profile: CandidateProfile;
  meta: CandidateProfileMeta | null;
  nhanTruong: Record<string, string>;
  onDaDoi: (moi: CandidateProfile, thongBao: string) => void;
  onSuaTheoKhach: () => void;
}) {
  const [loi, setLoi] = useState("");
  const [dangGui, setDangGui] = useState(false);
  const [lyDo, setLyDo] = useState<Record<string, string>>({});
  const hoc = profile.hoc_tap;
  const [trangThai, setTrangThai] = useState<HocTap["trang_thai"]>(hoc?.trang_thai ?? "dang_hoc");
  const [mucTieu, setMucTieu] = useState(hoc?.muc_tieu ?? "N4");
  const [khoa, setKhoa] = useState(hoc?.khoa_code ?? "");
  const [ketQua, setKetQua] = useState(hoc?.ket_qua ?? "N4");

  const cho = deXuatDangCho(profile);
  const daSua = khachDaSua(profile);
  const tn = profile.trang_thai_tieng_nhat;
  const muc = (meta?.japanese_levels ?? []).filter((m) => m.code !== "chua_hoc");

  const giuNguyen = async (field: string) => {
    const ly = (lyDo[field] ?? "").trim();
    if (ly.length < 3) {
      setLoi("Ghi lý do giữ giá trị (ít nhất 3 ký tự) — để sau này biết vì sao không theo lời khách.");
      return;
    }
    setDangGui(true);
    setLoi("");
    try {
      onDaDoi(await managementApi.giuNguyenDeXuat(profile.code, field, ly), "Đã giữ giá trị nhân viên và đóng đề xuất.");
    } catch (r) {
      setLoi(r instanceof Error ? r.message : "Không đóng được đề xuất.");
    } finally {
      setDangGui(false);
    }
  };

  const ghiHoc = async (e: FormEvent) => {
    e.preventDefault();
    setDangGui(true);
    setLoi("");
    try {
      const moi = await managementApi.ghiHocTap(profile.code, {
        trang_thai: trangThai,
        muc_tieu: mucTieu,
        khoa_code: khoa.trim() || null,
        ket_qua: trangThai === "da_hoan_thanh" ? ketQua : null,
        expected_version: profile.version,
      });
      onDaDoi(moi, "Đã ghi tiến độ học. Trình độ dùng để đối chiếu không đổi.");
    } catch (r) {
      setLoi(r instanceof Error ? r.message : "Không ghi được tiến độ học.");
    } finally {
      setDangGui(false);
    }
  };

  return (
    <>
      {loi && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{loi}</p>}

      {(cho.length > 0 || daSua.length > 0) && (
        <section className="rounded-2xl border border-amber-200 bg-white p-4 shadow-sm" aria-labelledby="de-xuat-khach">
          <h3 id="de-xuat-khach" className="text-sm font-semibold text-slate-800">Khách đề xuất sửa — chờ bạn xem</h3>
          <p className="mt-1 text-xs text-slate-500">
            Ô bạn đã xác minh có căn cứ thì khách không sửa thẳng được; điều khách sửa nằm ở đây cho tới khi bạn quyết.
          </p>
          <ul className="mt-3 space-y-3">
            {cho.map((c) => (
              <li key={`${c.field}-${String(c.suggested)}`} className="rounded-xl bg-amber-50 p-3 text-sm">
                <p className="font-medium text-slate-900">{nhanTruong[c.field] || c.field}</p>
                <p className="mt-1 text-slate-700">
                  Nhân viên đã ghi: <strong>{giaTri(c.previous)}</strong> · Khách nói: <strong>{giaTri(c.suggested)}</strong>
                </p>
                {/* Khối nằm ở cột hẹp bên phải: ô lý do một dòng riêng, nút xuống dưới —
                    xếp ngang thì ô lý do bị ép còn vài chữ (kiểm trình duyệt 12/10). */}
                <div className="mt-2 space-y-2">
                  <input
                    aria-label={`Lý do giữ giá trị ${nhanTruong[c.field] || c.field}`}
                    value={lyDo[c.field] ?? ""}
                    onChange={(e) => setLyDo((d) => ({ ...d, [c.field]: e.target.value }))}
                    placeholder="Lý do giữ (vd: đã đối chứng bằng gốc)"
                    maxLength={300}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-400"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={dangGui}
                      onClick={() => giuNguyen(c.field)}
                      className="rounded-md border border-[#bbc7bd] bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-reu-50 disabled:opacity-50"
                    >
                      Giữ giá trị nhân viên
                    </button>
                    <button
                      type="button"
                      onClick={onSuaTheoKhach}
                      className="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
                    >
                      Sửa theo khách
                    </button>
                  </div>
                </div>
              </li>
            ))}
            {daSua.map((c) => (
              <li key={`da-${c.field}-${c.recorded_at}`} className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
                Khách đã sửa <strong>{nhanTruong[c.field] || c.field}</strong> (ô nhân viên nhập chưa xác minh): {giaTri(c.previous)} →{" "}
                {giaTri(c.suggested)} — đã áp dụng, chỉ để bạn biết.
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" aria-labelledby="tien-do-hoc">
        <h3 id="tien-do-hoc" className="text-sm font-semibold text-slate-800">Tiến độ học tiếng Nhật</h3>
        <p className="mt-2 text-sm text-slate-900">{tn?.nhan || "Chưa có trình độ tiếng Nhật"}</p>
        {tn?.dang_hoc && <p className="mt-1 text-xs text-slate-600">{tn.dang_hoc.nhan}</p>}
        {tn?.chuong_trinh && <p className="mt-1 text-xs text-slate-600">{tn.chuong_trinh.nhan}</p>}
        {hoc && <p className="mt-1 text-xs text-slate-500">Đang ghi: {NHAN_TRANG_THAI[hoc.trang_thai]}</p>}

        <form onSubmit={ghiHoc} className="mt-4 space-y-3 text-sm">
          <label className="block text-xs font-medium text-slate-600">
            Trạng thái
            <select value={trangThai} onChange={(e) => setTrangThai(e.target.value as HocTap["trang_thai"])}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-brand-400">
              {Object.entries(NHAN_TRANG_THAI).map(([ma, nhan]) => <option key={ma} value={ma}>{nhan}</option>)}
            </select>
          </label>
          <label className="block text-xs font-medium text-slate-600">
            Học hướng tới
            <select value={mucTieu} onChange={(e) => setMucTieu(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-brand-400">
              {muc.map((m) => <option key={m.code} value={m.code}>{m.label}</option>)}
            </select>
          </label>
          <label className="block text-xs font-medium text-slate-600">
            Mã khóa (nếu có)
            <input value={khoa} onChange={(e) => setKhoa(e.target.value)} maxLength={20} placeholder="KH-0001"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-brand-400" />
          </label>
          {trangThai === "da_hoan_thanh" && (
            <label className="block text-xs font-medium text-slate-600">
              Kết quả chương trình
              <select value={ketQua} onChange={(e) => setKetQua(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-brand-400">
                {muc.map((m) => <option key={m.code} value={m.code}>{m.label}</option>)}
              </select>
              <span className="mt-1 block font-normal text-amber-800">
                Ghi là &quot;Hoàn thành chương trình — chưa xác minh chứng chỉ&quot;. Trình độ dùng để đối chiếu đơn KHÔNG đổi;
                muốn đổi thì ghi kết quả sơ tuyển có căn cứ (bản gốc / tra cứu).
              </span>
            </label>
          )}
          <button type="submit" disabled={dangGui}
            className="w-full rounded-md bg-ink-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {dangGui ? "Đang ghi…" : "Ghi tiến độ học"}
          </button>
        </form>
      </section>
    </>
  );
}
