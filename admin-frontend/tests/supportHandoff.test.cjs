/**
 * Màn hình yêu cầu hỗ trợ không được nói hai điều ngược nhau.
 *
 * Kiểm trên trình duyệt ngày 06/10, `HT-C9AD4C`: bản bàn giao có mục ĐỐI CHIẾU đủ
 * 18 đơn, và ngay dưới là câu "Yêu cầu này không kèm kết quả đối chiếu". Câu ấy
 * vốn nói về `advice_block` — bảng của MỘT đơn, chỉ có khi khách gửi từ phòng tư
 * vấn theo đơn — nhưng đọc lên như thể không có đối chiếu nào.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { dungTrang, gia, cacNut, chu } = require("./dungTrang.cjs");

function yeuCau(them) {
  return {
    code: "HT-1", kind: "gap_mat", status: "cho_xu_ly", full_name: "Khách", phone: "0900000000",
    message: "Muốn gặp", job_order_code: null, advice_block: null, ban_giao: null,
    assigned_to: null, reply: null, created_at: new Date().toISOString(), ...them,
  };
}

async function moChiTiet(item) {
  const t = dungTrang("app/admin/support/page.tsx", {
    "@/components/admin/AdminUI": {
      EmptyState: gia("EmptyState"), ErrorBanner: gia("ErrorBanner"), PageHeader: gia("PageHeader"),
    },
    "@/lib/auth": { loadCurrentUser: async () => ({ email: "a@local.test", role: "consultant" }) },
    "@/lib/managementApi": {
      managementApi: {
        supportQueue: async () => ({ items: [item], count: 1 }),
        mySupportRequests: async () => ({ items: [], count: 0 }),
      },
    },
  });
  t.render();
  await t.flush();
  const nut = cacNut(t.render()).find((n) => n.type === "button" && chu(n) === "Xem chi tiết");
  nut.props.onClick();
  await t.flush();
  return chu(t.render());
}

test("có bàn giao (đã có đối chiếu cả hồ sơ) thì không nói 'không kèm kết quả đối chiếu'", async () => {
  const ra = await moChiTiet(yeuCau({ ban_giao: "ĐỐI CHIẾU\n  Đã xét 18 đơn, đủ điều kiện 11 đơn." }));
  assert.match(ra, /Đã xét 18 đơn/);
  assert.doesNotMatch(ra, /không kèm kết quả đối chiếu/);
  assert.match(ra, /không có bảng đối chiếu riêng cho một đơn/);
});

test("không có cả bàn giao lẫn bảng theo đơn thì vẫn nói rõ là không có", async () => {
  const ra = await moChiTiet(yeuCau({}));
  assert.match(ra, /không kèm kết quả đối chiếu/);
});

test("gửi từ phòng tư vấn theo đơn thì hiện bảng của đơn ấy", async () => {
  const ra = await moChiTiet(yeuCau({ ban_giao: "x", advice_block: "DH-0001 · ĐẠT" }));
  assert.match(ra, /DH-0001 · ĐẠT/);
  assert.doesNotMatch(ra, /không có bảng đối chiếu riêng/);
});
