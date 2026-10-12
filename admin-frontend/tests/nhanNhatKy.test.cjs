/**
 * Mọi hành động backend ghi vào nhật ký thao tác phải có nhãn tiếng Việt trên màn
 * "Nhật ký hệ thống" (12/10). Kiểm trình duyệt 12/10 thấy "support.released",
 * "support.handover" hiện nguyên mã máy và bộ lọc không chọn được.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const BACKEND = path.join(__dirname, "..", "..", "backend", "app");

function cacTepPy(thuMuc) {
  const ra = [];
  for (const muc of fs.readdirSync(thuMuc, { withFileTypes: true })) {
    const p = path.join(thuMuc, muc.name);
    if (muc.isDirectory() && muc.name !== "__pycache__") ra.push(...cacTepPy(p));
    else if (muc.name.endsWith(".py")) ra.push(p);
  }
  return ra;
}

test("mọi mã trong audit_action(...) ở backend đều có nhãn", () => {
  const ma = new Set();
  for (const p of cacTepPy(BACKEND)) {
    const nguon = fs.readFileSync(p, "utf8");
    for (const m of nguon.matchAll(/await audit_action\(\s*[^,]+,\s*"([a-z_]+\.[a-z_]+)"/g)) ma.add(m[1]);
  }
  assert.ok(ma.size >= 30, `chỉ dò được ${ma.size} mã — biểu thức dò có còn đúng không?`);
  const trang = fs.readFileSync(path.join(__dirname, "..", "app", "admin", "audit-logs", "page.tsx"), "utf8");
  const thieu = [...ma].filter((m) => !trang.includes(`"${m}":`)).sort();
  assert.deepEqual(thieu, []);
});
