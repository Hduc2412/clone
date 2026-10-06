// Kiểm hành vi component bằng hook harness và API giả; không gọi AI/DB thật.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const state = {
  stage_label: 'Kiểm tra hồ sơ', eligible_count: null, turns: [],
  suggested_questions: [], next_best_action: { type: 'none', label: '', target: null },
};

function load(file, api, { strict = false } = {}) {
  let cursor = 0, effectCursor = 0;
  const values = [], effects = [], pending = [];
  const react = {
    useState(initial) {
      const i = cursor++;
      if (!(i in values)) values[i] = typeof initial === 'function' ? initial() : initial;
      return [values[i], next => { values[i] = typeof next === 'function' ? next(values[i]) : next; }];
    },
    useRef(initial) {
      const i = cursor++;
      if (!(i in values)) values[i] = { current: initial };
      return values[i];
    },
    useCallback: fn => fn,
    useMemo: fn => fn(),
    useEffect(fn, deps) {
      const i = effectCursor++;
      const prev = effects[i];
      if (!prev || deps.some((d, j) => d !== prev.deps[j])) {
        prev?.cleanup?.();
        effects[i] = { deps };
        pending.push(() => {
          effects[i].cleanup = fn();
          // React StrictMode (dev) cố ý chạy effect, dọn, rồi chạy lại. Mô phỏng đúng
          // chuyện đó để đo được lượt mở đầu có bị gọi hai lần không.
          if (strict) { effects[i].cleanup?.(); effects[i].cleanup = fn(); }
        });
      }
    },
  };
  const jsx = (type, props, key) => ({ type, props: props || {}, key });
  const component = name => Object.assign(() => null, { displayName: name });
  const modules = {
    react,
    'react/jsx-runtime': { jsx, jsxs: jsx },
    '@/lib/candidateApi': api,
    '@/components/ui/primitives': Object.fromEntries(['Card', 'Badge', 'Button'].map(n => [n, component(n)])),
    '@/components/candidate/fields': Object.fromEntries(['TextField', 'SelectField', 'NumberField', 'TriStateField'].map(n => [n, component(n)])),
  };
  const context = { exports: {}, Error, window: { scrollTo() {} }, require(name) {
    if (modules[name]) return modules[name];
    // Không dựng các component con; giữ node để kiểm đúng prop/callback nối luồng.
    if (name === 'next/link' || name.startsWith('@/components/') || name === './AdvisorChat') {
      return { __esModule: true, default: component(name.split('/').at(-1)) };
    }
    throw new Error(`Module chưa dựng: ${name}`);
  } };
  const source = fs.readFileSync(path.join(__dirname, '../components/candidate', file), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  return {
    component: context.exports.default,
    render(fn, props) { cursor = 0; effectCursor = 0; return fn(props); },
    async flush() {
      pending.splice(0).forEach(fn => fn());
      for (let i = 0; i < 4; i++) await new Promise(resolve => setImmediate(resolve));
    },
    unmount() { effects.forEach(e => e.cleanup?.()); },
  };
}

function nodes(tree) {
  if (tree == null || typeof tree === 'boolean') return [];
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (typeof tree !== 'object') return [tree];
  return [tree, ...nodes(tree.props.children)];
}
const text = tree => nodes(tree).filter(n => typeof n === 'string' || typeof n === 'number').join(' ');
const find = (tree, type) => nodes(tree).find(n => n.type === type);

async function chat(overrides = {}, props = {}, opts = {}) {
  const calls = [];
  const api = {
    openAgentTurn: async (...args) => { calls.push(['open', ...args]); return state; },
    fetchAgentState: async () => state,
    fetchAdvisorTurns: async (...args) => { calls.push(['history', ...args]); return { items: [] }; },
    askAgent: async (...args) => { calls.push(['agent', ...args]); return {
      ...state, question: args[1], answer: 'Trả lời hồ sơ', source: 'mo_hinh',
      facts_to_save: [{ field: 'experience_years', value: 2 }], suggested_action: null,
    }; },
    askAdvisor: async (...args) => { calls.push(['order', ...args]); return {
      question: args[2], answer: 'Trả lời đúng đơn', source: 'mo_hinh',
    }; },
    confirmAgentFact: async (...args) => { calls.push(['confirm', ...args]); },
    ...overrides,
  };
  const h = load('AdvisorChat.tsx', api, opts);
  const p = { sessionId: 'session-a', ...props };
  const wrapper = h.component(p);
  const render = () => h.render(wrapper.type, wrapper.props);
  render(); await h.flush();
  async function ask(question) {
    find(render(), 'input').props.onChange({ target: { value: question } });
    find(render(), 'form').props.onSubmit({ preventDefault() {} });
    await h.flush();
    return render();
  }
  return { h, calls, render, ask, wrapper };
}

test('sau CV: mở tư vấn hồ sơ, không gọi đường theo đơn', async () => {
  const c = await chat();
  assert.deepEqual(c.calls, [['open', 'session-a', 'sau_cv']]);
  assert.match(text(c.render()), /Tư vấn theo hồ sơ/);
  // Chưa đối chiếu không được gợi câu hỏi sai tiền đề "vì sao chưa đạt".
  const suggestions = nodes(c.render()).find(n => typeof n.type === 'function' && n.props.cac)?.props.cac;
  assert.ok(suggestions.includes('Hồ sơ em còn thiếu thông tin gì?'));
});

test('theo đơn: dùng đúng mã đơn cho lịch sử và câu hỏi', async () => {
  const c = await chat({}, { orderCode: 'DH-0002' });
  const tree = await c.ask(' Em còn thiếu gì? ');
  assert.deepEqual(c.calls, [
    ['history', 'session-a', 'DH-0002'], ['order', 'session-a', 'DH-0002', 'Em còn thiếu gì?'],
  ]);
  assert.match(text(tree), /Trả lời đúng đơn/);
  assert.doesNotMatch(text(tree), /Trợ lý nghe được/);
});

test('thông tin trong hội thoại chỉ lưu khi khách bấm xác nhận', async () => {
  let refreshed = 0;
  const c = await chat({}, { onProfileChanged: () => { refreshed++; } });
  const tree = await c.ask('Em làm hai năm');
  assert.equal(c.calls.filter(x => x[0] === 'confirm').length, 0);
  assert.match(text(tree), /chưa được lưu/);
  const confirm = nodes(tree).find(n => n.type === 'button' && text(n) === 'Đúng, lưu lại');
  await confirm.props.onClick(); await c.h.flush();
  assert.deepEqual(c.calls.at(-1), ['confirm', 'session-a', 'experience_years', 2]);
  assert.equal(refreshed, 1);
  assert.doesNotMatch(text(c.render()), /Trợ lý nghe được/);
});

test('đề xuất mang mã danh mục: hiện nhãn tiếng Việt, gửi lên vẫn là mã', async () => {
  // Kiểm trên trình duyệt 06/10: câu xác nhận hiện "Loại hình: vien_duong_lao".
  const c = await chat({
    askAgent: async (...args) => { c.calls.push(['agent', ...args]); return {
      ...state, question: args[1], answer: 'Ghi nhận', source: 'mo_hinh',
      facts_to_save: [{ field: 'desired_employer_type', value: 'vien_duong_lao', value_label: 'Viện dưỡng lão' }],
      suggested_action: null,
    }; },
  });
  const tree = await c.ask('Em muốn làm viện dưỡng lão');
  assert.match(text(tree), /Viện dưỡng lão/);
  assert.doesNotMatch(text(tree), /vien_duong_lao/);
  const confirm = nodes(tree).find(n => n.type === 'button' && text(n) === 'Đúng, lưu lại');
  await confirm.props.onClick(); await c.h.flush();
  assert.deepEqual(c.calls.at(-1), ['confirm', 'session-a', 'desired_employer_type', 'vien_duong_lao']);
});

test('bấm Không đúng không ghi hồ sơ', async () => {
  const c = await chat();
  const tree = await c.ask('Em làm hai năm');
  nodes(tree).find(n => n.type === 'button' && text(n) === 'Không đúng').props.onClick();
  assert.equal(c.calls.filter(x => x[0] === 'confirm').length, 0);
  assert.doesNotMatch(text(c.render()), /Trợ lý nghe được/);
});

test('lỗi API giữ câu hỏi để khách thử lại', async () => {
  const c = await chat({ askAdvisor: async () => { throw new Error('Đang mất kết nối'); } }, { orderCode: 'DH-0002' });
  const tree = await c.ask('Câu hỏi chưa gửi');
  assert.match(text(tree), /Đang mất kết nối/);
  assert.equal(find(tree, 'input').props.value, 'Câu hỏi chưa gửi');
});

test('đổi phiên hoặc đơn: khóa remount khác, không lẫn lịch sử và đề xuất', () => {
  const h = load('AdvisorChat.tsx', {});
  const keys = [
    { sessionId: 's' }, { sessionId: 's', orderCode: 'A' },
    { sessionId: 's', orderCode: 'B' }, { sessionId: 'other', orderCode: 'A' },
  ].map(p => h.component(p).key);
  assert.equal(new Set(keys).size, 4);
  assert.equal(h.component({ sessionId: 's', moc: 'sau_cv' }).key,
    h.component({ sessionId: 's', moc: 'sau_matching' }).key);
});

test('đổi màn hình lúc đang hỏi: không đưa câu trả lời cũ vào khung mới', async () => {
  let resolve;
  const c = await chat({ askAdvisor: () => new Promise(r => { resolve = r; }) }, { orderCode: 'A' });
  await c.ask('Hỏi đơn A');
  c.h.unmount();
  resolve({ question: 'Hỏi đơn A', answer: 'Dữ liệu cũ', source: 'mo_hinh' });
  await c.h.flush();
  assert.doesNotMatch(text(c.render()), /Dữ liệu cũ/);
});

test('nối luồng: upload đọc CV xong mới hiện AdvisorChat, biểu mẫu mặc định thu gọn', async () => {
  const api = {
    ensureSessionId: async () => 's', fetchProfile: async () => null,
    fetchProfileMeta: async () => ({}), fetchMyRegistrations: async () => ({ items: [] }),
    valueOf: (section, key) => section[key]?.value,
  };
  const h = load('ConsultationFlow.tsx', api);
  const render = () => h.render(h.component, {});
  render(); await h.flush();
  let tree = render();
  assert.equal(nodes(tree).filter(n => n.type?.displayName === 'AdvisorChat').length, 0);
  assert.equal(find(tree, 'details').props.open, false);
  const cv = nodes(tree).find(n => n.type?.displayName === 'CvUpload');
  cv.props.onProfileRead({ fields: {}, preferences: {}, status: 'draft', version: 1 });
  tree = render();
  const panel = nodes(tree).filter(n => n.type?.displayName === 'AdvisorChat');
  assert.equal(panel.length, 1);
  assert.equal(panel[0].props.sessionId, 's');
  assert.equal(panel[0].props.moc, 'sau_cv');
  assert.match(text(tree), /Xác nhận hồ sơ và xem đơn phù hợp/);
});

// --- Lượt mở đầu: lỗi mạng, thử lại, không gọi trùng -------------------------
//
// Bản trước bật cờ "đã mở đầu" TRƯỚC khi gọi: gọi hỏng một lần là trong cùng lần
// hiển thị không bao giờ gọi lại, khách chỉ thấy một dòng lỗi. Chủ đồ án yêu cầu
// sửa trước commit ngày 06/10: phân biệt đang gọi / đã thành công, có nút thử
// lại, và không tạo trùng lượt mở đầu.

const nutThuLai = tree => nodes(tree).find(n => n.type === 'button' && /Thử lại/.test(text(n)));

function hoan() {
  let xong, hong;
  const p = new Promise((a, b) => { xong = a; hong = b; });
  return { p, xong, hong };
}

test('mở đầu hỏng: hiện lỗi kèm nút Thử lại; bấm thì gọi lại và vào được phòng', async () => {
  let lan = 0;
  const c = await chat({
    openAgentTurn: async () => {
      lan += 1;
      if (lan === 1) throw new Error('Không kết nối được máy chủ.');
      return state;
    },
    fetchAgentState: async () => ({ ...state, turns: [{ question: '[hệ thống] sau_cv', answer: 'Mình đã đọc CV của bạn.', source: 'mo_hinh' }] }),
  });
  let cay = c.render();
  assert.match(text(cay), /Không kết nối được máy chủ/);
  assert.ok(nutThuLai(cay), 'không có nút Thử lại sau khi mở đầu hỏng');

  nutThuLai(cay).props.onClick();
  c.render(); await c.h.flush();
  cay = c.render();
  assert.equal(lan, 2, 'bấm Thử lại không gọi lại lượt mở đầu');
  assert.match(text(cay), /Mình đã đọc CV của bạn/);
  assert.doesNotMatch(text(cay), /Không kết nối được máy chủ/);
  assert.equal(nutThuLai(cay), undefined, 'thành công rồi mà nút Thử lại còn đó');
});

test('mở đầu thành công nhưng nạp lịch sử hỏng: thử lại KHÔNG gọi mở đầu lần hai', async () => {
  let mo = 0, nap = 0;
  const c = await chat({
    openAgentTurn: async () => { mo += 1; return state; },
    fetchAgentState: async () => { nap += 1; if (nap === 1) throw new Error('Mất kết nối.'); return state; },
  });
  nutThuLai(c.render()).props.onClick();
  c.render(); await c.h.flush();
  assert.equal(mo, 1, 'lượt mở đầu bị gọi lại dù lần đầu đã ghi thành công');
  assert.equal(nap, 2);
  assert.equal(nutThuLai(c.render()), undefined);
});

test('StrictMode chạy effect hai lần trong lúc đang gọi: chỉ MỘT lời gọi mở đầu', async () => {
  const cho = hoan();
  let mo = 0;
  const c = await chat({ openAgentTurn: () => { mo += 1; return cho.p; } }, {}, { strict: true });
  assert.match(text(c.render()), /đang mở phòng tư vấn/, 'đang gọi mà không báo gì');
  cho.xong(state);
  await c.h.flush();
  assert.equal(mo, 1, 'StrictMode làm lượt mở đầu bị gọi hai lần — máy chủ có thể ghi trùng');
  assert.doesNotMatch(text(c.render()), /đang mở phòng tư vấn/);
});

test('lỗi một câu hỏi KHÔNG hiện nút Thử lại của lần nạp — câu ấy đã nằm lại trong ô nhập', async () => {
  const c = await chat({ askAgent: async () => { throw new Error('Chưa gửi được câu hỏi.'); } });
  const cay = await c.ask('Em còn thiếu gì?');
  assert.match(text(cay), /Chưa gửi được câu hỏi/);
  assert.equal(nutThuLai(cay), undefined);
  assert.equal(find(cay, 'input').props.value, 'Em còn thiếu gì?');
});

// --- Khởi động và "Khai lại từ đầu": mã phiên rỗng, bộ nhớ trình duyệt bị chặn ---
//
// `ensureSessionId` tự bắt lỗi MẠNG — mất mạng không làm nó ném. Hai chỗ hỏng
// thật, đo được bằng cách đọc hàm ấy ngày 06/10:
// - máy chủ không trả lời và trong máy chưa có mã → nó trả CHUỖI RỖNG;
// - trình duyệt chặn `localStorage` → nó NÉM (chỗ chạm bộ nhớ nằm ngoài try).

function luong(api) {
  const h = load('ConsultationFlow.tsx', {
    fetchProfile: async () => null, fetchProfileMeta: async () => ({}),
    fetchMyRegistrations: async () => ({ items: [] }), valueOf: (s, k) => s[k]?.value,
    ...api,
  });
  const render = () => h.render(h.component, {});
  return { h, render };
}
const nutTen = (tree, ten) => nodes(tree).find(n => n.type?.displayName === 'Button' && text(n).includes(ten));

test('khởi động: mã phiên rỗng thì KHÔNG gọi API với mã rỗng, và nói rõ chưa mở được phiên', async () => {
  const goi = [];
  const { h, render } = luong({
    ensureSessionId: async () => '',
    fetchProfile: async (sid) => { goi.push(sid); return null; },
  });
  render(); await h.flush();
  const cay = render();
  assert.deepEqual(goi, [], `đã gọi fetchProfile với mã ${JSON.stringify(goi)}`);
  assert.match(text(cay), /Chưa mở được phiên tư vấn/);
  assert.ok(nutTen(cay, 'Thử lại'), 'không có đường thử lại');
  assert.doesNotMatch(text(cay), /Đang tải biểu mẫu/);
});

test('khởi động: trình duyệt chặn bộ nhớ (ensureSessionId ném) thì KHÔNG treo ở "Đang tải"', async () => {
  const { h, render } = luong({
    ensureSessionId: async () => { throw new Error('The operation is insecure.'); },
  });
  render(); await h.flush();
  const cay = render();
  assert.doesNotMatch(text(cay), /Đang tải biểu mẫu/, 'trang treo ở màn hình tải');
  assert.ok(nutTen(cay, 'Thử lại'));
});

test('"Khai lại từ đầu" mà không mở được phiên mới: GIỮ màn hình, báo lỗi; mở được thì mới xóa', async () => {
  const hoSo = { code: 'UV-1', fields: {}, preferences: {}, status: 'confirmed', version: 1, labels: {} };
  let moiTra = '';
  const { h, render } = luong({
    ensureSessionId: async () => 's',
    fetchProfile: async () => hoSo,
    fetchMatches: async () => ({ matches: [], eligible_count: 0, total_considered: 0, missing_info: [], disclaimer: '' }),
    resetSession: async () => moiTra,
  });
  render(); await h.flush();
  let cay = render();
  nutTen(cay, 'Khai lại từ đầu').props.onClick();
  await h.flush();
  cay = render();
  assert.match(text(cay), /Chưa mở được phiên tư vấn/);
  assert.ok(nutTen(cay, 'Khai lại từ đầu'), 'màn hình kết quả bị xóa dù chưa có phiên mới');
  // Câu báo chỉ đúng nút có trên màn hình. Kiểm trên trình duyệt 06/10: câu cũ bảo
  // "bấm Thử lại" mà màn hình này không có nút "Thử lại" nào.
  assert.equal(nutTen(cay, 'Thử lại'), undefined);
  assert.doesNotMatch(text(cay), /bấm Thử lại/);
  assert.match(text(cay), /bấm lại “Khai lại từ đầu”/);

  moiTra = 's2';
  nutTen(cay, 'Khai lại từ đầu').props.onClick();
  await h.flush();
  cay = render();
  assert.equal(nutTen(cay, 'Khai lại từ đầu'), undefined, 'có phiên mới mà vẫn ở màn hình cũ');
  assert.doesNotMatch(text(cay), /Chưa mở được phiên tư vấn/);
});

class ApiError extends Error {}

test('đăng ký một đơn thất bại ở bước kết quả: khách PHẢI thấy lời báo', async () => {
  // Lỗi có từ trước 06/10: `register()` báo qua `setError`, nhưng bước kết quả
  // không vẽ `error` — đăng ký hỏng là màn hình đứng im. Lộ ra khi viết ca cho
  // "Khai lại từ đầu", vì hai việc dùng chung đúng chỗ thiếu ấy.
  const hoSo = { code: 'UV-1', fields: {}, preferences: {}, status: 'confirmed', version: 1, labels: {} };
  const { h, render } = luong({
    ensureSessionId: async () => 's',
    getSessionId: () => 's',
    fetchProfile: async () => hoSo,
    fetchMatches: async () => ({
      matches: [{ code: 'DH-0001', eligible: true }], eligible_count: 1, total_considered: 1,
      missing_info: [], disclaimer: '',
    }),
    ApiError,
    registerForOrder: async () => { throw new ApiError('Đơn này vừa hết hạn nộp hồ sơ.'); },
  });
  render(); await h.flush();
  const the = nodes(render()).find(n => n.type?.displayName === 'MatchCard');
  assert.ok(the, 'không thấy thẻ đơn ở bước kết quả');
  await the.props.onRegister('DH-0001');
  await h.flush();
  assert.match(text(render()), /Đơn này vừa hết hạn nộp hồ sơ/);
});

test('bước kết quả nói ngay cạnh danh sách: thiếu thông tin không loại đơn, nguyện vọng chỉ xếp thứ tự', async () => {
  // Hai quy tắc này từng nằm xa chỗ khách đọc kết quả (thẻ cuối trang và biểu
  // mẫu thu gọn). Ghim lại để không ai lặng lẽ bỏ chúng khỏi bước kết quả.
  const hoSo = { code: 'UV-1', fields: {}, preferences: {}, status: 'confirmed', version: 1, labels: {} };
  const { h, render } = luong({
    ensureSessionId: async () => 's',
    fetchProfile: async () => hoSo,
    fetchMatches: async () => ({ matches: [], eligible_count: 0, total_considered: 18, missing_info: [], disclaimer: '' }),
  });
  render(); await h.flush();
  const chu = text(render());
  assert.match(chu, /không loại đơn vì nó/);
  assert.match(chu, /chỉ dùng để xếp thứ tự/);
});

test('khai lại từ đầu: đơn đã đăng ký của phiên cũ KHÔNG sang phiên mới (đường chủ đồ án tái hiện)', async () => {
  // Phiên cũ có một đơn đã đăng ký → Khai lại từ đầu → khai hồ sơ mới → xem kết
  // quả. Bản trước vẫn hiện "bạn đang có hồ sơ đăng ký đơn …" của phiên cũ, và
  // thẻ đơn ấy mang cờ "đã đăng ký".
  let phien = 's1';
  const dangKy = { s1: [{ job_order_code: 'DH-0009', status: 'pending_intake' }], s2: [] };
  const hoSo = (code, status = 'confirmed') => ({
    code, status, version: 1, labels: {}, preferences: {},
    fields: { full_name: { value: 'Ca Một' }, japanese_level: { value: 'N4' } },
  });
  const { h, render } = luong({
    ensureSessionId: async () => 's1',
    getSessionId: () => phien,
    fetchProfile: async sid => (sid === 's1' ? hoSo('UV-1') : null),
    fetchMyRegistrations: async sid => ({ items: dangKy[sid] }),
    fetchMatches: async () => ({
      matches: [{ code: 'DH-0009', eligible: true }], eligible_count: 1, total_considered: 1,
      missing_info: [], disclaimer: '',
    }),
    resetSession: async () => { phien = 's2'; return 's2'; },
    createProfile: async () => hoSo('UV-2', 'draft'),
    updateProfile: async () => hoSo('UV-2', 'draft'),
    confirmProfile: async () => hoSo('UV-2'),
  });
  render(); await h.flush();
  let cay = render();
  assert.match(text(cay), /đang có hồ sơ đăng ký đơn/, 'tiền đề: phiên cũ phải có đơn đã đăng ký');

  nutTen(cay, 'Khai lại từ đầu').props.onClick();
  await h.flush();
  cay = render();
  const o = nodes(cay).find(n => n.type?.displayName === 'CvUpload');
  assert.equal(o.key, 's2', 'ô gửi CV không dựng lại theo phiên — sẽ hiện kết quả đọc CV cũ');

  o.props.onProfileRead(hoSo('UV-2', 'draft'));
  cay = render();
  nutTen(cay, 'Xác nhận hồ sơ').props.onClick();
  await h.flush();
  cay = render();
  assert.ok(nutTen(cay, 'Khai lại từ đầu'), 'chưa sang được bước kết quả của phiên mới');
  assert.doesNotMatch(text(cay), /đang có hồ sơ đăng ký đơn/, 'đơn đã đăng ký của phiên cũ hiện ở phiên mới');
  const the = nodes(cay).find(n => n.type?.displayName === 'MatchCard');
  assert.equal(the.props.registered, false, 'thẻ đơn mang cờ "đã đăng ký" của phiên cũ');
});

test('vừa đăng ký xong rồi khai lại: thông báo "đã gửi đăng ký" không theo sang phiên mới', async () => {
  let phien = 's1';
  const hoSo = (code, status = 'confirmed') => ({
    code, status, version: 1, labels: {}, preferences: {},
    fields: { full_name: { value: 'Ca Một' }, japanese_level: { value: 'N4' } },
  });
  const { h, render } = luong({
    ensureSessionId: async () => 's1',
    getSessionId: () => phien,
    fetchProfile: async sid => (sid === 's1' ? hoSo('UV-1') : null),
    fetchMyRegistrations: async () => ({ items: [] }),
    fetchMatches: async () => ({
      matches: [{ code: 'DH-0009', eligible: true }], eligible_count: 1, total_considered: 1,
      missing_info: [], disclaimer: '',
    }),
    registerForOrder: async () => ({
      application_code: 'HS-1', job_order_code: 'DH-0009', job_order_title: 'Đơn thử', message: 'Đã ghi nhận.',
    }),
    resetSession: async () => { phien = 's2'; return 's2'; },
    createProfile: async () => hoSo('UV-2', 'draft'),
    updateProfile: async () => hoSo('UV-2', 'draft'),
    confirmProfile: async () => hoSo('UV-2'),
  });
  render(); await h.flush();
  await nodes(render()).find(n => n.type?.displayName === 'MatchCard').props.onRegister('DH-0009');
  await h.flush();
  // `\s+`: bộ khung nối các mảnh chữ bằng dấu cách, nên "đơn " + "DH-0009" thành hai dấu cách.
  assert.match(text(render()), /Đã gửi đăng ký đơn\s+DH-0009/, 'tiền đề: vừa đăng ký xong');

  nutTen(render(), 'Khai lại từ đầu').props.onClick();
  await h.flush();
  nodes(render()).find(n => n.type?.displayName === 'CvUpload').props.onProfileRead(hoSo('UV-2', 'draft'));
  nutTen(render(), 'Xác nhận hồ sơ').props.onClick();
  await h.flush();
  assert.doesNotMatch(text(render()), /Đã gửi đăng ký đơn/);
});
