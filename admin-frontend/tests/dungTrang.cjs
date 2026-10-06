/**
 * Dựng một trang Next (client component) không cần trình duyệt.
 *
 * Biên dịch file `.tsx` bằng TypeScript, thay React bằng bộ hook tối giản và các
 * module ngoài bằng bản giả truyền vào. Component viết **trong cùng file** (thẻ
 * đơn, dòng tiêu chí…) được gọi thật — đó là chỗ hay sập. Component nhập từ ngoài
 * thì giữ nguyên nút để kiểm prop.
 *
 * Không phải file kiểm thử (`*.test.cjs`), nên `npm test` không chạy riêng nó.
 */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const GOC = path.join(__dirname, "..");

function gia(ten) {
  return Object.assign(() => null, { displayName: ten });
}

function dungTrang(duongTuGoc, modulesGia) {
  const values = [];
  let cursor = 0;
  let effectCursor = 0;
  const effects = [];
  const pending = [];
  const react = {
    useState(initial) {
      const i = cursor++;
      if (!(i in values)) values[i] = typeof initial === "function" ? initial() : initial;
      return [values[i], (next) => { values[i] = typeof next === "function" ? next(values[i]) : next; }];
    },
    useCallback: (fn) => fn,
    useMemo: (fn) => fn(),
    useEffect(fn, deps) {
      const i = effectCursor++;
      const truoc = effects[i];
      if (!truoc || !deps || deps.some((d, j) => d !== truoc.deps[j])) {
        effects[i] = { deps: deps || [] };
        pending.push(fn);
      }
    },
  };
  const jsx = (type, props, key) => ({ type, props: props || {}, key });
  const modules = {
    react,
    "react/jsx-runtime": { jsx, jsxs: jsx, Fragment: "Fragment" },
    "next/link": { __esModule: true, default: gia("Link") },
    ...modulesGia,
  };
  const context = {
    exports: {},
    window: { prompt: () => null, alert() {} },
    Date,
    require(ten) {
      if (modules[ten]) return modules[ten];
      throw new Error(`Module chưa dựng: ${ten}`);
    },
  };
  const nguon = fs.readFileSync(path.join(GOC, duongTuGoc), "utf8");
  vm.runInNewContext(ts.transpileModule(nguon, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText, context);
  const Trang = context.exports.default;
  return {
    context,
    render() { cursor = 0; effectCursor = 0; return moRong(Trang({})); },
    async flush() {
      for (let vong = 0; vong < 3; vong++) {
        pending.splice(0).forEach((fn) => fn());
        for (let i = 0; i < 4; i++) await new Promise((r) => setImmediate(r));
        this.render();
      }
    },
  };
}

/** Gọi luôn các component con viết trong file — bản giả có `displayName` thì giữ nguyên. */
function moRong(cay) {
  if (cay == null || typeof cay === "boolean") return cay;
  if (Array.isArray(cay)) return cay.map(moRong);
  if (typeof cay !== "object") return cay;
  if (typeof cay.type === "function" && !cay.type.displayName) return moRong(cay.type(cay.props));
  return { ...cay, props: { ...cay.props, children: moRong(cay.props.children) } };
}

function cacNut(cay) {
  if (cay == null || typeof cay === "boolean") return [];
  if (Array.isArray(cay)) return cay.flatMap(cacNut);
  if (typeof cay !== "object") return [cay];
  return [cay, ...cacNut(cay.props.children)];
}

function chu(cay) {
  return cacNut(cay)
    .filter((n) => typeof n === "string" || typeof n === "number")
    .join(" ");
}

module.exports = { dungTrang, gia, cacNut, chu };
