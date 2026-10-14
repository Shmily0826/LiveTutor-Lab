/** Actual encoder function, with bounded canvas output seams. No browser/device. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../patches/neko-study-2026-10-10-product/static/main.js'), 'utf8');
const start = source.indexOf('async function compressImageForStudy(');
const end = source.indexOf('\nfunction insertPastedText(', start);
assert(start > 0 && end > start);

async function encode(type, outputs, { signal, width = 600, height = 400 } = {}) {
  const calls = [];
  const canvas = { getContext: () => ({ fillRect() {}, drawImage() {} }),
    toDataURL: (mime, quality) => { calls.push([mime, quality]); return outputs[mime + ':' + quality]; } };
  const scope = { loadImageFromBlob: async () => ({ naturalWidth: width, naturalHeight: height }),
    llmVisionMaxImagePx: 768, TARGET_DATA_URL_LENGTH: 100, document: { createElement: () => canvas },
    console: { warn() {} } };
  vm.createContext(scope);
  vm.runInContext(source.slice(start, end), scope);
  const result = await scope.compressImageForStudy({ type }, signal);
  return { result, calls, width: canvas.width, height: canvas.height };
}

(async () => {
  let result = await encode('image/png', { 'image/png:undefined': 'data:image/png;base64,AA==' });
  assert.equal(result.result, 'data:image/png;base64,AA==');
  assert.deepEqual(result.calls, [['image/png', undefined]]);
  result = await encode('image/png', { 'image/png:undefined': 'x'.repeat(101), 'image/jpeg:0.82': 'jpeg82' });
  assert.equal(result.result, 'jpeg82');
  assert.deepEqual(result.calls, [['image/png', undefined], ['image/jpeg', .82]]);
  result = await encode('image/jpeg', { 'image/jpeg:0.82': 'x'.repeat(101), 'image/jpeg:0.56': 'jpeg56' });
  assert.equal(result.result, 'jpeg56');
  assert.deepEqual(result.calls, [['image/jpeg', .82], ['image/jpeg', .56]]);
  result = await encode('image/png', { 'image/png:undefined': 'x'.repeat(101), 'image/jpeg:0.82': 'x'.repeat(101),
    'image/jpeg:0.56': 'x'.repeat(101), 'image/jpeg:0.3': 'x'.repeat(101) });
  assert.equal(result.result, null);
  assert.equal(result.calls.length, 4);
  result = await encode('image/png', {}, { signal: { aborted: true } });
  assert.equal(result.result, null);
  assert.deepEqual(result.calls, []);
  result = await encode('image/png', { 'image/png:undefined': 'png' }, { width: 1600, height: 800 });
  assert.equal(result.width, 768);
  assert.equal(result.height, 384);
  result = await encode('image/png', {}, { width: 0 });
  assert.equal(result.result, null);
  assert.deepEqual(result.calls, []);
  process.stdout.write('PASS: 7 encoder cases (PNG, JPEG fallback, byte cap, cancel, dimensions)\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
