/**
 * Trang Thông báo (12/10). Trước đó không màn hình nào đọc `/notifications`: con số trên
 * nút chỉ tăng và không ai đánh dấu đã đọc được.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const { dungTrang, gia, cacNut, chu } = require("./dungTrang.cjs");

function napLib() {
  const nguon = fs.readFileSync(path.join(__dirname, "..", "lib", "thongBao.ts"), "utf8");
  const context = { exports: {}, require() { return {}; } };
  vm.runInNewContext(ts.transpileModule(nguon, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  return context.exports;
}
const L = napLib();

test("mỗi loại việc mở đúng màn hình xử lý", () => {
  assert.equal(L.noiXuLy({ reference_type: "job_order", reference_code: "DH-0003" }), "/admin/job-orders/DH-0003");
  assert.equal(L.noiXuLy({ reference_type: "support_request", reference_code: "HT-1" }), "/admin/support");
  assert.equal(L.noiXuLy({ reference_type: "application", reference_code: "HS-1" }), "/admin/queue");
  assert.equal(L.noiXuLy({ reference_type: "appointment", reference_code: "LH-1" }), "/admin/appointments");
});

test("thông báo lịch hẹn kiểu cũ (không có title) vẫn có câu đọc được", () => {
  const t = L.tieuDe({ appointment_code: "LH-1", customer_name: "T. T. H.", appointment_date: "2026-10-20", appointment_time: "09:00" });
  assert.match(t, /Lịch hẹn mới — T\. T\. H\. · 2026-10-20 09:00/);
  assert.equal(L.tieuDe({ title: "Ứng viên mới đăng ký đơn" }), "Ứng viên mới đăng ký đơn");
});

test("mô tả lấy tên khách (đã rút gọn ở máy chủ nếu cần), mã đơn và mã việc", () => {
  const m = L.moTa({ reference_code: "HS-1", detail: { customer_name: "T. T. T. H.", job_order_code: "DH-0001" } });
  assert.equal(m, "Khách: T. T. T. H. · Đơn DH-0001 · HS-1");
});

async function moTrang(ds, goi) {
  const t = dungTrang("app/admin/notifications/page.tsx", {
    "@/components/admin/AdminUI": { EmptyState: gia("EmptyState"), ErrorBanner: gia("ErrorBanner"), PageHeader: gia("PageHeader") },
    "@/lib/thongBao": { ...L, baoThongBaoDaDoi: () => goi.push(["bao_doi"]) },
    "@/lib/managementApi": { managementApi: {
      notifications: async (chiChuaDoc) => { goi.push(["ds", chiChuaDoc]); return ds; },
      markNotificationRead: async (ma) => { goi.push(["doc", ma]); },
      markAllNotificationsRead: async () => { goi.push(["doc_het"]); return { updated: 2 }; },
    } },
  });
  t.render();
  await t.flush();
  return t;
}

test("trang hiện thông báo chưa đọc; bấm 'Đã đọc' gọi đúng mã, rồi nạp lại", async () => {
  const goi = [];
  const ds = [{ title: "Ứng viên mới đăng ký đơn", reference_type: "application", reference_code: "HS-9", is_read: false, created_at: "2026-10-12T08:00:00Z" }];
  const t = await moTrang(ds, goi);
  const cay = t.render();
  assert.match(chu(cay), /Ứng viên mới đăng ký đơn/);
  assert.deepEqual(goi[0], ["ds", true], "mặc định chỉ chưa đọc");
  const nut = cacNut(cay).find((n) => n.type === "button" && chu(n).includes("Đã đọc"));
  await nut.props.onClick();
  await t.flush();
  assert.ok(goi.some((g) => g[0] === "doc" && g[1] === "HS-9"));
  assert.ok(goi.filter((g) => g[0] === "ds").length >= 2, "đánh dấu xong phải nạp lại danh sách");
});

test("nút 'Đánh dấu tất cả đã đọc' gọi API đánh dấu hết theo phạm vi người xem", async () => {
  const goi = [];
  const t = await moTrang([{ title: "X", reference_type: "application", reference_code: "HS-1", is_read: false, created_at: "" }], goi);
  const header = cacNut(t.render()).find((n) => n.type?.displayName === "PageHeader");
  const nut = cacNut(header.props.action).find((n) => n.type === "button" && chu(n).includes("tất cả"));
  await nut.props.onClick();
  assert.ok(goi.some((g) => g[0] === "doc_het"));
  assert.ok(goi.some((g) => g[0] === "bao_doi"), "đánh dấu xong phải báo nút Thông báo nạp lại số");
});
