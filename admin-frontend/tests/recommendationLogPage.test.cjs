/**
 * Trang chi tiết nhật ký giới thiệu phải dựng được đơn bị loại.
 *
 * Lỗi bắt trên trình duyệt thật ngày 06/10: mở `RL-891284` ra "Application error:
 * a client-side exception", console báo `Cannot read properties of undefined
 * (reading 'map')`. Nhật ký rút gọn đơn bị loại (`matching_service._gon_lai`): bỏ
 * hẳn khóa `soft_rows`, và `hard_rows` chỉ còn các dòng không đạt. Trang vẫn gọi
 * `item.soft_rows.map`. Đo cùng ngày: 154 trên 218 nhật ký có đơn như thế.
 *
 * `npm run build` không bắt được, vì kiểu `MatchItem` khai `soft_rows` là bắt
 * buộc — kiểu nói dối về dữ liệu. Nên ca này dựng trang thật với dữ liệu đúng
 * hình dạng bản ghi trong Mongo, và gọi cả các component con.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { dungTrang, gia, chu } = require("./dungTrang.cjs");

const DUONG = "app/admin/recommendation-logs/[code]/page.tsx";

// Đúng các khóa của một đơn bị loại trong `RL-891284` (DH-0017), rút gọn giá trị.
const DON_LOAI = {
  code: "DH-0017", title: "Đơn bị loại", employer_name: "Cơ sở X", prefecture: "Osaka",
  region_group: "kansai", employer_type: "benh_vien", program: "epa", deadline: "2026-12-01",
  eligible: false, score: 0, rank: null,
  hard_rows: [{ key: "japanese_level", label: "Tiếng Nhật", requirement_text: "N3",
    candidate_text: "N4", result: "KHONG_DAT" }],
  hard_rows_passed: 6, gaps: [], missing_info: [], labels: {},
};
const DON_DAT = {
  ...DON_LOAI, code: "DH-0001", title: "Đơn đạt", eligible: true, score: 75, rank: 1,
  hard_rows: [{ key: "japanese_level", label: "Tiếng Nhật", requirement_text: "N4",
    candidate_text: "N4", result: "DAT" }],
  soft_rows: [{ key: "region", label: "Khu vực", requirement_text: "Tokyo",
    candidate_text: "Tokyo", points: 40, max_points: 40, kind: "mem" }],
};
delete DON_DAT.hard_rows_passed;
const NHAT_KY = {
  code: "RL-1", profile_code: "UV-1", profile_version: 1, as_of: "2026-10-06",
  total_considered: 2, eligible_count: 1, trigger: "public", actor_email: null,
  engine_version: "1.0.0", weights_version: "1.0", weights_fingerprint: "w",
  orders_fingerprint: "o", pool_query: { published: true }, missing_info: [],
  items: [DON_DAT, DON_LOAI],
};

async function moNhatKy(nhatKy = NHAT_KY) {
  const t = dungTrang(DUONG, {
    "next/navigation": { useParams: () => ({ code: nhatKy.code }) },
    "@/components/admin/AdminUI": { ErrorBanner: gia("ErrorBanner"), PageHeader: gia("PageHeader") },
    "@/lib/managementApi": { managementApi: { recommendationLog: async () => nhatKy } },
  });
  t.render();
  await t.flush();
  return chu(t.render());
}

test("dựng được nhật ký có đơn bị loại thiếu soft_rows", async () => {
  const ra = await moNhatKy();
  assert.match(ra, /Đơn bị loại/);
  assert.match(ra, /DH-0017/);
});

test("đơn bị loại không hiện điểm, kể cả điểm 0", async () => {
  const ra = await moNhatKy({ ...NHAT_KY, items: [DON_LOAI] });
  assert.doesNotMatch(ra, /\d+\s*\/\s*100/);
  assert.doesNotMatch(ra, /\+\s*0\b/);
  assert.match(ra, /không được chấm điểm nguyện vọng/);
});

test("nói rõ các tiêu chí đạt đã được lược khỏi nhật ký", async () => {
  const ra = await moNhatKy({ ...NHAT_KY, items: [DON_LOAI] });
  assert.match(ra, /6 tiêu chí bắt buộc khác đã đạt/);
});

test("đơn đạt vẫn hiện đủ điểm và dòng tiêu chí mềm", async () => {
  const ra = await moNhatKy({ ...NHAT_KY, items: [DON_DAT] });
  assert.match(ra, /75 \/100/);
  assert.match(ra, /\+ 40/);
  assert.doesNotMatch(ra, /không được chấm điểm nguyện vọng/);
});
