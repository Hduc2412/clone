/**
 * Chuyển và trả yêu cầu hỗ trợ từ giao diện.
 *
 * Trước 07/10 trang hỗ trợ không có thao tác nào đổi người xử lý — 67 yêu cầu mang tên
 * tài khoản đã xóa phải trả về hàng đợi bằng script. Giờ quản lý có tab "Đang có người
 * xử lý" với ô "Chuyển cho…", và người đang giữ tự trả được về hàng đợi.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { dungTrang, gia, cacNut, chu } = require("./dungTrang.cjs");

const A = "a@local.test";
const B = "b@local.test";

function yc(them) {
  return {
    code: "HT-1", kind: "gap_mat", status: "dang_xu_ly", full_name: "Khách", phone: "0900000000",
    message: "Muốn gặp", job_order_code: null, advice_block: null, ban_giao: null,
    assigned_to: A, reply: null, created_at: new Date().toISOString(), ...them,
  };
}

async function moTrang({ vaiTro, email, tab }) {
  const goi = [];
  const api = {
    supportQueue: async (p) => {
      goi.push(["queue", p.status]);
      return { items: p.status === "dang_xu_ly" ? [yc({})] : [], count: 1, total: 1 };
    },
    mySupportRequests: async () => ({ items: [yc({ assigned_to: email })], count: 1 }),
    users: async () => [
      { email: A, full_name: "A", status: "active" },
      { email: B, full_name: "B", status: "active" },
    ],
    handoverSupportRequest: async (...a) => { goi.push(["chuyen", ...a]); return {}; },
    releaseSupportRequest: async (...a) => { goi.push(["tra", ...a]); return {}; },
  };
  const t = dungTrang("app/admin/support/page.tsx", {
    "@/components/admin/AdminUI": {
      EmptyState: gia("EmptyState"), ErrorBanner: gia("ErrorBanner"), PageHeader: gia("PageHeader"),
    },
    "@/lib/auth": { loadCurrentUser: async () => ({ email, role: vaiTro }) },
    "@/lib/managementApi": { managementApi: api },
  });
  t.context.window.prompt = () => "A nghỉ phép";
  t.render();
  await t.flush();
  if (tab) {
    const nut = cacNut(t.render()).find((n) => n.type === "button" && chu(n) === tab);
    if (!nut) return { t, goi, coTab: false };
    nut.props.onClick();
    await t.flush();
  }
  return { t, goi, coTab: true, cay: t.render() };
}

test("quản lý có tab 'Đang có người xử lý' và chuyển được cho B", async () => {
  const { t, goi, coTab, cay } = await moTrang({ vaiTro: "manager", email: "ql@local.test", tab: "Đang có người xử lý" });
  assert.ok(coTab);
  assert.ok(goi.some((g) => g[0] === "queue" && g[1] === "dang_xu_ly"));
  const o = cacNut(cay).find((n) => n.type === "select" && chu(n).includes("Chuyển cho"));
  const lua = cacNut(o).filter((n) => n.type === "option").map((n) => n.props.value);
  assert.ok(lua.includes(B) && !lua.includes(A), "ô chuyển phải có B, không có chính A");
  o.props.onChange({ target: { value: B } });
  await t.flush();
  assert.deepEqual(goi.find((g) => g[0] === "chuyen"), ["chuyen", "HT-1", B, "A nghỉ phép"]);
});

test("người đang giữ tự trả về hàng đợi được, không có ô chuyển", async () => {
  const { t, goi, cay } = await moTrang({ vaiTro: "consultant", email: A, tab: "Tôi đang xử lý" });
  assert.equal(cacNut(cay).filter((n) => n.type === "select" && chu(n).includes("Chuyển cho")).length, 0);
  const nut = cacNut(cay).find((n) => n.type === "button" && chu(n) === "Trả về hàng đợi");
  nut.props.onClick();
  await t.flush();
  assert.deepEqual(goi.find((g) => g[0] === "tra"), ["tra", "HT-1", "A nghỉ phép"]);
});

test("tư vấn viên không thấy tab của quản lý", async () => {
  const { coTab } = await moTrang({ vaiTro: "consultant", email: A, tab: "Đang có người xử lý" });
  assert.equal(coTab, false);
});
