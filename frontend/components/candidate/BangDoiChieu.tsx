/**
 * Bảng đối chiếu hồ sơ với MỘT đơn — trọng tâm của phần tư vấn (yêu cầu 08/10).
 *
 * ## Chỉ dấu ✓, nhưng chỉ ở phần nhìn thấy
 *
 * Cột cuối hẹp, chỉ có ✓ khi tiêu chí đạt; không đạt hay chưa rõ đều để trống. Lý
 * do: người ít dùng công nghệ đọc một cột ✓ nhanh hơn một cột ba màu ba chữ, và một
 * dấu ✗ đỏ cạnh "chưa cung cấp" đọc thành "bị loại" trong khi thật ra chỉ là chưa khai.
 *
 * Nhưng ô trống với trình đọc màn hình là "không có gì". Nên mỗi ô có chữ ẩn —
 * "Đáp ứng" hoặc "Chưa đáp ứng hoặc chưa rõ" — và phần tổng kết bên dưới **vẫn tách
 * rõ** không đạt với thiếu thông tin. Màu và ký hiệu không bao giờ là phương tiện
 * duy nhất mang kết quả: số đếm và danh sách bên dưới nói bằng chữ.
 *
 * Backend vẫn trả đủ ba trạng thái (`DAT`, `KHONG_DAT`, `CHUA_RO`); chỉ cách hiện là
 * gọn lại. Không có chỗ nào ở đây gộp trạng thái nghiệp vụ.
 *
 * ## Điện thoại: thẻ theo tiêu chí, không kéo ngang
 *
 * Bốn cột trên màn hình hẹp buộc khách cuộn ngang và mất dòng đang so. Dưới mốc `sm`
 * mỗi tiêu chí thành một thẻ — cùng dữ liệu, cùng quy tắc ✓.
 */
import type { CriterionRow, SoftRow } from "@/lib/candidateApi";

export const CHU_THICH =
  "✓: đáp ứng theo thông tin hiện có. Ô trống: chưa đáp ứng hoặc cần bổ sung; xem giải thích bên dưới.";
const CHU_AN_DAT = "Đáp ứng";
const CHU_AN_KHONG = "Chưa đáp ứng hoặc chưa rõ";
export const CHUA_CUNG_CAP = "Chưa cung cấp";

/** Khách chưa khai trường này thì nói rõ là chưa cung cấp — không để ô trống như mất dữ liệu. */
export function thongTinKhach(row: CriterionRow): string {
  if (row.missing_field || !row.candidate_text?.trim()) return CHUA_CUNG_CAP;
  return row.candidate_text;
}

function DauTich({ dat }: { dat: boolean }) {
  return dat ? (
    <>
      <span aria-hidden className="text-base font-semibold text-emerald-700">
        ✓
      </span>
      <span className="sr-only">{CHU_AN_DAT}</span>
    </>
  ) : (
    <span className="sr-only">{CHU_AN_KHONG}</span>
  );
}

export const KHACH_CHUA_NEU = "khach_chua_neu";
export const DON_CHUA_CONG_BO = "don_chua_cong_bo";

/**
 * Vì sao một dòng nguyện vọng chưa đánh giá được (08/10).
 *
 * "Khách chưa nêu ngân sách" và "đơn chưa công bố chi phí" là hai chuyện khác nhau —
 * trước đây cả hai cùng hiện "(chưa rõ nguyện vọng)". Máy chủ gửi `unknown_reasons`;
 * nhật ký cũ chưa có thì suy từ chính dòng ấy, không sửa dữ liệu lịch sử.
 */
export function lyDoChuaRo(r: SoftRow): string[] {
  if (r.outcome !== "unknown") return [];
  if (r.unknown_reasons) return r.unknown_reasons;
  const ra: string[] = [];
  if (r.missing_field) ra.push(KHACH_CHUA_NEU);
  if (r.requirement_text.startsWith("chưa")) ra.push(DON_CHUA_CONG_BO);
  return ra;
}

const PHIA_KHACH: Record<string, string> = {
  region: "khu vực mong muốn",
  employer_type: "loại cơ sở mong muốn",
  salary: "lương mong muốn",
  cost: "ngân sách",
};
const PHIA_DON: Record<string, string> = { salary: "lương", cost: "chi phí" };

/** Điểm cho dòng chưa đánh giá được là điểm trung lập theo luật, không phải điểm mạnh. */
export function moTaChuaRo(key: string, label: string, lyDo: string[], points: number): string {
  const muc = label.toLowerCase();
  const vi_sao = [
    lyDo.includes(KHACH_CHUA_NEU) && `bạn chưa nêu ${PHIA_KHACH[key] ?? muc}`,
    lyDo.includes(DON_CHUA_CONG_BO) && `đơn chưa công bố ${PHIA_DON[key] ?? muc}`,
  ].filter(Boolean).join(", ");
  return points > 0
    ? `${vi_sao} — điểm trung lập vì chưa đủ dữ liệu để đánh giá, không phải điểm mạnh`
    : vi_sao;
}

export function demKetQua(rows: CriterionRow[]) {
  return {
    dat: rows.filter((r) => r.result === "DAT").length,
    khong: rows.filter((r) => r.result === "KHONG_DAT").length,
    chuaRo: rows.filter((r) => r.result === "CHUA_RO").length,
  };
}

export default function BangDoiChieu({
  rows,
  softRows = [],
  eligible,
  score,
  scoreRanked,
  questions = [],
  anDiem = false,
}: {
  rows: CriterionRow[];
  softRows?: SoftRow[];
  eligible: boolean;
  score?: number;
  scoreRanked?: boolean;
  questions?: string[];
  /** Phòng tư vấn hai cột đặt điểm sang cột phải (`TheDiem`) — bảng ở đây giữ nguyên. */
  anDiem?: boolean;
}) {
  if (rows.length === 0) return null;
  const dem = demKetQua(rows);
  const khongDat = rows.filter((r) => r.result === "KHONG_DAT");
  const chuaRo = rows.filter((r) => r.result === "CHUA_RO");

  return (
    <div className="space-y-4">
      <p className="text-xs leading-5 text-slate-600">{CHU_THICH}</p>

      {/* --- Máy tính: bảng bốn cột --- */}
      <table className="hidden w-full border-collapse text-sm sm:table">
        <caption className="sr-only">Đối chiếu từng tiêu chí bắt buộc của đơn với hồ sơ của bạn</caption>
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th scope="col" className="py-2 pr-3 font-medium">Tiêu chí</th>
            <th scope="col" className="py-2 pr-3 font-medium">Yêu cầu của đơn</th>
            <th scope="col" className="py-2 pr-3 font-medium">Thông tin của bạn</th>
            <th scope="col" className="w-10 py-2 text-center font-medium">
              <span aria-hidden>✓</span>
              <span className="sr-only">Đáp ứng</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const thieu = thongTinKhach(row) === CHUA_CUNG_CAP;
            return (
              <tr key={row.key} className="border-b border-slate-100 align-top">
                <th scope="row" className="py-2.5 pr-3 text-left font-medium text-slate-800">
                  {row.label}
                </th>
                <td className="py-2.5 pr-3 text-slate-700">{row.requirement_text}</td>
                <td className={`py-2.5 pr-3 ${thieu ? "italic text-slate-500" : "text-slate-700"}`}>
                  {thongTinKhach(row)}
                </td>
                <td className="py-2.5 text-center">
                  <DauTich dat={row.result === "DAT"} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* --- Điện thoại: mỗi tiêu chí một thẻ --- */}
      <ul className="space-y-2 sm:hidden" aria-label="Đối chiếu từng tiêu chí bắt buộc">
        {rows.map((row) => {
          const thieu = thongTinKhach(row) === CHUA_CUNG_CAP;
          return (
            <li key={row.key} className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="font-medium text-slate-800">{row.label}</p>
                <span className="w-5 shrink-0 text-center">
                  <DauTich dat={row.result === "DAT"} />
                </span>
              </div>
              <dl className="mt-1.5 space-y-1 text-sm">
                <div>
                  <dt className="inline text-slate-500">Yêu cầu của đơn: </dt>
                  <dd className="inline text-slate-700">{row.requirement_text}</dd>
                </div>
                <div>
                  <dt className="inline text-slate-500">Thông tin của bạn: </dt>
                  <dd className={`inline ${thieu ? "italic text-slate-500" : "text-slate-700"}`}>
                    {thongTinKhach(row)}
                  </dd>
                </div>
              </dl>
            </li>
          );
        })}
      </ul>

      {/* --- Tổng kết bằng chữ: không đạt và thiếu thông tin vẫn tách rõ --- */}
      <div className="rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700 ring-1 ring-slate-200">
        <p>
          <strong>{rows.length}</strong> tiêu chí bắt buộc: <strong>{dem.dat}</strong> đạt ·{" "}
          <strong>{dem.khong}</strong> chưa đạt · <strong>{dem.chuaRo}</strong> chưa rõ.
        </p>
        {khongDat.length > 0 && (
          <div className="mt-2">
            <p className="font-medium text-slate-800">Chưa đáp ứng:</p>
            <ul className="mt-1 list-inside list-disc">
              {khongDat.map((r) => (
                <li key={r.key}>
                  {r.label} — đơn: {r.requirement_text}; hồ sơ: {thongTinKhach(r)}
                </li>
              ))}
            </ul>
          </div>
        )}
        {(chuaRo.length > 0 || questions.length > 0) && (
          <div className="mt-2">
            <p className="font-medium text-slate-800">
              Cần bổ sung — chưa rõ, <span className="underline">không phải</span> là không đạt:
            </p>
            <ul className="mt-1 list-inside list-disc">
              {chuaRo.map((r) => (
                <li key={r.key}>{r.label}</li>
              ))}
              {questions.map((cau) => (
                <li key={cau} className="text-slate-600">{cau}</li>
              ))}
            </ul>
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Dấu ✓ là đáp ứng theo thông tin bạn khai hoặc CV ghi, <strong>chưa phải</strong> đã
          được nhân viên xác minh — nhân viên sẽ đối chiếu giấy tờ khi gặp bạn.
        </p>
      </div>

      {/* --- Điểm khớp nguyện vọng: tách hẳn khỏi điều kiện bắt buộc --- */}
      {!anDiem && (
        <KhoiDiem eligible={eligible} score={score} scoreRanked={scoreRanked} softRows={softRows} />
      )}
    </div>
  );
}

type DiemProps = {
  eligible: boolean;
  score?: number;
  scoreRanked?: boolean;
  softRows?: SoftRow[];
};

/** Một dòng thành phần điểm, viết bằng chữ — dùng chung cho khối dưới bảng và thẻ cột phải. */
function moTaDong(r: SoftRow) {
  const lyDo = lyDoChuaRo(r);
  return {
    noiDung: `${r.label}: ${lyDo.includes(DON_CHUA_CONG_BO) ? "đơn chưa công bố" : r.requirement_text} — bạn: ${
      lyDo.includes(KHACH_CHUA_NEU) ? CHUA_CUNG_CAP : r.candidate_text
    }`,
    diem: `+${r.points}/${r.max_points}`,
    lyDo: lyDo.length > 0 ? moTaChuaRo(r.key, r.label, lyDo, r.points) : "",
  };
}

/** Khi nào không có điểm: chưa đạt điều kiện bắt buộc, hoặc khách chưa nêu nguyện vọng nào. */
function khongCoDiem({ eligible, scoreRanked }: DiemProps): string | null {
  if (!eligible) return "Đơn này chưa đạt điều kiện bắt buộc nên không chấm điểm nguyện vọng.";
  if (scoreRanked === false)
    return "Bạn chưa nêu khu vực, loại cơ sở, mức lương hay ngân sách mong muốn, nên chưa có điểm để xếp đơn này với đơn khác.";
  return null;
}

function KhoiDiem(props: DiemProps) {
  const { score, softRows = [] } = props;
  const vang = khongCoDiem(props);
  // Chỉ hiện con số khi máy chủ nói xếp hạng được — hai nhánh loại trừ nhau, không
  // bao giờ vừa có số vừa có câu "chưa có điểm".
  const hienSo = props.eligible && props.scoreRanked !== false;
  return (
    <div className="rounded-xl border border-slate-200 p-4 text-sm leading-6 text-slate-700">
      <p className="font-medium text-slate-800">Điểm khớp nguyện vọng</p>
      {!hienSo ? (
        <p className="mt-1 text-slate-600">{vang}</p>
      ) : (
        <>
          <p className="mt-1">
            <strong className="text-lg text-slate-900">{score}</strong>
            <span className="text-slate-500"> / 100</span> — mức khớp với nguyện vọng của bạn,{" "}
            <strong>không phải</strong> khả năng trúng tuyển.
          </p>
          {softRows.length > 0 && (
            <ul className="mt-2 space-y-1">
              {softRows.map((r) => {
                const d = moTaDong(r);
                return (
                  <li key={r.key} className="flex flex-wrap justify-between gap-2">
                    <span>{d.noiDung}</span>
                    <span className="text-slate-500">
                      {d.diem}
                      {d.lyDo && ` (${d.lyDo})`}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Thẻ điểm ở cột phải phòng tư vấn (bản thiết kế 08/10). Cùng luật với khối dưới
 * bảng — không đạt thì không có điểm, chưa nêu nguyện vọng thì nói thẳng — chỉ khác
 * cách trình bày: số lớn, thanh ngang, thành phần điểm gập lại.
 */
export function TheDiem(props: DiemProps) {
  const { score, softRows = [] } = props;
  const vang = khongCoDiem(props);
  // Chỉ hiện con số khi máy chủ nói xếp hạng được — hai nhánh loại trừ nhau, không
  // bao giờ vừa có số vừa có câu "chưa có điểm".
  const hienSo = props.eligible && props.scoreRanked !== false;
  const phanTram = Math.max(0, Math.min(100, score ?? 0));
  return (
    <section className="rounded-[10px] border border-slate-200 bg-white p-6" aria-label="Điểm khớp nguyện vọng">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Khớp nguyện vọng</p>
      {!hienSo ? (
        <p className="mt-3 text-sm leading-6 text-slate-600">{vang}</p>
      ) : (
        <>
          <p className="mt-2 flex items-baseline gap-1">
            <strong className="chu-nhan text-5xl not-italic text-slate-900" style={{ fontStyle: "normal" }}>
              {score}
            </strong>
            <span className="text-base text-slate-500"> / 100</span>
          </p>
          <div aria-hidden className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-reu-600" style={{ width: `${phanTram}%` }} />
          </div>
          {softRows.length > 0 && (
            <details className="mt-4 text-xs leading-5 text-slate-600">
              <summary className="cursor-pointer font-medium text-slate-700">Xem các thành phần điểm</summary>
              <ul className="mt-3 space-y-3">
                {softRows.map((r) => {
                  const d = moTaDong(r);
                  return (
                    <li key={r.key}>
                      <p className="flex justify-between gap-2 text-slate-800">
                        <span>{r.label}</span>
                        <span>{d.diem}</span>
                      </p>
                      <p className="mt-0.5">{d.noiDung}</p>
                      {d.lyDo && <p className="mt-0.5 text-slate-500">{d.lyDo}</p>}
                    </li>
                  );
                })}
              </ul>
            </details>
          )}
        </>
      )}
      <p className="mt-4 border-t border-slate-200 pt-3 text-[11px] leading-5 text-[#705f49]">
        Điểm thể hiện mức khớp với nguyện vọng, <strong>không phải</strong> khả năng trúng tuyển.
      </p>
    </section>
  );
}
