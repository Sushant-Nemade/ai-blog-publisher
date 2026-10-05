const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const vm = require('node:vm');

function registry(fetch) {
  const context = vm.createContext({ URL, AbortSignal, fetch, window: {
    location: { href: 'http://localhost/project/index.html', origin: 'http://localhost' }, CONFIG: {},
  }});
  vm.runInContext(readFileSync('blogboard/web/js/blogs-data.js', 'utf8'), context);
  return context;
}

test('content paths stay inside the repository site', () => {
  const context = registry();
  assert.equal(vm.runInContext("contentURL('blogs/ml/example.md')", context), 'http://localhost/project/blogs/ml/example.md');
  for (const path of ['../secret', 'https://example.org/post.md', 'blogs/ml/../../secret.md']) {
    assert.throws(() => vm.runInContext(`contentURL(${JSON.stringify(path)})`, context));
  }
});

test('failed loads are not cached as empty categories', async () => {
  let calls = 0;
  const context = registry(async () => ({ ok: ++calls > 1, status: 503, text: async () => '[]' }));
  await assert.rejects(vm.runInContext("loadCategoryArticles('ml')", context));
  assert.equal((await vm.runInContext("loadCategoryArticles('ml')", context)).length, 0);
  assert.equal(calls, 2);
});

test('metadata shape and paths are validated', async () => {
  const context = registry(async () => ({ ok: true, text: async () => JSON.stringify([{ category: 'ml', file: '../secret' }]) }));
  await assert.rejects(vm.runInContext("loadCategoryArticles('ml')", context));
});