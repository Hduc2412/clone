/**
 * Con số trên badge phải nói đúng nhãn nó đứng cạnh.
 *
 * Lỗi bị bắt bằng E2E ngày 01/10: mục "Lịch hẹn" ở thanh bên hiện số **thông báo
 * chưa đọc**. Hai con số không liên quan gì nhau — toàn bộ thông báo đang có là
 * hồ sơ mới đăng ký và tin nhắn khách để lại, không có cái nào là lịch hẹn. Nhân
 * viên thấy "10" cạnh chữ Lịch hẹn, bấm vào thì `appointments_total = 0` và màn
 * hình trống.
 *
 * Loại lỗi này không làm sập gì, không có ngoại lệ nào để bắt, và `npm run build`
 * không thấy gì sai: cả hai đều là `number`. Chỉ người đọc màn hình mới phát hiện.
 *
 * ## Vì sao soi cấu trúc chứ không tìm chuỗi
 *
 * Ca kiểm kiểu `assert(nguon.includes("appointments_pending"))` sẽ xanh ngay cả
 * khi chuỗi ấy nằm ở một chỗ hoàn toàn khác trong file — đúng cái bẫy đã làm ba
 * ca kiểm thử của bộ này vô dụng hồi 29/09. Nên ở đây dùng chính bộ phân tích của
 * TypeScript: tìm đúng biểu thức canh badge rồi xem nó đọc biến nào.
 *
 * Thẻ `<Link>` ở thanh bên nhận `href={item.href}` — một biến, không phải chuỗi.
 * Nên không định vị được bằng thuộc tính `href`; phải định vị bằng chính phép so
 * sánh `item.href === "/admin/appointments"` đứng canh badge.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

const DUONG = path.join(__dirname, "..", "components", "admin", "AdminShell.tsx");
const NGUON = fs.readFileSync(DUONG, "utf8");
const CAY = ts.createSourceFile(
  DUONG,
  NGUON,
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TSX,
);

function diQua(node, lam) {
  lam(node);
  node.forEachChild((con) => diQua(con, lam));
}

/** Tên biến mà `useState` gán cho giá trị lấy từ một khóa của overview. */
function bienGanVoi(khoa) {
  let setter = null;
  diQua(CAY, (n) => {
    if (!ts.isCallExpression(n) || n.arguments.length !== 1) return;
    const arg = n.arguments[0];
    if (!ts.isPropertyAccessExpression(arg)) return;
    if (arg.name.text !== khoa) return;
    if (ts.isIdentifier(n.expression)) setter = n.expression.text;
  });
  if (!setter) return null;
  let bien = null;
  diQua(CAY, (n) => {
    if (!ts.isVariableDeclaration(n) || !n.name) return;
    if (!ts.isArrayBindingPattern(n.name)) return;
    const ten = n.name.elements.map((e) =>
      e.name && ts.isIdentifier(e.name) ? e.name.text : null,
    );
    if (ten[1] !== setter) return;
    // Phải là một `useState` của chính nó, không phải bí danh của ô nhớ khác.
    //
    // Đột biến làm lọt bộ kiểm thử lúc đầu: `const [lichCho, setLichCho] =
    // [unread, setUnread]`. Tên hai biến khác nhau, nên phép so tên vẫn xanh,
    // mà giá trị thì vẫn là một — đúng lỗi gốc, chỉ đổi cách viết. Xét tên là
    // chưa đủ; phải xét cả nguồn của ô nhớ.
    const nguon = n.initializer;
    if (!nguon || !ts.isCallExpression(nguon)) return;
    if (nguon.expression.getText() !== "useState") return;
    bien = ten[0];
  });
  return bien;
}

/** Tên biến trong nhánh phải của `<so_sanh ... > && (<badge>)`. */
function bienCanhBadgeTheoSoSanh(href) {
  let ket = null;
  diQua(CAY, (n) => {
    if (!ts.isBinaryExpression(n)) return;
    if (n.operatorToken.kind !== ts.SyntaxKind.AmpersandAmpersandToken) return;
    if (!n.left.getText().includes(JSON.stringify(href))) return;
    const ten = new Set();
    diQua(n.right, (m) => {
      if (ts.isIdentifier(m)) ten.add(m.text);
    });
    // Biến canh badge nằm ở nhánh `&&` trong cùng; lấy luôn cả điều kiện bên
    // phải của phép `&&` lồng nhau để không bỏ sót `dieu_kien && so > 0 && (...)`.
    diQua(n, (m) => {
      if (!ts.isBinaryExpression(m)) return;
      if (m.operatorToken.kind !== ts.SyntaxKind.GreaterThanToken) return;
      if (ts.isIdentifier(m.left)) ten.add(m.left.text);
    });
    ket = ten;
  });
  return ket;
}

/** Mọi giá trị `href` viết thẳng dưới dạng chuỗi trong các thẻ `<Link>`. */
function hrefChuoiCuaCacLink() {
  const ra = [];
  diQua(CAY, (n) => {
    if (!ts.isJsxElement(n) && !ts.isJsxSelfClosingElement(n)) return;
    const mo = ts.isJsxElement(n) ? n.openingElement : n;
    if (mo.tagName.getText() !== "Link") return;
    const a = mo.attributes.properties.find(
      (p) => ts.isJsxAttribute(p) && p.name.getText() === "href",
    );
    if (a && a.initializer && ts.isStringLiteral(a.initializer)) {
      ra.push(a.initializer.text);
    }
  });
  return ra;
}

test("hai con số là hai biến khác nhau, lấy từ hai khóa khác nhau", () => {
  const bienLich = bienGanVoi("appointments_pending");
  const bienThongBao = bienGanVoi("notifications_unread");
  assert.ok(bienLich, "không thấy biến nào nhận giá trị appointments_pending");
  assert.ok(bienThongBao, "không thấy biến nào nhận giá trị notifications_unread");
  assert.notEqual(bienLich, bienThongBao, "hai con số phải là hai biến khác nhau");
});

test("badge cạnh mục Lịch hẹn đọc số lịch đang chờ, không đọc số thông báo", () => {
  const bienLich = bienGanVoi("appointments_pending");
  const bienThongBao = bienGanVoi("notifications_unread");
  const trongBadge = bienCanhBadgeTheoSoSanh("/admin/appointments");
  assert.ok(trongBadge, "không tìm thấy badge nào canh mục /admin/appointments");
  assert.ok(
    trongBadge.has(bienLich),
    `badge của mục Lịch hẹn phải đọc '${bienLich}'; nó đang đọc: ${[...trongBadge].join(", ")}`,
  );
  assert.ok(
    !trongBadge.has(bienThongBao),
    `badge của mục Lịch hẹn KHÔNG được đọc '${bienThongBao}' (số thông báo chưa đọc)`,
  );
});

test("badge Thông báo ở đầu trang không trỏ sang màn hình lịch hẹn", () => {
  // Thông báo hiện có hai loại: hồ sơ mới đăng ký (`application`) và tin nhắn
  // khách để lại (`support_request`). Không loại nào xử lý ở màn hình lịch hẹn.
  const href = hrefChuoiCuaCacLink();
  assert.ok(
    href.includes("/admin/queue"),
    `badge Thông báo phải trỏ về hàng đợi hồ sơ; href đang có: ${href.join(", ")}`,
  );
  assert.ok(
    !href.includes("/admin/appointments"),
    `có thẻ Link viết thẳng tới màn hình lịch hẹn: ${href.join(", ")}`,
  );
});
