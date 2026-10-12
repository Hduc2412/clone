/**
 * Màn quản trị theo hướng hình thức 08/10 (Phase 5, 12/10).
 *
 * - Thanh bên phải CUỘN được: 16 mục cao hơn màn hình ≤ ~900px; trước 12/10 khối tài
 *   khoản bị đẩy ra ngoài và nút "Thoát" không bấm được. Soi đúng thẻ `<nav>` của
 *   AdminShell bằng bộ phân tích TypeScript, không tìm chuỗi trong cả tệp.
 * - Không còn mã màu thương hiệu cũ rải rác — đổi màu thì đổi ở `tailwind.config.ts`.
 * - Màu báo LỖI không dùng `brand`: nút bấm đỏ trầm và ô báo lỗi phải phân biệt được.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

const GOC = path.join(__dirname, "..");

function cacTep(thuMuc) {
  const ra = [];
  for (const muc of fs.readdirSync(path.join(GOC, thuMuc), { withFileTypes: true })) {
    const p = path.join(thuMuc, muc.name);
    if (muc.isDirectory()) ra.push(...cacTep(p));
    else if (muc.name.endsWith(".tsx")) ra.push(p);
  }
  return ra;
}

function lopCuaThe(nguon, tenThe) {
  const cay = ts.createSourceFile("x.tsx", nguon, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const ra = [];
  (function di(n) {
    if ((ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) && n.tagName.getText() === tenThe) {
      for (const tt of n.attributes.properties) {
        if (ts.isJsxAttribute(tt) && tt.name.getText() === "className" && tt.initializer) ra.push(tt.initializer.getText());
      }
    }
    ts.forEachChild(n, di);
  })(cay);
  return ra;
}

test("thanh bên cuộn được để khối tài khoản và nút Thoát luôn tới được", () => {
  const nguon = fs.readFileSync(path.join(GOC, "components", "admin", "AdminShell.tsx"), "utf8");
  const nav = lopCuaThe(nguon, "nav");
  assert.equal(nav.length, 1);
  assert.match(nav[0], /overflow-y-auto/);
  assert.match(nav[0], /min-h-0/, "thiếu min-h-0 thì phần tử flex không co lại được và vẫn không cuộn");
  assert.match(nguon, />Thoát</);
});

test("không còn mã màu thương hiệu cũ trong app/ và components/", () => {
  const sai = [];
  for (const p of [...cacTep("app"), ...cacTep("components")]) {
    const nguon = fs.readFileSync(path.join(GOC, p), "utf8");
    const m = nguon.match(/\[#(cb1d1e|a81718|b51718|171b22)\]/gi);
    if (m) sai.push(`${p}: ${m.join(", ")}`);
  }
  assert.deepEqual(sai, []);
});

test("ô báo lỗi dùng đỏ của Tailwind, không dùng màu thương hiệu", () => {
  const nguon = fs.readFileSync(path.join(GOC, "components", "admin", "AdminUI.tsx"), "utf8");
  const i = nguon.indexOf("export function ErrorBanner");
  assert.ok(i >= 0);
  const khoi = nguon.slice(i, nguon.indexOf("\n}\n", i));
  assert.match(khoi, /red-/);
  assert.doesNotMatch(khoi, /brand-/);
});


// Phông tự phục vụ (12/10): build không còn tải từ Google. Kiểm: không còn `next/font/google`;
// `phong-chu.css` chỉ trỏ tệp trong `public/fonts` và mọi tệp ấy có thật; có bộ chữ tiếng Việt
// cho cả hai phông; có giấy phép OFL đi kèm.
function kiemPhongTuPhucVu(GOC) {
  const layout = fs.readFileSync(path.join(GOC, 'app', 'layout.tsx'), 'utf8');
  assert.doesNotMatch(layout, /from ["']next\/font\/google["']/, 'còn tải phông từ Google lúc build');
  assert.match(layout, /import ["']\.\/phong-chu\.css["']/);
  const css = fs.readFileSync(path.join(GOC, 'app', 'phong-chu.css'), 'utf8');
  assert.doesNotMatch(css, /fonts\.(googleapis|gstatic)\.com/, 'CSS phông còn trỏ ra Google');
  const tep = [...css.matchAll(/url\(\/fonts\/([^)]+)\)/g)].map((m) => m[1]);
  assert.ok(tep.length >= 24, `chỉ thấy ${tep.length} tệp phông`);
  for (const t of tep) assert.ok(fs.existsSync(path.join(GOC, 'public', 'fonts', t)), `thiếu tệp ${t}`);
  for (const ho of ['Be Vietnam Pro', 'Gelasio']) {
    assert.match(css, new RegExp(`/\\* ${ho} \\d+ \\w+ — vietnamese \\*/`), `${ho} thiếu bộ chữ tiếng Việt`);
  }
  assert.match(css, /--font-sans: 'Be Vietnam Pro'/);
  assert.match(css, /--font-serif: 'Gelasio'/);
  assert.match(fs.readFileSync(path.join(GOC, 'public', 'fonts', 'OFL.txt'), 'utf8'), /SIL Open Font License/);
}

test("phông tự phục vụ: không tải từ Google lúc build, đủ tệp, có bộ tiếng Việt", () => {
  kiemPhongTuPhucVu(GOC);
});

// 12/10: consultant gõ thẳng /admin/users vẫn thấy khung trang. Một danh sách
// `CHI_QUAN_LY` phải canh CẢ thanh bên lẫn nội dung `<main>`.
test("trang chỉ dành cho quản lý: cùng một danh sách canh thanh bên và nội dung", () => {
  const nguon = fs.readFileSync(path.join(GOC, "components", "admin", "AdminShell.tsx"), "utf8");
  assert.match(nguon, /const CHI_QUAN_LY = \[[^\]]*"\/admin\/users"[^\]]*"\/admin\/audit-logs"/);
  assert.match(nguon, /\.filter\(\(item\) => !CHI_QUAN_LY\.includes\(item\.href\)/);
  const main = nguon.slice(nguon.indexOf("<main"), nguon.indexOf("</main>"));
  assert.match(main, /CHI_QUAN_LY\.some/, "nội dung trang không bị chặn khi gõ thẳng địa chỉ");
  assert.match(main, /user\.role === "consultant"/);
});
