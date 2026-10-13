// Trang Hỏi đáp phải nói cùng một điều với trang Chi phí, Quy trình và với dữ liệu giao
// cho trợ lý tư vấn (13/10). Đo mô hình thật 13/10: trợ lý nói "khám sức khỏe miễn phí",
// "học 6–7 tháng", "trọn gói 90 triệu" — đúng theo kho tri thức — trong khi `faq.ts` ghi
// khám là khoản "không hoàn lại", học "bốn đến tám tháng", chi phí "khác nhau theo diện".
// Chủ đồ án chốt: theo kho tri thức.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const doc = (...p) => fs.readFileSync(path.join(__dirname, '..', ...p), 'utf8');
const FAQ = doc('content', 'faq.ts');
const PAGES = doc('content', 'pages.ts');
const TRO_LY = fs.readFileSync(path.join(__dirname, '..', '..', 'backend', 'app', 'consultation', 'eligibility.py'), 'utf8');

test('ba nguồn cùng một con số: 90 triệu, 6–7 tháng, khám không mất tiền', () => {
  for (const [ten, nguon] of [['faq.ts', FAQ], ['pages.ts', PAGES]]) {
    assert.match(nguon, /90 triệu/, `${ten} thiếu tổng 90 triệu`);
    assert.match(nguon, /6[–-]7 tháng|6 đến 7 tháng/, `${ten} thiếu thời gian học 6–7 tháng`);
    assert.match(nguon, /[Kk]hám[^".]*không mất tiền|Không mất tiền/, `${ten} thiếu "khám không mất tiền"`);
  }
  assert.match(TRO_LY, /KHÔNG mất tiền/, 'dữ liệu của trợ lý đổi chính sách khám mà trang web không đổi theo');
});

test('trang Hỏi đáp không còn các câu đã lệch', () => {
  for (const cu of [/bốn đến tám tháng/, /khác nhau theo từng diện/, /Phí dịch vụ chỉ thu/, /khám sức khỏe hay học phí đã học thì không hoàn lại/]) {
    assert.doesNotMatch(FAQ, cu);
  }
});
