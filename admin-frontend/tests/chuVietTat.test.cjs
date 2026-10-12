/**
 * Chữ viết tắt trên ô đại diện (12/10). Kiểm trình duyệt thấy màn Người dùng hiện "V("
 * cho "Kiểm vai trò Tư vấn (tạm)" — màn ấy tự tính, không đi qua bản đã sửa ở khung.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const GOC = path.join(__dirname, "..");

function nap() {
  const context = { exports: {} };
  const nguon = fs.readFileSync(path.join(GOC, "lib", "chuVietTat.ts"), "utf8");
  vm.runInNewContext(ts.transpileModule(nguon, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES5 },
  }).outputText, context);
  return context.exports.chuVietTat;
}

test("chỉ lấy tiếng bắt đầu bằng chữ cái, kể cả Đ và Ư", () => {
  const f = nap();
  assert.equal(f("Kiểm vai trò Tư vấn (tạm)"), "TV");
  assert.equal(f("Nguyễn Thị Hoa"), "TH");
  assert.equal(f("Đặng Ưng"), "ĐƯ");
  assert.equal(f("  Quản   trị viên "), "TV");
  assert.equal(f("(tạm) - 123"), "?");
  assert.equal(f(""), "?");
  assert.equal(f(undefined), "?");
});

function cacTep(thuMuc) {
  const ra = [];
  for (const muc of fs.readdirSync(path.join(GOC, thuMuc), { withFileTypes: true })) {
    const p = path.join(thuMuc, muc.name);
    if (muc.isDirectory()) ra.push(...cacTep(p));
    else if (muc.name.endsWith(".tsx")) ra.push(p);
  }
  return ra;
}

test("không màn nào tự tách tên lấy hai chữ cuối — phải gọi chuVietTat", () => {
  const sai = [];
  for (const p of [...cacTep("app"), ...cacTep("components")]) {
    const nguon = fs.readFileSync(path.join(GOC, p), "utf8");
    if (/\.split\([^)]*\)\s*(\.filter\([\s\S]*?\))?\s*\.slice\(-2\)/.test(nguon)) sai.push(p);
  }
  assert.deepEqual(sai, []);
});
