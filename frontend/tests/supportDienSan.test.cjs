// Biểu mẫu "Nói chuyện với nhân viên" điền sẵn họ tên và số điện thoại từ hồ sơ (12/10).
// Kiểm trình duyệt 12/10: khách vừa khai hồ sơ xong lại phải gõ lại hai ô này.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function dung(props) {
  let cursor = 0;
  const values = [];
  const react = {
    useState(initial) {
      const i = cursor++;
      if (!(i in values)) values[i] = typeof initial === 'function' ? initial() : initial;
      return [values[i], () => {}];
    },
  };
  const jsx = (type, p) => ({ type, props: p || {} });
  const context = { exports: {}, require(ten) {
    if (ten === 'react') return react;
    if (ten === 'react/jsx-runtime') return { jsx, jsxs: jsx, Fragment: 'Fragment' };
    if (ten === '@/content/site') return { COMPANY: { phone: '0971716939', phoneDisplay: '0971.716.939', hours: '' } };
    if (ten === '@/lib/candidateApi') return { sendSupportRequest: async () => ({}) };
    throw new Error(`Module chưa dựng: ${ten}`);
  } };
  const nguon = fs.readFileSync(path.join(__dirname, '..', 'components', 'candidate', 'SupportRequestForm.tsx'), 'utf8');
  vm.runInNewContext(ts.transpileModule(nguon, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  return context.exports.default(props);
}

function oNhap(cay, ten) {
  const ra = [];
  (function di(n) {
    if (!n || typeof n !== 'object') return;
    if (Array.isArray(n)) return n.forEach(di);
    if (n.type === 'input' && n.props.name === ten) ra.push(n);
    di(n.props && n.props.children);
  })(cay);
  return ra[0];
}

test('có hồ sơ thì họ tên và số điện thoại được điền sẵn', () => {
  const cay = dung({ sessionId: 's', hoSo: { fields: {
    full_name: { value: 'Lê Thị Kiểm Thử' }, phone: { value: '0900000123' } } } });
  assert.equal(oNhap(cay, 'full_name').props.defaultValue, 'Lê Thị Kiểm Thử');
  assert.equal(oNhap(cay, 'phone').props.defaultValue, '0900000123');
});

test('không có hồ sơ thì để trống, không in "undefined"', () => {
  const cay = dung({ sessionId: 's' });
  assert.equal(oNhap(cay, 'full_name').props.defaultValue, '');
  assert.equal(oNhap(cay, 'phone').props.defaultValue, '');
});

test('phòng tư vấn truyền hồ sơ vào mọi chỗ gọi biểu mẫu', () => {
  const nguon = fs.readFileSync(path.join(__dirname, '..', 'components', 'candidate', 'OrderConsultationRoom.tsx'), 'utf8');
  const cho = nguon.match(/<SupportRequestForm[\s\S]*?\/>/g) || [];
  assert.ok(cho.length >= 2, `chỉ thấy ${cho.length} chỗ gọi`);
  for (const c of cho) assert.match(c, /hoSo=\{hoSo\}/, `thiếu hoSo: ${c.slice(0, 80)}`);
});
