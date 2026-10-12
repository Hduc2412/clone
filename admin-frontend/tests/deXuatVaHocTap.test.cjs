/**
 * Đề xuất của khách chờ nhân viên và tiến độ học — giao diện cho API đã có từ 08/10 (12/10).
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const { cacNut, chu } = require("./dungTrang.cjs");

function dung(api) {
  // setState xếp hàng, áp vào lần render sau — như React thật, không đổi giá trị ngay.
  const values = [];
  const cho = [];
  let cursor = 0;
  const react = {
    useState(initial) {
      const i = cursor++;
      if (!(i in values)) values[i] = typeof initial === "function" ? initial() : initial;
      return [values[i], (next) => { cho.push([i, next]); }];
    },
  };
  const jsx = (type, props, key) => ({ type, props: props || {}, key });
  const context = { exports: {}, require(ten) {
    if (ten === "react") return react;
    if (ten === "react/jsx-runtime") return { jsx, jsxs: jsx, Fragment: "Fragment" };
    if (ten === "@/lib/managementApi") return { managementApi: api };
    throw new Error(`Module chưa dựng: ${ten}`);
  } };
  const nguon = fs.readFileSync(path.join(__dirname, "..", "components", "admin", "DeXuatVaHocTap.tsx"), "utf8");
  vm.runInNewContext(ts.transpileModule(nguon, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  const M = context.exports;
  const render = (props) => {
    for (const [i, next] of cho.splice(0)) values[i] = typeof next === "function" ? next(values[i]) : next;
    cursor = 0;
    return M.default(props);
  };
  return { M, render };
}

const META = { japanese_levels: [{ code: "chua_hoc", label: "Chưa học" }, { code: "N5", label: "N5" }, { code: "N4", label: "N4" }, { code: "N3", label: "N3" }] };
const HO_SO = {
  code: "UV-1", version: 7,
  consultation_profile: { conflicts: [
    { field: "japanese_level", previous: "N4", suggested: "N3", kind: "khac_gia_tri_nhan_vien", trang_thai: "cho_nhan_vien" },
    { field: "birth_year", previous: 1999, suggested: 2000, kind: "khac_gia_tri_nhan_vien", trang_thai: "da_xu_ly" },
    { field: "major", previous: "X", suggested: "Điều dưỡng", kind: "khach_sua_o_nhan_vien_nhap", trang_thai: "da_ap_dung" },
    { field: "gender", previous: "nam", suggested: "nu", evidence: "em là nữ" },
  ] },
  trang_thai_tieng_nhat: { nhan: "N4 — có chứng chỉ, nhân viên đã đối chứng (bản gốc)" },
};
const NHAN = { japanese_level: "Tiếng Nhật", major: "Chuyên ngành" };

test("chỉ đề xuất đang chờ mới cần xử lý; đã xử lý và mâu thuẫn từ chat không lẫn vào", () => {
  const { M } = dung({});
  assert.deepEqual(M.deXuatDangCho(HO_SO).map((c) => c.field), ["japanese_level"]);
  assert.deepEqual(M.khachDaSua(HO_SO).map((c) => c.field), ["major"]);
});

test("hiện giá trị nhân viên và lời khách; giữ nguyên mà không ghi lý do thì không gọi API", async () => {
  const goi = [];
  const { render } = dung({ giuNguyenDeXuat: async (...a) => { goi.push(a); return HO_SO; } });
  const props = { profile: HO_SO, meta: META, nhanTruong: NHAN, onDaDoi: () => {}, onSuaTheoKhach: () => {} };
  let cay = render(props);
  assert.match(chu(cay), /Nhân viên đã ghi:\s+N4\s+· Khách nói:\s+N3/);
  assert.doesNotMatch(chu(cay), /undefined/);
  const nut = () => cacNut(render(props)).find((n) => n.type === "button" && chu(n).includes("Giữ giá trị nhân viên"));
  await nut().props.onClick();
  assert.equal(goi.length, 0, "giữ nguyên mà không có lý do");
  assert.match(chu(render(props)), /Ghi lý do giữ giá trị/);
  const o = cacNut(render(props)).find((n) => n.type === "input" && String(n.props["aria-label"]).includes("Lý do giữ giá trị"));
  o.props.onChange({ target: { value: "Đã đối chứng bằng gốc" } });
  render(props);
  await nut().props.onClick();
  assert.deepEqual(goi[0], ["UV-1", "japanese_level", "Đã đối chứng bằng gốc"]);
});

test("ghi tiến độ: đang học không gửi kết quả; hoàn thành gửi kết quả và phiên bản hồ sơ", async () => {
  const goi = [];
  const { render } = dung({ ghiHocTap: async (ma, body) => { goi.push([ma, body]); return HO_SO; } });
  const props = { profile: HO_SO, meta: META, nhanTruong: NHAN, onDaDoi: () => {}, onSuaTheoKhach: () => {} };
  const form = () => cacNut(render(props)).find((n) => n.type === "form");
  await form().props.onSubmit({ preventDefault() {} });
  assert.equal(goi[0][1].trang_thai, "dang_hoc");
  assert.equal(goi[0][1].ket_qua, null);
  assert.equal(goi[0][1].expected_version, 7);
  const chon = cacNut(render(props)).filter((n) => n.type === "select")[0];
  chon.props.onChange({ target: { value: "da_hoan_thanh" } });
  assert.match(chu(render(props)), /Trình độ dùng để đối chiếu đơn KHÔNG đổi/);
  await form().props.onSubmit({ preventDefault() {} });
  assert.equal(goi[1][1].trang_thai, "da_hoan_thanh");
  assert.equal(goi[1][1].ket_qua, "N4");
});
