// Chữ có chân phải đi qua phông tự nạp có bộ tiếng Việt, không đứng đầu bằng Georgia (12/10).
//
// Georgia trên Windows thiếu chữ hai dấu ("ắ", "ầ", "ặ"…): trình duyệt tách thành chữ gốc
// + dấu rời, đặt dấu lệch — "Bắt đầu" hiện thành "Bă´t đâ`u" trên trang chủ. Georgia chỉ
// được đứng SAU `var(--font-serif…)` làm dự phòng.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const GOC = path.join(__dirname, '..');

function tep(thuMuc, duoi) {
  const ra = [];
  for (const ten of fs.readdirSync(path.join(GOC, thuMuc), { withFileTypes: true })) {
    const p = path.join(thuMuc, ten.name);
    if (ten.isDirectory()) ra.push(...tep(p, duoi));
    else if (duoi.some((d) => ten.name.endsWith(d))) ra.push(p);
  }
  return ra;
}

test('không chỗ nào để Georgia đứng đầu danh sách phông', () => {
  const sai = [];
  for (const p of [...tep('app', ['.tsx', '.css']), ...tep('components', ['.tsx'])]) {
    const nguon = fs.readFileSync(path.join(GOC, p), 'utf8');
    // font-family: Georgia… (CSS)  |  fontFamily: "Georgia…" (style trong JSX)
    if (/font-family:\s*["']?Georgia/i.test(nguon) || /fontFamily:\s*["'`]Georgia/.test(nguon)) sai.push(p);
  }
  assert.deepEqual(sai, [], `Georgia đứng đầu ở: ${sai.join(', ')}`);
});


// Phông tự phục vụ (12/10): build không còn tải từ Google. Kiểm: không còn `next/font/google`;
// `phong-chu.css` chỉ trỏ tệp trong `public/fonts` và mọi tệp ấy có thật; có bộ chữ tiếng Việt
// cho cả hai phông; có giấy phép OFL đi kèm.
function kiemPhongTuPhucVu(GOC) {
  const layout = fs.readFileSync(path.join(GOC, 'app', 'layout.tsx'), 'utf8');
  assert.doesNotMatch(layout, /from ["']next\/font\/google["']/, 'còn tải phông từ Google lúc build');
  assert.match(layout, /import ["']\.\/phong-chu\.css["']/);
  const css = fs.readFileSync(path.join(GOC, 'app', 'phong-chu.css'), 'utf8');
  assert.doesNotMatch(css, /fonts\.(googleapis|gstatic)\.com/, 'CSS phông còn trỏ ra Google');
  const tep = [...css.matchAll(/url\(\/fonts\/([^)]+)\)/g)].map((m) => m[1]);
  assert.ok(tep.length >= 24, `chỉ thấy ${tep.length} tệp phông`);
  for (const t of tep) assert.ok(fs.existsSync(path.join(GOC, 'public', 'fonts', t)), `thiếu tệp ${t}`);
  for (const ho of ['Be Vietnam Pro', 'Gelasio']) {
    assert.match(css, new RegExp(`/\\* ${ho} \\d+ \\w+ — vietnamese \\*/`), `${ho} thiếu bộ chữ tiếng Việt`);
  }
  assert.match(css, /--font-sans: 'Be Vietnam Pro'/);
  assert.match(css, /--font-serif: 'Gelasio'/);
  assert.match(fs.readFileSync(path.join(GOC, 'public', 'fonts', 'OFL.txt'), 'utf8'), /SIL Open Font License/);
}

test('phông tự phục vụ: không tải từ Google lúc build, đủ tệp, có bộ tiếng Việt', () => {
  kiemPhongTuPhucVu(GOC);
});
