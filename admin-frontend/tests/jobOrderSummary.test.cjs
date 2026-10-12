/**
 * Trang chi tiết đơn cho consultant (09/10).
 *
 * Biểu mẫu sửa chỉ dành cho Admin/Manager, nên trước đây consultant mở đơn chỉ thấy
 * trạng thái và hạn nộp. Ghim ba điều:
 * - consultant thấy bản chỉ đọc, không thấy biểu mẫu; Admin/Manager ngược lại;
 * - bản chỉ đọc tách điều kiện bắt buộc khỏi thông tin tham khảo;
 * - bản chỉ đọc không bao giờ in `internal_note`, kể cả khi lỡ có trong dữ liệu.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { dungTrang, gia, cacNut, chu } = require("./dungTrang.cjs");

const DON = {
  code: "DH-0001", title: "Điều dưỡng Tokyo", employer_name: "Viện Sakura", employer_type: "vien_duong_lao",
  program: "tokutei_ginou", prefecture: "Tokyo", region_group: "kanto", city: "Setagaya", quota: 5, hired_count: 1,
  deadline: "2026-12-24", status: "open", published: true, description: null,
  requirements: { japanese_required: "N4", education_required: "cao_dang", experience_min: 0, age_min: 20, age_max: 35, gender_pref: "khong_yeu_cau" },
  reference: { salary_min: 180000, salary_max: 200000, allowances: ["Nhà ở"], cost_total_vnd: 90000000,
    interview_date: null, departure_expected: null, highlights: [] },
  labels: { status: "Đang tuyển", employer_type: "Viện dưỡng lão", program: "Kỹ năng đặc định", region_group: "Kantō",
    japanese_required: "N4", education_required: "Cao đẳng", gender_pref: "Không yêu cầu" },
  consultant_note: "Hỏi chứng chỉ gốc",
  created_at: "", updated_at: "",
};
const META = { transitions: { open: [] }, statuses: [], employer_types: [], programs: [], japanese_levels: [],
  education_levels: [], gender_prefs: [], regions: [], prefectures: [] };

async function moTrang(vaiTro, don = DON) {
  const t = dungTrang("app/admin/job-orders/[code]/page.tsx", {
    "next/navigation": { useParams: () => ({ code: don.code }), useRouter: () => ({ push() {} }) },
    "@/components/admin/AdminUI": { ErrorBanner: gia("ErrorBanner"), PageHeader: gia("PageHeader") },
    "@/components/admin/JobOrderForm": { __esModule: true, default: gia("JobOrderForm") },
    "@/components/admin/JobOrderSummary": { __esModule: true, default: gia("JobOrderSummary") },
    "@/components/admin/JobOrderStatusBadge": { JobOrderStatusBadge: gia("Badge"), PublicVisibilityBadge: gia("Badge2") },
    "@/lib/managementApi": { managementApi: {
      jobOrder: async () => don, jobOrderEvents: async () => [], jobOrderMeta: async () => META,
    } },
    "@/lib/auth": { loadCurrentUser: async () => ({ role: vaiTro }) },
  });
  t.render();
  await t.flush();
  return t.render();
}
const co = (cay, ten) => cacNut(cay).some((n) => n.type?.displayName === ten);

test("consultant: bản chỉ đọc, không biểu mẫu sửa; manager: biểu mẫu, không bản chỉ đọc", async () => {
  const tv = await moTrang("consultant");
  assert.ok(co(tv, "JobOrderSummary"), "consultant không thấy nội dung đơn");
  assert.ok(!co(tv, "JobOrderForm"));
  const ql = await moTrang("manager");
  assert.ok(co(ql, "JobOrderForm"));
  assert.ok(!co(ql, "JobOrderSummary"));
});

test("consultant: ghi chú tư vấn có, khối ghi chú nội bộ không (máy chủ đã gỡ khóa)", async () => {
  const ra = chu(await moTrang("consultant"));
  assert.match(ra, /Hỏi chứng chỉ gốc/);
  assert.doesNotMatch(ra, /Ghi chú nội bộ/);
});

// --- Bản chỉ đọc --------------------------------------------------------------

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function napTomTat() {
  const jsx = (type, props, key) => ({ type, props: props || {}, key });
  const context = { exports: {}, require(ten) {
    if (ten === "react/jsx-runtime") return { jsx, jsxs: jsx, Fragment: "Fragment" };
    throw new Error(`Module chưa dựng: ${ten}`);
  } };
  const nguon = fs.readFileSync(path.join(__dirname, "..", "components", "admin", "JobOrderSummary.tsx"), "utf8");
  vm.runInNewContext(ts.transpileModule(nguon, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  return context.exports;
}
const TomTat = napTomTat();
function moRong(cay) {
  if (cay == null || typeof cay === "boolean") return cay;
  if (Array.isArray(cay)) return cay.map(moRong);
  if (typeof cay !== "object") return cay;
  if (typeof cay.type === "function") return moRong(cay.type(cay.props));
  return { ...cay, props: { ...cay.props, children: moRong(cay.props.children) } };
}
const veTomTat = (don) => moRong({ type: TomTat.default, props: { order: don } });

test("tách điều kiện bắt buộc khỏi thông tin tham khảo; lương ở nhóm tham khảo", () => {
  const cay = veTomTat(DON);
  const ra = chu(cay);
  const iBatBuoc = ra.indexOf("Điều kiện bắt buộc");
  const iThamKhao = ra.indexOf("Thông tin tham khảo");
  assert.ok(iBatBuoc >= 0 && iThamKhao > iBatBuoc);
  const tiengNhat = ra.indexOf("Từ N4");
  assert.ok(tiengNhat > iBatBuoc && tiengNhat < iThamKhao, "tiếng Nhật phải nằm trong nhóm bắt buộc");
  const luong = ra.indexOf("180.000 ¥");
  assert.ok(luong > iThamKhao, "lương phải nằm trong nhóm tham khảo — lương không loại ai");
  assert.match(ra, /90\.000\.000 đ/);
  assert.match(ra, /20–35 tuổi/);
  assert.match(ra, /Kinh nghiệm Không yêu cầu/);
});

test("trường trống ghi 'Chưa có thông tin', không để ô rỗng", () => {
  const ra = chu(veTomTat(DON));
  assert.match(ra, /Ngày phỏng vấn Chưa có thông tin/);
  assert.match(ra, /Điểm nổi bật Chưa có thông tin/);
});

test("không in internal_note dù dữ liệu lỡ mang theo", () => {
  const ra = chu(veTomTat({ ...DON, internal_note: "BI_MAT_NOI_BO" }));
  assert.doesNotMatch(ra, /BI_MAT_NOI_BO/);
});

test("định dạng lương và tuổi", () => {
  assert.equal(TomTat.luongText(null, null), "Chưa có thông tin");
  assert.equal(TomTat.luongText(180000, 180000), "180.000 ¥ / tháng");
  assert.equal(TomTat.tuoiText(null, 30), "Đến 30 tuổi");
  assert.equal(TomTat.tuoiText(null, null), "Không giới hạn");
});
