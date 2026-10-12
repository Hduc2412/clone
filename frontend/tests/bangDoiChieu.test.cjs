// Bảng đối chiếu ✓ và cửa xác nhận hồ sơ (yêu cầu 08/10). Dựng component thật bằng
// JSX giả, mở cả component con viết trong cùng tệp; không gọi máy chủ.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const jsx = (type, props, key) => ({ type, props: props || {}, key });
const Fragment = Symbol('Fragment');

function load(file, extra = {}) {
  const react = { useState: initial => [typeof initial === 'function' ? initial() : initial, () => {}] };
  const modules = {
    react,
    'react/jsx-runtime': { jsx, jsxs: jsx, Fragment },
    'next/link': { __esModule: true, default: Object.assign(() => null, { displayName: 'Link' }) },
    ...extra,
  };
  const context = { exports: {}, require(name) {
    if (modules[name]) return modules[name];
    throw new Error(`Module chưa dựng: ${name}`);
  } };
  const source = fs.readFileSync(path.join(__dirname, '../components/candidate', file), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  return context.exports;
}

const Bang = load('BangDoiChieu.tsx');
const BangModule = { __esModule: true, ...Bang };

/** Mở mọi component hàm (trừ những cái giả có displayName) thành cây phần tử. */
function expand(tree) {
  if (tree == null || typeof tree === 'boolean') return tree;
  if (Array.isArray(tree)) return tree.map(expand);
  if (typeof tree !== 'object') return tree;
  if (typeof tree.type === 'function' && !tree.type.displayName) return expand(tree.type(tree.props));
  const children = tree.props.children;
  return { ...tree, props: { ...tree.props, children: children === undefined ? undefined : expand(children) } };
}
function nodes(tree) {
  if (tree == null || typeof tree === 'boolean') return [];
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (typeof tree !== 'object') return [tree];
  return [tree, ...nodes(tree.props.children)];
}
const text = tree => nodes(tree).filter(n => typeof n === 'string' || typeof n === 'number').join(' ').replace(/\s+/g, ' ').replace(/ ([:;,.])/g, '$1').trim();
const all = (tree, pred) => nodes(tree).filter(n => typeof n === 'object' && pred(n));
const cls = n => String(n.props.className || '');

const ROWS = [
  { key: 'japanese', label: 'Tiếng Nhật', requirement_text: 'Từ N4', candidate_text: 'N3', result: 'DAT', missing_field: null },
  { key: 'age', label: 'Độ tuổi', requirement_text: '20–35 tuổi', candidate_text: '', result: 'CHUA_RO', missing_field: 'birth_year' },
  { key: 'education', label: 'Bằng cấp', requirement_text: 'Cao đẳng điều dưỡng', candidate_text: 'Trung học phổ thông', result: 'KHONG_DAT', missing_field: null },
];
const SOFT = [
  { key: 'region', label: 'Khu vực', requirement_text: 'Tokyo', candidate_text: 'Kanto', points: 25, max_points: 40, outcome: 'region_match' },
  { key: 'salary', label: 'Lương', requirement_text: '180.000 yên', candidate_text: 'chưa nêu mức mong muốn', points: 0, max_points: 20, outcome: 'unknown', unknown_reasons: ['khach_chua_neu'], missing_field: 'salary_expectation_jpy' },
  // Đơn chưa công bố chi phí, khách đã nêu ngân sách: điểm trung lập theo luật `cost.unknown`.
  { key: 'cost', label: 'Chi phí', requirement_text: 'chưa rõ chi phí', candidate_text: 'khả năng 100.000.000 đ', points: 5, max_points: 10, outcome: 'unknown', unknown_reasons: ['don_chua_cong_bo'], missing_field: null },
];

const ve = props => expand(jsx(Bang.default, props));

test('nhật ký cũ không có unknown_reasons: suy từ chính dòng', () => {
  const cu = { key: 'cost', label: 'Chi phí', requirement_text: 'chưa rõ chi phí', candidate_text: 'chưa rõ khả năng',
               points: 5, max_points: 10, outcome: 'unknown', missing_field: 'budget_vnd' };
  assert.equal(JSON.stringify(Bang.lyDoChuaRo(cu)), JSON.stringify(['khach_chua_neu', 'don_chua_cong_bo']));
  assert.equal(Bang.lyDoChuaRo({ ...cu, outcome: 'within' }).length, 0);
});

test('dấu ✓ chỉ ở tiêu chí đạt; ô khác để trống nhưng có chữ ẩn', () => {
  const cay = ve({ rows: ROWS, eligible: false });
  const bang = all(cay, n => n.type === 'table')[0];
  const dong = all(bang, n => n.type === 'tr').slice(1); // bỏ dòng tiêu đề
  assert.equal(dong.length, ROWS.length);
  dong.forEach((tr, i) => {
    const o = all(tr, n => n.type === 'td').at(-1);
    const thay = all(o, n => n.type === 'span' && n.props['aria-hidden']).map(text).join('');
    const an = all(o, n => cls(n).includes('sr-only')).map(text).join('');
    if (ROWS[i].result === 'DAT') {
      assert.equal(thay, '✓');
      assert.equal(an, 'Đáp ứng');
    } else {
      assert.equal(thay, '', `dòng ${ROWS[i].key} không được có ký hiệu nhìn thấy`);
      assert.equal(an, 'Chưa đáp ứng hoặc chưa rõ');
    }
  });
  // Không còn nhãn ba màu cũ, không có dấu ✗ hay chữ "Đáp ứng" lặp lại ở phần nhìn thấy.
  assert.doesNotMatch(text(bang), /✗|Chưa đạt|Chưa rõ/);
});

test('chú thích đúng nguyên văn và nói rõ ✓ chưa phải nhân viên xác minh', () => {
  const chu = text(ve({ rows: ROWS, eligible: false }));
  assert.ok(chu.includes('✓: đáp ứng theo thông tin hiện có. Ô trống: chưa đáp ứng hoặc cần bổ sung; xem giải thích bên dưới.'));
  assert.match(chu, /chưa phải đã được nhân viên xác minh/);
});

test('thiếu thông tin thì ghi "Chưa cung cấp", không để ô trống', () => {
  const bang = all(ve({ rows: ROWS, eligible: false }), n => n.type === 'table')[0];
  const tuoi = all(bang, n => n.type === 'tr')[2];
  assert.equal(text(all(tuoi, n => n.type === 'td')[1]), 'Chưa cung cấp');
});

test('điện thoại: mỗi tiêu chí một thẻ, cùng dữ liệu và cùng quy tắc ✓, không kéo ngang', () => {
  const cay = ve({ rows: ROWS, eligible: false });
  const bang = all(cay, n => n.type === 'table')[0];
  assert.match(cls(bang), /\bhidden\b/); assert.match(cls(bang), /sm:table/);
  const the = all(cay, n => n.type === 'ul' && cls(n).includes('sm:hidden'))[0];
  const muc = all(the, n => n.type === 'li');
  assert.equal(muc.length, ROWS.length);
  muc.forEach((li, i) => {
    const chu = text(li);
    assert.ok(chu.includes(ROWS[i].label));
    assert.ok(chu.includes(ROWS[i].requirement_text));
    assert.ok(chu.includes(Bang.thongTinKhach(ROWS[i])));
    const thay = all(li, n => n.type === 'span' && n.props['aria-hidden']).map(text).join('');
    assert.equal(thay, ROWS[i].result === 'DAT' ? '✓' : '');
  });
  assert.equal(all(cay, n => /overflow-x-auto|min-w-\[/.test(cls(n))).length, 0);
});

test('tổng kết vẫn tách chưa đạt với chưa rõ bằng chữ', () => {
  const cay = ve({ rows: ROWS, eligible: false, questions: ['Bạn sinh năm nào?'] });
  const chu = text(cay);
  assert.match(chu, /3 tiêu chí bắt buộc: 1 đạt · 1 chưa đạt · 1 chưa rõ/);
  assert.match(chu, /Chưa đáp ứng: Bằng cấp — đơn: Cao đẳng điều dưỡng; hồ sơ: Trung học phổ thông/);
  assert.match(chu, /Cần bổ sung — chưa rõ, không phải là không đạt: Độ tuổi Bạn sinh năm nào\?/);
});

test('đơn chưa đạt điều kiện bắt buộc: không chấm, không hiện con số điểm', () => {
  const chu = text(ve({ rows: ROWS, eligible: false, score: 45, scoreRanked: true, softRows: SOFT }));
  assert.match(chu, /không chấm điểm nguyện vọng/);
  assert.doesNotMatch(chu, /45|\/ 100/);
});

test('chưa nêu nguyện vọng: không hiện điểm thấp gây hiểu nhầm', () => {
  const dat = ROWS.map(r => ({ ...r, result: 'DAT', candidate_text: r.candidate_text || '1999', missing_field: null }));
  const chu = text(ve({ rows: dat, eligible: true, score: 5, scoreRanked: false, softRows: SOFT }));
  assert.match(chu, /chưa có điểm để xếp/);
  assert.doesNotMatch(chu, /\b5\b|\/ 100/);
});

test('có điểm thì nói không phải khả năng trúng tuyển và giải thích từng phần', () => {
  const dat = ROWS.map(r => ({ ...r, result: 'DAT', candidate_text: r.candidate_text || '1999', missing_field: null }));
  const chu = text(ve({ rows: dat, eligible: true, score: 25, scoreRanked: true, softRows: SOFT }));
  assert.match(chu, /25 \/ 100/);
  assert.match(chu, /không phải khả năng trúng tuyển/);
  assert.match(chu, /Khu vực: Tokyo — bạn: Kanto \+ ?25 ?\/ ?40/);
  // Nguyện vọng chưa nêu không phải điểm mạnh: ghi chưa rõ, không mượn chữ của đơn.
  // Khách chưa nêu: ghi đúng là khách chưa nêu, không mượn chữ của đơn (08/10).
  assert.match(chu, /Lương: 180\.000 yên — bạn: Chưa cung cấp \+ ?0 ?\/ ?20 \(bạn chưa nêu lương mong muốn\)/);
  // Đơn chưa công bố: không phải "nguyện vọng chưa rõ", và 5 điểm là trung lập, không phải điểm mạnh.
  assert.match(chu, /Chi phí: đơn chưa công bố — bạn: khả năng 100\.000\.000 đ \+ ?5 ?\/ ?10 \(đơn chưa công bố chi phí — điểm trung lập vì chưa đủ dữ liệu để đánh giá, không phải điểm mạnh\)/);
  assert.doesNotMatch(chu, /chưa rõ nguyện vọng/);
});

// --- Cửa xác nhận ở phòng tư vấn theo đơn ---------------------------------

const Panel = load('OrderAdvicePanel.tsx', { '@/components/candidate/BangDoiChieu': BangModule });
const ADVICE = {
  branch: 'chua_phu_hop', branch_label: 'Chưa phù hợp', order_code: 'DH-0001', order_title: 'Điều dưỡng Tokyo',
  eligible: false, score: 0, can_register: false, profile_confirmed: true,
  blockers: [ROWS[2]], unknowns: [ROWS[1]], strengths: [ROWS[0]], rows: ROWS, soft_rows: [],
  questions: [], learning: null, learning_note: '', text: 'ĐOẠN PHÂN TÍCH', text_source: 'ghep_san',
  text_template: 'ĐOẠN PHÂN TÍCH', recommendation_log_code: 'RL-1', reused: false,
  suc_khoe: { benh_loai_tru: ['lao'], loi_nhac: '' },
};

test('hồ sơ chưa xác nhận: không bảng, không kết luận, mời xác nhận đúng đơn', () => {
  const cay = expand(jsx(Panel.default, { advice: { ...ADVICE, profile_confirmed: false } }));
  assert.equal(all(cay, n => n.type === 'table').length, 0);
  const chu = text(cay);
  assert.doesNotMatch(chu, /ĐOẠN PHÂN TÍCH|Chưa phù hợp|tiêu chí bắt buộc/);
  const link = all(cay, n => n.type?.displayName === 'Link')[0];
  assert.equal(link.props.href, '/tu-van?don=DH-0001');
});

test('đã xác nhận: bảng hiện sẵn theo đúng thứ tự engine, rồi mới tới phân tích', () => {
  const cay = expand(jsx(Panel.default, { advice: ADVICE }));
  const bang = all(cay, n => n.type === 'table')[0];
  assert.ok(bang, 'bảng phải hiện ngay, không cần bấm mở');
  const nhan = all(bang, n => n.type === 'th' && n.props.scope === 'row').map(text);
  assert.deepEqual(nhan, ROWS.map(r => r.label));
  const chu = text(cay);
  assert.ok(chu.indexOf('Bạn đáp ứng những gì?') < chu.indexOf('ĐOẠN PHÂN TÍCH'));
  // Điểm chuyển sang cột phải: bảng không còn khối điểm thứ hai.
  assert.equal((chu.match(/Điểm khớp nguyện vọng/g) || []).length, 0);
  assert.match(chu, /không chấm điểm nguyện vọng/);
});

// --- Phòng tư vấn hai cột (bản thiết kế 08/10) -------------------------------

test('thẻ điểm cột phải giữ đúng luật: không đạt thì không có số, có điểm thì nói không phải khả năng đậu', () => {
  const khong = text(expand(jsx(Bang.TheDiem, { eligible: false, score: 45, softRows: SOFT })));
  assert.doesNotMatch(khong, /45/);
  assert.match(khong, /không chấm điểm nguyện vọng/);
  const chuaNeu = text(expand(jsx(Bang.TheDiem, { eligible: true, score: 5, scoreRanked: false })));
  assert.doesNotMatch(chuaNeu, /\b5\b/);
  const co = text(expand(jsx(Bang.TheDiem, { eligible: true, score: 25, scoreRanked: true, softRows: SOFT })));
  assert.match(co, /25 \/ 100/);
  assert.match(co, /không phải khả năng trúng tuyển/);
  assert.match(co, /điểm trung lập vì chưa đủ dữ liệu để đánh giá, không phải điểm mạnh/);
});

test('bảng có anDiem thì không còn khối điểm, các dòng tiêu chí giữ nguyên', () => {
  const cay = ve({ rows: ROWS, eligible: true, score: 25, scoreRanked: true, softRows: SOFT, anDiem: true });
  assert.doesNotMatch(text(cay), /\/ 100|Điểm khớp nguyện vọng/);
  const nhan = all(all(cay, n => n.type === 'table')[0], n => n.type === 'th' && n.props.scope === 'row').map(text);
  assert.deepEqual(nhan, ROWS.map(r => r.label));
});

test('thẻ hồ sơ dùng nguyên nhãn tiếng Nhật máy chủ ghép, kể cả "chưa xác minh chứng chỉ"', () => {
  const profile = {
    fields: { full_name: { value: 'Nguyễn Thị Hoa' }, major: { value: 'Điều dưỡng' } },
    preferences: {}, labels: { education_level: 'Cao đẳng', desired_region_group: 'Kanto' },
    confirmed_at: '2026-10-08', missing_required: [],
    trang_thai_tieng_nhat: {
      muc: 'N5', ma: 'tu_khai', nhan: 'N5 — tự khai, chưa được đối chứng',
      chuong_trinh: { nhan: 'Hoàn thành chương trình N4 tại trung tâm — chưa xác minh chứng chỉ' },
    },
  };
  const chu = text(expand(jsx(Panel.TheHoSo, { profile, orderCode: 'DH-0001' })));
  assert.match(chu, /TH/);
  assert.match(chu, /N5 — tự khai, chưa được đối chứng/);
  assert.match(chu, /Hoàn thành chương trình N4 tại trung tâm — chưa xác minh chứng chỉ/);
  assert.match(chu, /Kinh nghiệm Chưa cung cấp/);
  assert.equal(Panel.chuDauTen(''), '?');
});

// --- Thanh bước ------------------------------------------------------------

test('thanh bước đi theo trạng thái thật của hồ sơ', () => {
  const Buoc = load('BuocTuVan.tsx');
  assert.equal(Buoc.BUOC.length, 6);
  assert.equal(Buoc.buocHienTai({ coHoSo: false, daXacNhan: false, coKetQua: false }), 0);
  assert.equal(Buoc.buocHienTai({ coHoSo: true, daXacNhan: false, coKetQua: false }), 1);
  assert.equal(Buoc.buocHienTai({ coHoSo: true, daXacNhan: true, coKetQua: false }), 2);
  // Có kết quả cũ mà hồ sơ chưa xác nhận lại thì chưa được tính là đã tới bảng đối chiếu.
  assert.equal(Buoc.buocHienTai({ coHoSo: true, daXacNhan: false, coKetQua: true }), 1);
  assert.equal(Buoc.buocHienTai({ coHoSo: true, daXacNhan: true, coKetQua: true }), 3);
  const cay = expand(jsx(Buoc.default, { hienTai: 3 }));
  const dangO = all(cay, n => n.type === 'li' && n.props['aria-current'] === 'step');
  assert.equal(dangO.length, 1);
  assert.match(text(dangO[0]), /Đối chiếu với đơn/);
});

// --- Thẻ đơn: nguyện vọng lệch không phải "còn thiếu" (08/10) -----------------

test('thẻ đơn gọi nguyện vọng lệch là "khác nguyện vọng", không phải "còn thiếu"', () => {
  const gia = (ten) => Object.assign(() => null, { displayName: ten });
  const Card = load('MatchCard.tsx', {
    '@/components/ui/primitives': { Badge: gia('Badge'), Button: gia('Button'), Card: gia('Card') },
    '@/lib/candidateApi': {},
    '@/lib/format': { daysUntil: () => 30, formatDate: (d) => d },
    '@/components/candidate/BangDoiChieu': BangModule,
  });
  const item = {
    code: 'DH-0007', title: 'Hộ lý Kobe', employer_name: 'Kobe Midori', prefecture: 'Hyogo',
    employer_type: 'vien_duong_lao', program: 'thuc_tap_sinh', deadline: '2026-12-01', eligible: true,
    score: 30, rank: 2, score_ranked: true, labels: {}, explanation_text: 'Giải thích.', explanation_block: '',
    gaps: ['Khu vực: khu vực Hyogo, mong muốn vùng Kantō.'],
    hard_rows: ROWS.map((r) => ({ ...r, result: 'DAT' })),
    soft_rows: [{ key: 'region', label: 'Khu vực', requirement_text: 'khu vực Hyogo', candidate_text: 'mong muốn vùng Kantō',
                  points: 0, max_points: 40, outcome: 'different' }],
  };
  const chu = text(expand(jsx(Card.default, { item })));
  assert.doesNotMatch(chu, /Còn thiếu/);
  assert.match(chu, /Khác nguyện vọng của bạn: Khu vực: đơn khu vực Hyogo, bạn mong muốn vùng Kantō/);
});
