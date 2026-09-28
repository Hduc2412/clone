/**
 * Mã phiên hành trình — kiểm ở mức đơn vị, không cần trình duyệt thật.
 *
 * Nạp thẳng `lib/journeySession.ts` vào một hộp kín rồi tự dựng những thứ nó
 * cần: `window`, `localStorage`, `sessionStorage`, `fetch`, `process.env`.
 * Nhờ vậy chạy được bằng `node --test`, không phải dựng Next lên.
 *
 * Điều quan trọng nhất bộ này canh: **trình duyệt không còn tự sinh mã phiên**.
 * Trước 22/09/2026 nó sinh bằng `crypto.randomUUID()` và máy chủ tin vào mã ấy,
 * nên ai gửi lên mã người khác là đọc được hồ sơ của họ. Nay mã do máy chủ cấp
 * kèm cookie đã ký. Nếu có ai lỡ tay đưa việc sinh mã về lại phía trình duyệt
 * thì `khong_tu_sinh_ma_khi_chua_hoi_may_chu` đỏ ngay.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const MA_MAY_CHU = "11111111-1111-4111-8111-111111111111";
const MA_CU = "22222222-2222-4222-8222-222222222222";

function kho() {
  const data = new Map();
  return {
    getItem: k => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
    removeItem: k => data.delete(k),
  };
}

/**
 * Dựng hộp kín và nạp module vào.
 *
 * `maDangGiu` là thứ đã nằm sẵn trong `localStorage`. `dapAn` là thứ máy chủ sẽ
 * trả về; đặt `null` để giả lập backend không với tới được.
 */
function dung({ maDangGiu = null, dapAn = MA_MAY_CHU } = {}) {
  const goi = [];
  const su_kien = [];
  const window = {
    localStorage: kho(),
    sessionStorage: kho(),
    dispatchEvent: e => su_kien.push(e.type),
  };
  if (maDangGiu) window.localStorage.setItem("xkld-candidate-session", maDangGiu);

  const fetch = async (url, opts) => {
    goi.push({ url, ...opts });
    if (dapAn === null) throw new Error("khong ket noi duoc");
    return { ok: true, json: async () => ({ session_id: dapAn, vua_mo: true }) };
  };

  const context = {
    exports: {},
    window,
    fetch,
    // Module đọc `process.env.NEXT_PUBLIC_BACKEND_URL` để biết gọi backend ở
    // đâu. Thiếu `process` thì module ném ngay lúc nạp, và mọi ca đều đỏ với
    // một lỗi chẳng liên quan gì tới thứ đang kiểm.
    process: { env: {} },
    Event: class { constructor(type) { this.type = type; } },
  };
  const source = fs.readFileSync(path.join(__dirname, "../lib/journeySession.ts"), "utf8");
  vm.runInNewContext(
    ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText,
    context,
  );
  return { api: context.exports, window, goi, su_kien };
}

const maDangLuu = window_ => window_.localStorage.getItem("xkld-candidate-session");

test("chưa có gì thì không bịa ra mã", () => {
  const { api } = dung();
  assert.equal(api.peekSessionId(), "");
  assert.equal(api.getSessionId(), "");
});

test("khong_tu_sinh_ma_khi_chua_hoi_may_chu", () => {
  // Mã tự sinh nay vô dụng vì không có cookie đi kèm — gọi API nào cũng 401.
  // Tệ hơn: nó trông như một phiên hợp lệ nên lỗi nổ ra ở tận màn hình sau.
  const { api, window, goi } = dung();
  api.getSessionId();
  assert.equal(maDangLuu(window), null);
  assert.equal(goi.length, 0, "đọc mã phiên không được phép gọi mạng");
});

test("mở phiên thì lấy mã của máy chủ và ghi lại", async () => {
  const { api, window, goi } = dung();
  assert.equal(await api.ensureSessionId(), MA_MAY_CHU);
  assert.equal(maDangLuu(window), MA_MAY_CHU);
  assert.equal(goi.length, 1);
  assert.match(goi[0].url, /\/public\/phien$/);
  // Thiếu dòng này thì trình duyệt không gửi cookie sang cổng khác, và mọi thứ
  // phía sau trả 401.
  assert.equal(goi[0].credentials, "include");
});

test("gọi nhiều lần cùng lúc chỉ mở một phiên", async () => {
  const { api, goi } = dung();
  const [a, b, c] = await Promise.all([
    api.ensureSessionId(), api.ensureSessionId(), api.ensureSessionId(),
  ]);
  assert.equal(a, MA_MAY_CHU);
  assert.equal(b, MA_MAY_CHU);
  assert.equal(c, MA_MAY_CHU);
  assert.equal(goi.length, 1, "vài thành phần cùng gọi lúc tải trang vẫn là một phiên");
});

test("backend không với tới được thì giữ mã cũ, không bịa mã mới", async () => {
  const { api, window } = dung({ maDangGiu: MA_CU, dapAn: null });
  assert.equal(await api.ensureSessionId(), MA_CU);
  assert.equal(maDangLuu(window), MA_CU);
});

test("mất mạng mà cũng chưa có mã cũ thì trả chuỗi rỗng", async () => {
  const { api } = dung({ dapAn: null });
  assert.equal(await api.ensureSessionId(), "");
});

test("chỉ ghi lại mã đúng hình dạng UUID", () => {
  const { api, window } = dung();
  api.rememberSessionId("12345678");
  assert.equal(maDangLuu(window), null);
  api.rememberSessionId(MA_MAY_CHU);
  assert.equal(maDangLuu(window), MA_MAY_CHU);
});

test("bỏ qua mã hỏng đang nằm trong máy", () => {
  const { api } = dung({ maDangGiu: "phien-ung-vien-0001" });
  assert.equal(api.peekSessionId(), "");
});

test("hỏi lại máy chủ thì bỏ bản sao trong máy", async () => {
  // Đường thoát khi mã trong máy lệch khỏi cookie: không có nó thì trang chết
  // hẳn ở câu "phiên đã hết hạn", tải lại bao nhiêu lần cũng vậy.
  const { api, window } = dung({ maDangGiu: MA_CU });
  assert.equal(await api.refreshSessionId(), MA_MAY_CHU);
  assert.equal(maDangLuu(window), MA_MAY_CHU);
});

test("khai lại từ đầu thì dọn cả hai kho và xin phiên khác", async () => {
  const { api, window, goi, su_kien } = dung({ maDangGiu: MA_CU });
  window.sessionStorage.setItem("xkld-chat-state-v1", "{}");

  assert.equal(await api.resetSession(), MA_MAY_CHU);
  assert.equal(window.sessionStorage.getItem("xkld-chat-state-v1"), null);
  assert.equal(maDangLuu(window), MA_MAY_CHU);
  // Cookie là `httponly` nên JavaScript không tự xoá được — phải nhờ máy chủ
  // ghi đè qua đường riêng.
  assert.match(goi[0].url, /\/public\/phien\/moi$/);
  assert.deepEqual(su_kien, ["xkld-journey-reset"]);
});
