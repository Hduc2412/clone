/**
 * Hàng đợi bị cắt thì màn hình phải nói ra.
 *
 * Đo ngày 06/10: 72 hồ sơ đăng ký chờ, trang hiện 50, không có dấu hiệu nào cho
 * thấy còn 22 người — và vì xếp người chờ lâu nhất lên đầu, 22 người bị giấu là
 * những người vừa đăng ký. Máy chủ nay trả `total`; trang so nó với số đang hiện.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { dungTrang, gia, chu } = require("./dungTrang.cjs");

const UI = {
  "@/components/admin/AdminUI": {
    EmptyState: gia("EmptyState"), ErrorBanner: gia("ErrorBanner"), PageHeader: gia("PageHeader"),
  },
  "@/lib/auth": { loadCurrentUser: async () => ({ email: "a@local.test", role: "consultant" }) },
};

function hoSo(i) {
  return {
    application_code: `HS-${String(i).padStart(6, "0")}`, lead_code: "LD-1", customer_name: "Khách",
    phone: "0900000000", status: "draft", assigned_to: null, job_order_code: "DH-0001",
    job_order_title: null, match_score: null, profile_code: "UV-1", report_code: null,
    japanese_level: null, destination: null, created_at: new Date().toISOString(),
  };
}

async function moHangDoiHoSo(soHien, tong) {
  const t = dungTrang("app/admin/queue/page.tsx", {
    ...UI,
    "@/lib/managementApi": { managementApi: {
      registrationQueue: async () => ({
        items: Array.from({ length: soHien }, (_, i) => hoSo(i)), count: soHien, total: tong,
      }),
    } },
  });
  t.render();
  await t.flush();
  return chu(t.render()).replace(/\s+/g, " ");
}

async function moHangDoiHoTro(soHien, tong) {
  const yc = (i) => ({
    code: `HT-${i}`, kind: "gap_mat", status: "cho_xu_ly", full_name: "Khách", phone: "0900000000",
    message: "", job_order_code: null, advice_block: null, ban_giao: null, assigned_to: null,
    reply: null, created_at: new Date().toISOString(),
  });
  const t = dungTrang("app/admin/support/page.tsx", {
    ...UI,
    "@/lib/managementApi": { managementApi: {
      supportQueue: async () => ({ items: Array.from({ length: soHien }, (_, i) => yc(i)), count: soHien, total: tong }),
      mySupportRequests: async () => ({ items: [], count: 0 }),
    } },
  });
  t.render();
  await t.flush();
  return chu(t.render()).replace(/\s+/g, " ");
}

test("hàng đợi hồ sơ: bị cắt thì nói rõ đang hiện bao nhiêu trên bao nhiêu", async () => {
  const ra = await moHangDoiHoSo(50, 72);
  assert.match(ra, /72 hồ sơ đang chờ/);
  assert.match(ra, /Đang hiện 50 trên 72 hồ sơ chờ/);
  assert.match(ra, /22 người vừa đăng ký/);
});

test("hàng đợi hồ sơ: đủ cả hàng thì chỉ hiện tổng, không cảnh báo", async () => {
  const ra = await moHangDoiHoSo(3, 3);
  assert.match(ra, /3 hồ sơ đang chờ/);
  assert.doesNotMatch(ra, /Đang hiện/);
});

test("tổng quan: thẻ 'Hồ sơ chờ nhận' đếm theo tổng máy chủ, không theo phần đã cắt", async () => {
  const t = dungTrang("app/admin/page.tsx", {
    "@/components/admin/AdminUI": UI["@/components/admin/AdminUI"],
    "@/components/admin/DonCanXuLy": { __esModule: true, default: gia("DonCanXuLy") },
    "@/lib/managementApi": { managementApi: {
      overview: async () => ({}),
      jobOrders: async () => [],
      registrationQueue: async () => ({ items: Array.from({ length: 50 }, (_, i) => hoSo(i)), count: 50, total: 72 }),
      candidateProfiles: async () => [],
      appointments: async () => [],
      scoreboard: async () => ({ items: [], rules: [] }),
    } },
  });
  t.render();
  await t.flush();
  const ra = chu(t.render()).replace(/\s+/g, " ");
  assert.match(ra, /Hồ sơ chờ nhận 72/);
});

test("hàng đợi hỗ trợ: bị cắt thì nói rõ", async () => {
  const ra = await moHangDoiHoTro(4, 9);
  assert.match(ra, /Đang hiện 4 trên 9 yêu cầu chờ/);
});

test("hàng đợi hỗ trợ: đủ cả hàng thì không cảnh báo", async () => {
  const ra = await moHangDoiHoTro(4, 4);
  assert.doesNotMatch(ra, /Đang hiện/);
});
