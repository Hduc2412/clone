const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function setup(candidate, chat) {
  const storage = () => {
    const data = new Map();
    return { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, v), removeItem: k => data.delete(k) };
  };
  const events = [];
  const window = { localStorage: storage(), sessionStorage: storage(), dispatchEvent: event => events.push(event.type) };
  if (candidate) window.localStorage.setItem("xkld-candidate-session", candidate);
  if (chat) window.sessionStorage.setItem("xkld-chat-state-v1", JSON.stringify({ sessionId: chat }));
  const context = { exports: {}, window, crypto: { randomUUID: () => "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" }, Event: class { constructor(type) { this.type = type; } } };
  const source = fs.readFileSync(path.join(__dirname, "../lib/journeySession.ts"), "utf8");
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, context);
  return { api: context.exports, window, events };
}

test("new chat and CV reuse one identity", () => {
  const { api } = setup();
  assert.equal(api.getSessionId(), api.getSessionId());
});
test("preserve legacy CV hex identity", () => {
  const { api } = setup("a".repeat(32));
  assert.equal(api.getSessionId(), "a".repeat(32));
});
test("adopt chat only without existing candidate", () => {
  const id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  assert.equal(setup(null, id).api.getSessionId(), id);
});
test("never merge conflicting legacy identities", () => {
  const { api } = setup("a".repeat(32), "c".repeat(32));
  assert.equal(api.getSessionId(), "a".repeat(32));
});
test("reset clears chat state before making fresh identity", () => {
  const { api, window, events } = setup("a".repeat(32), "a".repeat(32));
  assert.notEqual(api.resetSession(), "a".repeat(32));
  assert.equal(window.sessionStorage.getItem("xkld-chat-state-v1"), null);
  assert.deepEqual(events, ["xkld-journey-reset"]);
});
