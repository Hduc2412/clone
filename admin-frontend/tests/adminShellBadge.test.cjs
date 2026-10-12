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

/**
 * Tên biến mà `useState` gán cho giá trị trả về của `managementApi.<hamApi>()`.
 *
 * Từ 12/10 cả hai số đều đọc khóa `count` (lịch chờ theo phạm vi, thông báo theo phạm
 * vi) nên không phân biệt được bằng tên khóa nữa — phân biệt bằng HÀM API trong chuỗi
 * `managementApi.<hamApi>().then((data) => setX(data.count))`.
 */
function bienNhanTu(hamApi) {
  let setter = null;
  diQua(CAY, (n) => {
    if (!ts.isCallExpression(n) || !ts.isPropertyAccessExpression(n.expression)) return;
    if (n.expression.name.text !== "then") return;
    const goi = n.expression.expression;
    if (!ts.isCallExpression(goi) || !ts.isPropertyAccessExpression(goi.expression)) return;
    if (goi.expression.name.text !== hamApi || goi.expression.expression.getText() !== "managementApi") return;
    diQua(n.arguments[0], (m) => {
      if (ts.isCallExpression(m) && ts.isIdentifier(m.expression) && /^set[A-Z]/.test(m.expression.text)) {
        setter = m.expression.text;
      }
    });
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

test("hai con số là hai biến khác nhau, lấy từ hai đường API khác nhau", () => {
  // Lịch chờ đọc `pendingAppointmentCount` (theo phạm vi, 12/10) — trước đó đọc
  // `appointments_pending` của trang tổng quan, tức cả hệ thống: consultant thấy
  // "Lịch hẹn 34" mà mở danh sách thì 0 lịch.
  const bienLich = bienNhanTu("pendingAppointmentCount");
  const bienThongBao = bienNhanTu("notificationCount");
  assert.ok(bienLich, "không thấy biến nào nhận giá trị từ pendingAppointmentCount()");
  assert.ok(bienThongBao, "không thấy biến nào nhận giá trị từ notificationCount()");
  assert.notEqual(bienLich, bienThongBao, "hai con số phải là hai biến khác nhau");
});

test("badge cạnh mục Lịch hẹn đọc số lịch đang chờ, không đọc số thông báo", () => {
  const bienLich = bienNhanTu("pendingAppointmentCount");
  const bienThongBao = bienNhanTu("notificationCount");
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

test("thanh bên không còn đọc số lịch chờ của cả hệ thống", () => {
  assert.equal(bienNhanTu("overview"), null, "AdminShell lại lấy số từ trang tổng quan (cả hệ thống)");
});

test("badge Thông báo ở đầu trang không trỏ sang màn hình lịch hẹn", () => {
  // 12/10: có trang Thông báo riêng (đọc `/notifications`, đánh dấu đã đọc được). Trước
  // đó chưa có màn hình nào đọc thông báo nên nút trỏ tạm về hàng đợi hồ sơ.
  const href = hrefChuoiCuaCacLink();
  assert.ok(
    href.includes("/admin/notifications"),
    `badge Thông báo phải trỏ về trang Thông báo; href đang có: ${href.join(", ")}`,
  );
  assert.ok(
    !href.includes("/admin/appointments"),
    `có thẻ Link viết thẳng tới màn hình lịch hẹn: ${href.join(", ")}`,
  );
});
