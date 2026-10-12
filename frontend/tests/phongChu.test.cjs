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

test('phông có chân được nạp kèm bộ chữ tiếng Việt và gắn vào <html>', () => {
  const layout = fs.readFileSync(path.join(GOC, 'app', 'layout.tsx'), 'utf8');
  const khoi = layout.slice(layout.indexOf('const gelasio'), layout.indexOf('});', layout.indexOf('const gelasio')));
  assert.match(khoi, /subsets:\s*\[[^\]]*"vietnamese"/);
  assert.match(khoi, /variable:\s*"--font-serif"/);
  assert.match(layout, /className=\{`\$\{beVietnamPro\.variable\} \$\{gelasio\.variable\}`\}/);
});
