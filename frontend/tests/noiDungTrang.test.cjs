/**
 * Nội dung trang: thông tin liên lạc và các con số nói với khách.
 *
 * Hai nhóm tính chất, và cả hai đều thuộc loại **hỏng mà không ai thấy ngay**.
 *
 * ## Nhóm 1 — thông tin liên lạc không nằm trong kho mã
 *
 * Kho mã công khai. Số hotline là số của một người thật, địa chỉ văn phòng là địa
 * điểm thật. Ngày 29/09 tôi rút chúng ra khỏi nguồn, đưa vào `NEXT_PUBLIC_*`.
 *
 * Bên backend đã có `tests/test_khong_lo_lien_lac.py` quét nguồn Python. Nhưng
 * `content/site.ts` thì **logic**, không phải hằng số: nó đọc biến môi trường, và
 * chưa khai thì rơi về giá trị giả. Cái rơi ấy phải đúng — hiện số thật khi lẽ ra
 * phải hiện số giả là thứ không ai kiểm bằng mắt, vì nhìn nó vẫn "đúng".
 *
 * ## Nhóm 2 — các con số nói với khách
 *
 * Chi phí và điều kiện hiện trên trang là lời hứa với người đang tính chuyện vay
 * tiền đi nước ngoài. Chúng phải khớp với thứ backend nói, và phải nêu tổng chứ
 * không nêu từng chặng trơ trọi.
 */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

/**
 * Đưa một mảng từ hộp kín về realm của tệp kiểm thử.
 *
 * `vm.runInNewContext` tạo một realm riêng, nên mảng sinh trong đó có prototype
 * `Array` khác. `assert.deepStrictEqual` so cả prototype, nên nó từ chối với câu
 * "same structure but are not reference-equal" dù nội dung giống từng ký tự —
 * mất mười phút mới lần ra, vì thông báo lỗi in ra hai mảng trông y hệt nhau.
 */
const cungRealm = (mang) => Array.from(mang);

/** Nạp một module trong `content/` với biến môi trường tự đặt. */
function nap(ten, env = {}) {
  const context = { exports: {}, module: { exports: {} }, process: { env } };
  context.module.exports = context.exports;
  const nguon = fs.readFileSync(path.join(__dirname, `../content/${ten}.ts`), "utf8");
  vm.runInNewContext(
    ts.transpileModule(nguon, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
    }).outputText,
    context,
  );
  return context.exports;
}

const SO_THAT = "0971.716.939";

// --- Thông tin liên lạc ---

test("chưa khai cấu hình thì hiện số GIẢ, không hiện số thật", () => {
  // Ca quan trọng nhất của file. Nếu một ngày ai đó viết lại số thật làm giá trị
  // mặc định "cho tiện khi chạy máy mình", ca này đỏ ngay — còn nhìn bằng mắt thì
  // trang trông vẫn hoàn toàn bình thường.
  const { COMPANY } = nap("site", {});
  assert.equal(COMPANY.hotline, "0000.000.000");
  assert.notEqual(COMPANY.hotline, SO_THAT);
});

test("khai cấu hình thì dùng số thật", () => {
  const { COMPANY } = nap("site", { NEXT_PUBLIC_HOTLINE: SO_THAT });
  assert.equal(COMPANY.hotline, SO_THAT);
});

test("link gọi và mã Zalo dựng từ cùng một số, chỉ còn chữ số", () => {
  // Ba chỗ hiện số mà lấy từ ba nguồn thì sớm muộn chúng lệch nhau, và khách gọi
  // vào một số không có ai.
  const { COMPANY } = nap("site", { NEXT_PUBLIC_HOTLINE: SO_THAT });
  assert.equal(COMPANY.hotlineHref, "tel:0971716939");
  assert.equal(COMPANY.zalo, "0971716939");
});

test("chưa khai địa chỉ thì hiện câu mời liên hệ, không hiện chuỗi rỗng", () => {
  // Chuỗi rỗng để lại một thẻ văn phòng trống trơn — trông như trang hỏng. Câu
  // mời liên hệ thì nói rõ đây là thứ phải hỏi, không phải thứ bị mất.
  const { OFFICES, coDiaChiThat } = nap("site", {});
  assert.equal(OFFICES.length, 3);
  for (const vp of OFFICES) {
    assert.ok(vp.address.length > 10, "địa chỉ trống");
    assert.equal(coDiaChiThat(vp.address), false);
  }
});

test("khai địa chỉ nào thì đúng văn phòng ấy đổi", () => {
  const { OFFICES, coDiaChiThat } = nap("site", {
    NEXT_PUBLIC_OFFICE_HANOI_ADDRESS: "Số 1 Đường A",
  });
  assert.equal(OFFICES[0].address, "Số 1 Đường A");
  assert.equal(coDiaChiThat(OFFICES[0].address), true);
  // Hai văn phòng chưa khai vẫn là chỗ trống — không được lây giá trị của nhau.
  assert.equal(coDiaChiThat(OFFICES[1].address), false);
});

test("tên thành phố vẫn nằm trong kho mã", () => {
  // Cố ý giữ: tên thành phố có trên mọi giấy tờ giới thiệu và không chỉ tới một
  // địa điểm cụ thể nào. Chỉ số nhà và tên đường là phần rút ra ngoài.
  const { OFFICES } = nap("site", {});
  assert.deepEqual(
    cungRealm(OFFICES.map((v) => v.city)),
    ["Hà Nội", "TP. Hồ Chí Minh", "Bến Tre"],
  );
});

test("không tệp nội dung nào chứa số điện thoại thật", () => {
  // Quét thẳng nguồn, không qua module: một số thật lọt vào `pages.ts` hay
  // `faq.ts` thì `site.ts` có sạch cũng vô nghĩa.
  const thuMuc = path.join(__dirname, "../content");
  const lot = [];
  for (const ten of fs.readdirSync(thuMuc)) {
    const noiDung = fs.readFileSync(path.join(thuMuc, ten), "utf8");
    if (noiDung.includes("0971") || noiDung.includes("716939")) lot.push(ten);
  }
  assert.deepEqual(lot, [], `số thật còn trong: ${lot.join(", ")}`);
});

// --- Giờ liên hệ ---

test("giờ mời khách liên hệ gọn hơn giờ làm việc chính thức", () => {
  // `workingHours` có nghỉ trưa vì phần đặt lịch chặn đúng khoảng đó. Nhưng bắt
  // khách nhớ hai khoảng giờ rời nhau chỉ để gửi một câu hỏi là dựng một rào cản
  // không cần thiết.
  const { COMPANY } = nap("site", {});
  assert.match(COMPANY.contactHours, /8h.*17h/);
  assert.ok(
    COMPANY.contactHours.length < COMPANY.workingHours.length,
    "giờ mời liên hệ phải gọn hơn giờ làm việc chính thức",
  );
});

// --- Các con số nói với khách ---

test("trang chi phí nêu đủ ba chặng và tổng", () => {
  // Nói "35 triệu học tiếng" trơ trọi là để khách chuẩn bị sai số tiền. Ba chặng
  // 10 + 35 + 45 phải luôn đi kèm tổng 90.
  const nguon = fs.readFileSync(path.join(__dirname, "../content/pages.ts"), "utf8");
  for (const so of ["10", "35", "45", "90"]) {
    assert.ok(
      new RegExp(`\\b${so}\\b`).test(nguon),
      `trang chi phí thiếu con số ${so} triệu`,
    );
  }
});

test("trang điều kiện nói đúng 18–40 tuổi và không yêu cầu bằng cấp", () => {
  // Phải khớp `app/consultation/eligibility.py`. Hai chỗ nói hai điều khác nhau
  // thì khách đọc trang web một đằng, bot trả lời một nẻo.
  const nguon = fs.readFileSync(path.join(__dirname, "../content/pages.ts"), "utf8");
  assert.match(nguon, /18/);
  assert.match(nguon, /40/);
  assert.match(nguon, /không yêu cầu bằng cấp/i);
});
