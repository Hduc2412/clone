/**
 * Tầng gọi API của luồng ứng viên — kiểm ở mức đơn vị, không cần trình duyệt.
 *
 * Mọi thao tác của ứng viên đi qua đúng file này: gửi CV, sửa hồ sơ, xem đơn phù
 * hợp, hỏi bot, xin gặp nhân viên. Trước bộ này nó **không có ca kiểm thử nào** —
 * cả phần giao diện chỉ có 10 ca và chúng chỉ phủ việc quản lý mã phiên.
 *
 * Cách nạp giống `journeySession.test.cjs`: biên dịch TypeScript rồi chạy trong
 * một hộp kín, tự dựng `fetch` và `require` mà module cần. Không phải dựng Next.
 *
 * ## Ba thứ đáng canh nhất, và vì sao
 *
 * 1. **`credentials: "include"`**. Cookie phiên là `httponly`; trình duyệt chỉ gửi
 *    kèm khi được yêu cầu rõ. Xóa một dòng ấy thì **mọi đường `/public/*` trả
 *    401** — toàn bộ luồng ứng viên chết, mà mã vẫn biên dịch sạch và `npm run
 *    build` vẫn xanh. Đúng loại lỗi không có test thì không ai thấy trước.
 *
 * 2. **`clean()` bỏ ô trống**. Nguyên tắc nền của cả hệ: *trường vắng mặt nghĩa
 *    là chưa rõ, không phải rỗng*. Gửi `""` lên cho một ô khách chưa điền là biến
 *    "chưa hỏi tới" thành "đã hỏi và khách không có" — bộ đối chiếu đọc hai thứ
 *    ấy khác nhau, và cái sau loại người.
 *
 * 3. **Lỗi mạng ra câu tiếng Việt, không ra `TypeError`**. Ứng viên phần lớn dùng
 *    điện thoại và mạng di động. "Failed to fetch" hiện lên màn hình là một lời
 *    nhắn không ai hiểu và không chỉ được đường nào đi tiếp.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const MAY_CHU = "http://may-chu-kiem-thu:8020";
const PHIEN = "11111111-1111-4111-8111-111111111111";

/**
 * Nạp `lib/candidateApi.ts` vào hộp kín.
 *
 * `dapAn` mô tả thứ máy chủ trả về. `null` nghĩa là không gọi được — dùng để kiểm
 * nhánh mất mạng.
 */
function dung({ dapAn = { ok: true, status: 200, body: { xong: true } } } = {}) {
  const goi = [];

  const fetch = async (url, opts = {}) => {
    goi.push({ url, ...opts });
    if (dapAn === null) throw new TypeError("Failed to fetch");
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
    // Hộp kín của `vm` không có sẵn global của trình duyệt. Thiếu cái nào thì ca
    // kiểm thử đỏ với một `ReferenceError` chẳng liên quan gì tới thứ đang kiểm.
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
    // `candidateApi` import hai module cùng thư mục. Dựng bản giả thay vì nạp
    // thật: `journeySession` cần `window` và `localStorage`, mà ở đây không kiểm
    // nó — nó đã có bộ riêng.
    require: (ten) => {
      if (ten === "./publicApi") return { BACKEND_PUBLIC_URL: MAY_CHU };
      if (ten === "./journeySession") {
        return {
          ensureSessionId: async () => PHIEN,
          getSessionId: () => PHIEN,
          refreshSessionId: async () => PHIEN,
          rememberSessionId: () => {},
          resetSession: () => {},
        };
      }
      throw new Error(`hộp kín chưa dựng module ${ten}`);
    },
  };
  context.module.exports = context.exports;

  const nguon = fs.readFileSync(
    path.join(__dirname, "../lib/candidateApi.ts"),
    "utf8",
  );
  vm.runInNewContext(
    ts.transpileModule(nguon, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
    }).outputText,
    context,
  );
  return { api: context.exports, goi };
}

// --- Cookie phiên ---

test("mọi lời gọi đều kèm cookie phiên", async () => {
  // Thiếu `credentials: "include"` thì mọi đường /public/* trả 401 và toàn bộ
  // luồng ứng viên chết, trong khi mã vẫn biên dịch sạch.
  const { api, goi } = dung();
  await api.fetchProfile(PHIEN);
  await api.confirmProfile(PHIEN);
  await api.fetchMatches(PHIEN);
  assert.equal(goi.length, 3);
  for (const g of goi) {
    assert.equal(g.credentials, "include", `${g.url} không gửi cookie phiên`);
  }
});

test("gửi file cũng phải kèm cookie phiên", async () => {
  // Đường tải file dựng `fetch` riêng, không đi qua `request()` — nên nó là chỗ
  // dễ quên nhất, và quên thì ứng viên gửi CV xong nhận 401.
  const { api, goi } = dung({
    dapAn: { ok: true, status: 201, body: { document: {} } },
  });
  await api.uploadDocument(PHIEN, { name: "cv.pdf" });
  assert.equal(goi[0].credentials, "include");
  assert.equal(goi[0].method, "POST");
});

test("mã phiên được mã hóa trước khi ghép vào đường dẫn", async () => {
  const { api, goi } = dung();
  await api.fetchProfile("a b/c?d");
  assert.ok(
    !goi[0].url.includes(" ") && !goi[0].url.includes("?d"),
    `đường dẫn chưa mã hóa: ${goi[0].url}`,
  );
});

// --- Ô trống ---

test("ô trống KHÔNG được gửi lên", async () => {
  // Nguyên tắc nền: trường vắng mặt nghĩa là chưa rõ, không phải rỗng. Gửi ""
  // cho ô khách chưa điền là biến "chưa hỏi tới" thành "đã hỏi và khách không
  // có" — bộ đối chiếu đọc hai thứ ấy khác nhau, và cái sau loại người.
  const { api, goi } = dung();
  await api.updateProfile(
    PHIEN,
    { japanese_level: "N4", education_level: "", major: null },
    { desired_prefecture: undefined },
  );
  const than = JSON.parse(goi[0].body);
  assert.deepEqual(Object.keys(than.fields), ["japanese_level"]);
  assert.deepEqual(than.preferences, {});
});

test("số 0 và false KHÔNG bị coi là ô trống", async () => {
  // `0 năm kinh nghiệm` là một câu trả lời, không phải một ô chưa điền. Lọc bằng
  // `if (!value)` sẽ nuốt mất nó — và ứng viên chưa có kinh nghiệm thành ứng
  // viên chưa khai kinh nghiệm.
  const { api, goi } = dung();
  await api.updateProfile(PHIEN, { experience_years: 0, care_experience: false }, {});
  const than = JSON.parse(goi[0].body);
  assert.equal(than.fields.experience_years, 0);
  assert.equal(than.fields.care_experience, false);
});

// --- Lỗi ---

test("mất mạng cho ra câu tiếng Việt, không phải TypeError", async () => {
  const { api } = dung({ dapAn: null });
  await assert.rejects(
    () => api.fetchProfile(PHIEN),
    (loi) => {
      assert.equal(loi.name, "ApiError");
      assert.equal(loi.status, 0);
      assert.match(loi.message, /mạng/i);
      assert.ok(!/fetch/i.test(loi.message), "để lọt chữ kỹ thuật ra màn hình");
      return true;
    },
  );
});

test("mất mạng lúc gửi file cũng nói rõ là chuyện gửi file", async () => {
  const { api } = dung({ dapAn: null });
  await assert.rejects(
    () => api.uploadDocument(PHIEN, { name: "cv.pdf" }),
    (loi) => {
      assert.equal(loi.status, 0);
      assert.match(loi.message, /không gửi được file/i);
      return true;
    },
  );
});

test("máy chủ trả detail dạng chuỗi thì dùng nguyên văn", async () => {
  // Máy chủ viết thông báo tiếng Việt có ngữ cảnh ("Đơn này hiện không còn nhận
  // hồ sơ"). Thay nó bằng câu chung chung là vứt đi phần hữu ích nhất.
  const { api } = dung({
    dapAn: { ok: false, status: 409, body: { detail: "Đơn này hiện không còn nhận hồ sơ." } },
  });
  await assert.rejects(
    () => api.confirmProfile(PHIEN),
    (loi) => {
      assert.equal(loi.status, 409);
      assert.equal(loi.message, "Đơn này hiện không còn nhận hồ sơ.");
      return true;
    },
  );
});

test("detail dạng object mang theo danh sách ô còn thiếu", async () => {
  // Màn hình dùng `missing` để tô đúng những ô cần điền. Mất nó thì khách bị báo
  // "còn thiếu thông tin" mà không biết thiếu ở đâu.
  const { api } = dung({
    dapAn: {
      ok: false,
      status: 409,
      body: {
        detail: { message: "Hồ sơ còn thiếu vài mục.", missing: ["birth_year", "phone"] },
      },
    },
  });
  await assert.rejects(
    () => api.confirmProfile(PHIEN),
    (loi) => {
      assert.equal(loi.message, "Hồ sơ còn thiếu vài mục.");
      assert.deepEqual(loi.missing, ["birth_year", "phone"]);
      return true;
    },
  );
});

test("thân phản hồi lỗi không đọc được vẫn ra một câu dùng được", async () => {
  // Máy chủ 502 từ proxy trả về HTML, không phải JSON. Không bắt thì màn hình
  // hiện lỗi cú pháp JSON — vô nghĩa với người dùng.
  const { api } = dung({ dapAn: { ok: false, status: 502, khongDocDuoc: true } });
  await assert.rejects(
    () => api.fetchProfile(PHIEN),
    (loi) => {
      assert.equal(loi.status, 502);
      assert.ok(loi.message.length > 10);
      assert.ok(!/JSON|token/i.test(loi.message));
      return true;
    },
  );
});

test("204 không thân phản hồi thì không cố đọc JSON", async () => {
  const { api } = dung({ dapAn: { ok: true, status: 204, khongDocDuoc: true } });
  assert.equal(await api.fetchProfile(PHIEN), undefined);
});

// --- Đường dẫn của hệ tư vấn ---

test("bot tư vấn gọi tiền tố riêng /tu-van/v1, không lẫn với /public", async () => {
  // Hai hệ tách nhau: khóa riêng, hạn mức riêng, tiền tố riêng. Nhìn danh sách
  // đường là biết đâu là hệ chính, đâu là phụ trợ — và đổi hình dạng dữ liệu của
  // một bên không làm gãy bên kia.
  const { api, goi } = dung();
  await api.askAdvisor(PHIEN, "DH-0001", "đơn này lương bao nhiêu");
  await api.fetchAdvisorTurns(PHIEN, "DH-0001");
  for (const g of goi) {
    assert.match(g.url, /\/tu-van\/v1\//, `${g.url} không nằm dưới /tu-van/v1`);
  }
});

test("yêu cầu hỗ trợ đi đường công khai của hệ tư vấn", async () => {
  const { api, goi } = dung({ dapAn: { ok: true, status: 201, body: { code: "HT-1" } } });
  await api.sendSupportRequest(PHIEN, {
    kind: "gap_mat",
    full_name: "Nguyễn Thị Hoa",
    phone: "0912345678",
    message: "Em muốn gặp nhân viên",
  });
  assert.match(goi[0].url, /\/tu-van\/v1\/.*\/ho-tro$/);
  assert.equal(goi[0].method, "POST");
});

// --- Đọc ô hồ sơ ---

test("valueOf trả undefined khi chưa có ô, không trả null", async () => {
  // "Chưa có ô" và "ô có giá trị null" là hai chuyện khác nhau. Gộp lại thì màn
  // hình không phân biệt được "chưa hỏi" với "đã hỏi và không có".
  const { api } = dung();
  assert.equal(api.valueOf(undefined, "phone"), undefined);
  assert.equal(api.valueOf({}, "phone"), undefined);
  assert.equal(api.valueOf({ phone: { value: null } }, "phone"), null);
  assert.equal(api.valueOf({ phone: { value: "0912345678" } }, "phone"), "0912345678");
});

test("chưa có hồ sơ (404) là trạng thái bình thường, không phải lỗi", async () => {
  // Người vào lần đầu chưa có hồ sơ nào. Ném lỗi ở đây thì màn hình tư vấn hiện
  // một thông báo đỏ ngay khi khách vừa mở trang — trước cả khi họ làm gì.
  const { api } = dung({ dapAn: { ok: false, status: 404, body: { detail: "chưa có" } } });
  assert.equal(await api.fetchProfile(PHIEN), null);
});

test("nhưng 404 ở đường khác vẫn là lỗi", async () => {
  // Chỉ `fetchProfile` được nuốt 404. Nuốt ở mọi nơi thì một đường dẫn gõ sai
  // trông y như một câu trả lời hợp lệ.
  const { api } = dung({ dapAn: { ok: false, status: 404, body: { detail: "không thấy" } } });
  await assert.rejects(() => api.fetchMatches(PHIEN), (loi) => loi.status === 404);
});
