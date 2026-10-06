/**
 * Quản lý chuyển được hồ sơ đang do người khác giữ — từ giao diện, không chỉ API.
 *
 * Kiểm trên trình duyệt thật ngày 06/10: A nhận `HS-78B363`, quản lý vào hàng đợi
 * thì tab "Tôi đang phụ trách" trống, tab "Chưa ai nhận" không có hồ sơ ấy. Ô
 * "Chuyển cho…" chỉ hiện với hồ sơ người đăng nhập tự giữ, còn tư vấn viên thì
 * không có quyền chuyển. Bước A → B khi ấy phải gọi thẳng API.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { dungTrang, gia, cacNut, chu } = require("./dungTrang.cjs");

const A = "a@local.test";
const B = "b@local.test";
const DA_XOA = "da-xoa@local.test";

function hoSo(code, nguoi) {
  return {
    application_code: code, lead_code: "LD-1", customer_name: "Khách mẫu", phone: "0900000000",
    status: "received", assigned_to: nguoi, job_order_code: "DH-0001", job_order_title: "Đơn",
    match_score: 75, profile_code: "UV-1", report_code: null, japanese_level: "N4",
    destination: null, created_at: new Date().toISOString(),
  };
}

async function moHangDoi({ vaiTro, tab }) {
  const goi = [];
  const api = {
    registrationQueue: async () => ({ items: [], count: 0 }),
    myRegistrations: async () => [],
    assignedRegistrations: async () => { goi.push("assigned"); return [hoSo("HS-1", A), hoSo("HS-2", DA_XOA)]; },
    users: async () => [
      { email: A, full_name: "A", status: "active" },
      { email: B, full_name: "B", status: "active" },
    ],
    handoverRegistration: async (...args) => { goi.push(["handover", ...args]); return {}; },
  };
  const t = dungTrang("app/admin/queue/page.tsx", {
    "@/components/admin/AdminUI": {
      EmptyState: gia("EmptyState"), ErrorBanner: gia("ErrorBanner"), PageHeader: gia("PageHeader"),
    },
    "@/lib/auth": { loadCurrentUser: async () => ({ email: "ql@local.test", role: vaiTro }) },
    "@/lib/managementApi": { managementApi: api },
  });
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

test("quản lý có tab hồ sơ của mọi người, kèm ô chuyển", async () => {
  const { goi, coTab, cay } = await moHangDoi({ vaiTro: "manager", tab: "Đang có người phụ trách" });
  assert.ok(coTab);
  assert.ok(goi.includes("assigned"));
  const o = cacNut(cay).filter((n) => n.type === "select");
  assert.equal(o.length, 2, "mỗi hồ sơ một ô Chuyển cho…");
  assert.match(chu(cay), new RegExp(`Người phụ trách:\\s+${A}`));
});

test("ô chuyển của hồ sơ A không liệt kê chính A, có B", async () => {
  const { cay } = await moHangDoi({ vaiTro: "manager", tab: "Đang có người phụ trách" });
  const oDau = cacNut(cay).find((n) => n.type === "select");
  const lua = cacNut(oDau).filter((n) => n.type === "option").map((n) => n.props.value);
  assert.ok(lua.includes(B));
  assert.ok(!lua.includes(A));
});

test("chọn B thì gọi đúng API chuyển giao, kèm lý do", async () => {
  const { t, goi, cay } = await moHangDoi({ vaiTro: "manager", tab: "Đang có người phụ trách" });
  t.context.window.prompt = () => "A nghỉ phép";
  cacNut(cay).find((n) => n.type === "select").props.onChange({ target: { value: B } });
  await t.flush();
  assert.deepEqual(goi.find((g) => Array.isArray(g)), ["handover", "HS-1", B, "A nghỉ phép"]);
});

test("người giữ là tài khoản đã xóa thì nói ra", async () => {
  const { cay } = await moHangDoi({ vaiTro: "manager", tab: "Đang có người phụ trách" });
  assert.match(chu(cay), /tài khoản không còn hoạt động/);
});

test("tư vấn viên không thấy tab này và không gọi API của nó", async () => {
  const { coTab, goi } = await moHangDoi({ vaiTro: "consultant", tab: "Đang có người phụ trách" });
  assert.equal(coTab, false);
  assert.ok(!goi.includes("assigned"));
});
