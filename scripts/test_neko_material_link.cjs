// Run the shipped link initializer against valid and hostile launch parameters.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../patches/neko-study-2026-10-10-product/static/main.js'), 'utf8');
const start = source.indexOf('function configureLearningMaterialLink()');
const end = source.indexOf('async function bootstrap()', start);
assert.ok(start >= 0 && end > start);
function check(value) {
  const link = {hidden: false, href: 'http://stale.invalid', removeAttribute(name) { delete this[name]; }};
  const context = vm.createContext({URL, URLSearchParams, $id: () => link,
    window: {location: {search: value === null ? '' : '?' + new URLSearchParams({learning_surface: value})}}});
  vm.runInContext(source.slice(start, end), context);
  context.configureLearningMaterialLink();
  return {link, context};
}
const good = check('http://127.0.0.1:54321');
assert.equal(good.link.hidden, false);
assert.equal(good.link.href, 'http://127.0.0.1:54321/');
good.context.window.location.search = '';
good.context.configureLearningMaterialLink();
assert.equal(good.link.hidden, true);
assert.equal(good.link.href, undefined, 'A stale launch URL must be removed');
for (const value of [null, '', 'javascript:alert(1)', 'https://127.0.0.1:54321', 'http://localhost:54321',
  'http://127.0.0.1.evil.test:54321', 'http://127.0.0.1', 'http://127.0.0.1:0',
  'http://127.0.0.1:99999', 'http://user:pass@127.0.0.1:54321', 'http://127.0.0.1:54321/private',
  'http://127.0.0.1:54321/?token=secret', 'http://127.0.0.1:54321/#anything',
  'http://127.1:54321', 'http://127.0.0.1:54321/x/..', ' http://127.0.0.1:54321',
  'http://127.0.0.1:54321/?', 'http://127.0.0.1:54321/#']) {
  const {link} = check(value);
  assert.equal(link.hidden, true, value);
  assert.equal(link.href, undefined, value);
}
const duplicate = check('http://127.0.0.1:54321');
duplicate.context.window.location.search += '&learning_surface=http%3A%2F%2F127.0.0.1%3A54322';
duplicate.context.configureLearningMaterialLink();
assert.equal(duplicate.link.hidden, true);
assert.equal(duplicate.link.href, undefined);
console.log('PASS: current local material link, stale reset, duplicate rejection and 18 absent/unsafe parameters');
