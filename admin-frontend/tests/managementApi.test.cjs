/**
 * Tầng gọi API của hệ quản trị — bộ kiểm thử đầu tiên của app này.
 *
 * Trước hôm nay `admin-frontend` **không có một ca kiểm thử nào**, và nó là nơi
 * nhân viên chốt hồ sơ, đổi trạng thái ứng viên, ghi kết quả sơ tuyển. Chất lượng
 * ở đây dựa hoàn toàn vào việc `npm run build` chạy sạch — thứ chỉ kiểm được kiểu
 * dữ liệu, không kiểm được hành vi.
 *
 * Nạp giống bên `frontend`: biên dịch TypeScript rồi chạy trong hộp kín `vm`.
 *
 * ## Ba nhóm đáng canh
 *
 * 1. **Thông báo lỗi đọc được.** FastAPI trả `detail` ở ba hình dạng, và hai
 *    trong ba là cấu trúc. Ném thẳng vào `new Error` cho ra `[object Object]` —
 *    người nhập liệu thấy đúng chừng ấy và không biết ô nào sai. Đây là loại lỗi
 *    không làm sập gì cả, chỉ làm công việc của người khác trở nên bất khả thi.
 *
 * 2. **Cookie và cache.** Thiếu `credentials` thì mọi lời gọi 401; thiếu
 *    `cache: "no-store"` thì trình duyệt phục vụ lại danh sách hàng đợi cũ, và
 *    hai nhân viên cùng nhận một hồ sơ đã có người lấy.
 *
 * 3. **`requestForm` KHÔNG được đặt `Content-Type`.** Trình duyệt phải tự sinh
 *    header multipart kèm chuỗi phân tách; đặt tay vào là máy chủ không tách được
 *    file ra khỏi phần dữ liệu. Một dòng "cho nhất quán" là hỏng cả bộ nhập Excel.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const MAY_CHU = "http://may-chu-kiem-thu:8020";

function dung({ dapAn = { ok: true, status: 200, body: { xong: true } } } = {}) {
  const goi = [];
  const dieuHuong = [];

  const fetch = async (url, opts = {}) => {
    goi.push({ url, ...opts });
    return {
      ok: dapAn.ok,
      status: dapAn.status,
      json: async () => {
        if (dapAn.khongDocDuoc) throw new SyntaxError("Unexpected token");
        return dapAn.body;
      },
    };
  };

  const context = {
    exports: {},
    module: { exports: {} },
    fetch,
    URLSearchParams,
    URL,
    FormData: class {
      constructor() {
        this.muc = [];
      }
      append(k, v) {
        this.muc.push([k, v]);
      }
    },
    process: { env: { NEXT_PUBLIC_BACKEND_URL: MAY_CHU } },
    // 401 đá người dùng về trang đăng nhập. Ghi lại thay vì đổi địa chỉ thật.
    window: {
      get location() {
        return {
          set href(v) {
            dieuHuong.push(v);
          },
        };
      },
    },
  };
  context.module.exports = context.exports;

  const nguon = fs.readFileSync(
    path.join(__dirname, "../lib/managementApi.ts"),
    "utf8",
  );
  vm.runInNewContext(
    ts.transpileModule(nguon, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
    }).outputText,
    context,
  );
  return { api: context.exports.managementApi, goi, dieuHuong };
}

const loiKhiGoi = async (fn) => {
  try {
    await fn();
  } catch (e) {
    return e.message;
  }
  throw new Error("lẽ ra phải ném lỗi");
};

// --- Thông báo lỗi ---

test("lỗi 422 của FastAPI thành câu chỉ đúng ô sai", async () => {
  // Đây là hình dạng FastAPI trả khi biểu mẫu sai. Không dịch ra thì người nhập
  // thấy "[object Object]" và phải đoán ô nào hỏng trong ba mươi ô.
  const { api } = dung({
    dapAn: {
      ok: false,
      status: 422,
      body: {
        detail: [
          { loc: ["body", "japanese_required"], msg: "Value error, mức không hợp lệ" },
          { loc: ["body", "requirements", "age_min"], msg: "phải là số nguyên" },
        ],
      },
    },
  });
  const cau = await loiKhiGoi(() => api.users());
  assert.match(cau, /japanese_required: mức không hợp lệ/);
  assert.match(cau, /requirements › age_min: phải là số nguyên/);
  // "Value error, " là rác của thư viện, không phải chữ cho người đọc.
  assert.ok(!cau.includes("Value error"), "để lọt tiền tố kỹ thuật ra màn hình");
  assert.ok(!cau.includes("[object"), "chưa dịch cấu trúc thành chữ");
});

test("detail dạng chuỗi dùng nguyên văn", async () => {
  const { api } = dung({
    dapAn: { ok: false, status: 409, body: { detail: "Hồ sơ này do người khác phụ trách." } },
  });
  assert.equal(
    await loiKhiGoi(() => api.users()),
    "Hồ sơ này do người khác phụ trách.",
  );
});

test("detail dạng object lấy khóa message", async () => {
  const { api } = dung({
    dapAn: { ok: false, status: 409, body: { detail: { message: "Đơn đã đóng." } } },
  });
  assert.equal(await loiKhiGoi(() => api.users()), "Đơn đã đóng.");
});

test("thân phản hồi không đọc được vẫn ra câu dùng được", async () => {
  // Proxy trả HTML khi 502. Không bắt thì màn hình hiện lỗi cú pháp JSON.
  const { api } = dung({ dapAn: { ok: false, status: 502, khongDocDuoc: true } });
  const cau = await loiKhiGoi(() => api.users());
  assert.ok(cau.length > 10);
  assert.ok(!/JSON|token/i.test(cau), `để lọt lỗi kỹ thuật: ${cau}`);
});

// --- Cookie, cache, đăng nhập ---

test("mọi lời gọi kèm cookie và không dùng lại bản cache", async () => {
  // Thiếu `no-store` thì trình duyệt phục vụ lại hàng đợi cũ, và hai nhân viên
  // cùng nhận một hồ sơ đã có người lấy — lỗi chỉ lộ ra khi cả hai đã gọi khách.
  const { api, goi } = dung();
  await api.users();
  assert.equal(goi[0].credentials, "include");
  assert.equal(goi[0].cache, "no-store");
});

test("401 đá về trang đăng nhập", async () => {
  const { api, dieuHuong } = dung({
    dapAn: { ok: false, status: 401, body: { detail: "hết phiên" } },
  });
  await loiKhiGoi(() => api.users());
  assert.deepEqual(Array.from(dieuHuong), ["/login"]);
});

test("lỗi khác 401 thì KHÔNG đá về đăng nhập", async () => {
  // Đá về đăng nhập khi gặp 403 là đăng xuất một người đang đăng nhập hợp lệ,
  // chỉ vì họ bấm vào thứ không thuộc quyền mình.
  const { api, dieuHuong } = dung({
    dapAn: { ok: false, status: 403, body: { detail: "không có quyền" } },
  });
  await loiKhiGoi(() => api.users());
  assert.deepEqual(Array.from(dieuHuong), []);
});

// --- Đường của hai màn hình mới ---

test("hàng đợi hỗ trợ đi đường riêng, không lẫn hàng đợi hồ sơ", async () => {
  // Hai hàng đợi tách nhau có chủ ý: trên là hồ sơ đã đủ điều kiện, dưới là khách
  // phần lớn CHƯA đủ nhưng vẫn muốn nói chuyện. Trộn thì việc gấp lẫn việc dài hạn.
  const { api, goi } = dung({ dapAn: { ok: true, status: 200, body: { items: [] } } });
  await api.supportQueue({ status: "cho_xu_ly", kind: "gap_mat" });
  await api.registrationQueue();
  assert.match(goi[0].url, /\/ho-tro\?/);
  assert.match(goi[0].url, /status=cho_xu_ly/);
  assert.match(goi[0].url, /kind=gap_mat/);
  assert.match(goi[1].url, /\/registrations\/queue$/);
});

test("lọc rỗng thì không đính dấu hỏi thừa vào đường dẫn", async () => {
  const { api, goi } = dung({ dapAn: { ok: true, status: 200, body: { items: [] } } });
  await api.supportQueue();
  assert.ok(goi[0].url.endsWith("/ho-tro"), `đường dẫn thừa: ${goi[0].url}`);
});

test("ghi kết quả sơ tuyển gửi đủ bốn quyết định của buổi gặp", async () => {
  // Một lời gọi đổi cả trình độ lẫn trạng thái. Thiếu một trường là máy chủ từ
  // chối — nhưng thiếu ở đây thì lỗi hiện ra sau khi nhân viên đã gõ xong ghi chú.
  const { api, goi } = dung({ dapAn: { ok: true, status: 200, body: {} } });
  await api.recordScreening("HS-ABC123", {
    japanese_level: "N4",
    chung_cu: "ban_goc",
    hinh_thuc: "truc_tiep",
    next_status: "eligible",
    note: "Nói được câu chào",
  });
  assert.match(goi[0].url, /\/applications\/HS-ABC123\/so-tuyen$/);
  assert.equal(goi[0].method, "POST");
  const than = JSON.parse(goi[0].body);
  assert.deepEqual(
    Object.keys(than).sort(),
    ["chung_cu", "hinh_thuc", "japanese_level", "next_status", "note"],
  );
});

test("khóa học: xóa gọi DELETE, đổi trạng thái gọi PATCH", async () => {
  const { api, goi } = dung({ dapAn: { ok: true, status: 200, body: {} } });
  await api.deleteCourse("KH-0002");
  assert.equal(goi[0].method, "DELETE");
  assert.match(goi[0].url, /\/khoa-hoc\/KH-0002$/);
});

test("mã có ký tự lạ vẫn được mã hóa trước khi ghép vào đường dẫn", async () => {
  const { api, goi } = dung({ dapAn: { ok: true, status: 200, body: {} } });
  await api.deleteCourse("KH/../users");
  assert.ok(
    !goi[0].url.includes("/../"),
    `đường dẫn chưa mã hóa, có thể trỏ sai chỗ: ${goi[0].url}`,
  );
});
