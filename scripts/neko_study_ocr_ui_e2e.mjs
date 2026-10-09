/** One-command reproducer: synthetic browser pixels -> RapidOCR -> shipped UI -> real plugin.
 * Reuses shared web-inspector and its installed Playwright Core, never a user profile.
 */
import { chromium } from 'file:///D:/AI/tools/web-inspector/node_modules/playwright-core/index.mjs';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import net from 'node:net';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const python = path.join(root, '.tmp-uv-cache/neko-study-venv/Scripts/python.exe');
const evidenceRoot = path.join(root, 'benchmarks/raw/evidence');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const relative = filename => path.relative(root, filename).split(path.sep).join('/');

async function command(executable, args, timeout = 60000) {
  const child = spawn(executable, args, { cwd: root, windowsHide: true });
  let stdout = '', stderr = '';
  child.stdout.on('data', data => { stdout += data; });
  child.stderr.on('data', data => { stderr = (stderr + data).slice(-3000); });
  const timer = setTimeout(() => child.kill(), timeout);
  try {
    const code = await new Promise((resolve, reject) => {
      child.on('error', reject); child.on('close', resolve);
    });
    assert.equal(code, 0, `command failed: ${stderr || stdout.slice(-1500)}`);
    return JSON.parse(stdout);
  } finally { clearTimeout(timer); }
}

function portOpen(port) {
  return new Promise(resolve => {
    const socket = net.connect({ host: '127.0.0.1', port });
    const finish = open => { socket.destroy(); resolve(open); };
    socket.once('connect', () => finish(true));
    socket.once('error', () => finish(false));
    socket.setTimeout(1000, () => finish(false));
  });
}

const realMode = process.argv.includes('--real-model');
const adapter = spawn(python, [
  '-I', '-B', '-u', 'scripts/neko_study_plugin_ui_adapter.py',
  ...(realMode ? ['--real-model'] : []),
], {
  cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
});
let ready, browser, context, finalState, proof, failure, output = '', errors = '';
let adapterExited = false;
const closed = new Promise(resolve => adapter.once('close', code => { adapterExited = true; resolve(code); }));
adapter.stdout.on('data', data => {
  output += data;
  for (const line of output.split(/\r?\n/)) {
    try { const value = JSON.parse(line); if (value.ready) ready = value; } catch {}
  }
});
adapter.stderr.on('data', data => { errors = (errors + data).slice(-3000); });
adapter.on('error', error => { failure = error; });
const pageErrors = [], consoleErrors = [], blockedRequests = [];
const cleanup = {};
let screenshotArtifact, pixelManifest, finalScreenshot, failureDump;
try {
  const readyDeadline = Date.now() + (realMode ? 150000 : 60000);
  while (!ready && !adapterExited && !failure && Date.now() < readyDeadline) await delay(100);
  assert.ok(ready, `adapter unavailable: ${failure?.message || output.slice(-2000) || errors}`);
  const origin = new URL(ready.url).origin;
  console.log(JSON.stringify({ stage: 'adapter_ready', session_id: ready.session_id, correlation_id: ready.correlation_id }));

  // The shared CLI is sufficient for the static synthetic lesson. It closes its own browser.
  const inspected = await command(process.execPath, [
    'D:/AI/tools/web-inspector/cli.mjs', ready.synthetic_lesson_url, '--screenshot', '--json',
  ]);
  const shot = inspected.results[0];
  assert.ok(shot.success && shot.screenshotPath);
  assert.deepEqual(shot.consoleErrors, []); assert.deepEqual(shot.pageErrors, []);
  assert.deepEqual(shot.failedRequests, []);
  assert.equal(shot.finalUrl, ready.synthetic_lesson_url);
  const pixels = await readFile(shot.screenshotPath);
  screenshotArtifact = path.join(evidenceRoot, `neko-study-browser-pixels-${ready.correlation_id}.png`);
  await copyFile(shot.screenshotPath, screenshotArtifact);
  pixelManifest = path.join(evidenceRoot, `neko-study-browser-pixels-${ready.correlation_id}.json`);
  await writeFile(pixelManifest, JSON.stringify({
    source_tool: 'web-inspector headless Chromium', synthetic_only: true,
    ...shot, screenshotPath: undefined, screenshot_artifact: relative(screenshotArtifact),
    screenshot_sha256: sha256(pixels), image_format: 'PNG', correlation_id: ready.correlation_id,
  }, null, 2) + '\n');
  const uploaded = await fetch(ready.screenshot_upload_url, {
    method: 'POST', headers: { 'content-type': 'image/png',
      'X-Fixture-Capture-Source': 'web-inspector-headless-chromium',
      'X-Fixture-Inspector-Artifact': path.basename(pixelManifest) }, body: pixels,
  });
  assert.ok(uploaded.ok, `screenshot upload failed: ${uploaded.status}`);
  const upload = await uploaded.json();
  assert.equal(upload.screenshot.sha256, sha256(pixels));

  // Keep the shipped asynchronous UI alive through its own DOM actions and reload.
  browser = await chromium.launch({ headless: true,
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    args: ['--mute-audio', '--no-first-run', '--no-default-browser-check',
      '--disable-background-networking', '--disable-sync', '--disable-extensions'],
  });
  context = await browser.newContext({ viewport: { width: 1280, height: 900 },
    permissions: [], serviceWorkers: 'block' });
  await context.route('**/*', route => {
    if (new URL(route.request().url()).origin === origin) return route.continue();
    blockedRequests.push(route.request().url());
    return route.abort('blockedbyclient');
  });
  await context.addInitScript(() => {
    const deny = () => { throw new Error('isolated fixture output blocked'); };
    window.AudioContext = window.webkitAudioContext = class { constructor() { deny(); } };
    if (window.speechSynthesis) window.speechSynthesis.speak = deny;
    HTMLMediaElement.prototype.play = async () => deny();
    if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = async () => deny();
    window.WebSocket = class { constructor() { deny(); } };
    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = new URL(typeof input === 'string' ? input : input.url, location.href);
      if (url.origin !== location.origin) return Promise.reject(new Error('external fetch blocked'));
      return nativeFetch(input, init);
    };
  });
  const page = await context.newPage();
  page.on('pageerror', error => pageErrors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await page.goto(ready.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  const deadline = Date.now() + (realMode ? 480000 : 150000);
  let lastRunCount = -1;
  while (Date.now() < deadline) {
    const stateResponse = await fetch(`${origin}/__fixture-state`);
    assert.ok(stateResponse.ok);
    finalState = await stateResponse.json();
    if (finalState.runs.length !== lastRunCount) {
      lastRunCount = finalState.runs.length;
      const entry = finalState.plugin_entrypoints_called.at(-1);
      if (entry && !['study_status', 'study_memory_list_decks', 'study_get_practice_scope', 'study_question_context'].includes(entry))
        console.log(JSON.stringify({ stage: 'plugin_progress', entry }));
    }
    const uiError = await page.evaluate(() => window.__nekoStudyUiError || '').catch(() => '');
    assert.equal(uiError, '', uiError);
    const artifact = await page.locator('#replyText').getAttribute('data-fixture-complete').catch(() => null);
    if (artifact && artifact !== 'true') {
      assert.ok(/^benchmarks\/raw\/evidence\/neko-study-plugin-ui-\d+T\d+Z\.json$/.test(artifact));
      proof = JSON.parse(await readFile(path.join(root, artifact), 'utf8'));
      proof.artifact = artifact;
      break;
    }
    await delay(200);
  }
  assert.ok(proof, `UI did not finish through reload within ${realMode ? 480 : 150} seconds`);
  assert.equal(proof.result, realMode ? 'PASS_SHIPPED_STATIC_UI_REAL_MODEL_LOOP' : 'PASS_SHIPPED_STATIC_UI_PLUGIN_LOOP');
  if (realMode) {
    assert.equal(proof.live_model_or_provider_used, true);
    assert.equal(proof.model_backend, 'real');
    assert.ok(proof.model_call_totals.calls >= 7, 'the live loop should record multiple provider calls');
    assert.ok(proof.model_call_totals.input_tokens > 0 && proof.model_call_totals.output_tokens > 0);
    assert.equal(proof.ui_ux_checks.mode_banner_replies, 0);
    assert.equal(proof.ui_ux_checks.explanations_have_cjk, true);
    assert.equal(proof.ui_ux_checks.summaries_have_cjk, true);
    console.log(JSON.stringify({ stage: 'ux_checks', ...proof.ui_ux_checks, grade: proof.model_call_totals }));
  } else {
    assert.equal(proof.live_model_or_provider_used, false);
  }
  assert.equal(proof.correlation_id, ready.correlation_id);
  assert.equal(proof.session_id, ready.session_id);
  assert.equal(proof.ocr.screenshot.sha256, sha256(pixels));
  assert.equal(proof.ocr.expected_token_recall, 1);
  assert.equal(proof.ocr.capture_calls, 1);
  assert.deepEqual(proof.required_flow_steps_missing, []);
  assert.ok(proof.mastery > proof.mastery_before_ui_answer);
  assert.ok(proof.trace_pass && proof.session_record_id_matches && proof.interaction_session_ids_match);
  assert.ok(proof.ui_events.every(group => group.events.every(event => event.result_visible === true)));
  assert.deepEqual(pageErrors, []); assert.deepEqual(consoleErrors, []);
  assert.deepEqual(blockedRequests, []);
  assert.ok(Object.values(proof.downstream_calls).every(value => value === 0));
  assert.ok(await page.locator('#replyText').isVisible());
  assert.ok(await page.locator('#learningProfileModal').isHidden());
  if (!(await page.locator('#practicePanel').evaluate(element => element.open)))
    await page.locator('#practicePanel > summary').click();
  finalScreenshot = path.join(evidenceRoot, `neko-study-ocr-ui-final-${ready.correlation_id}.png`);
  await page.screenshot({ path: finalScreenshot, fullPage: true });
  console.log(JSON.stringify({ stage: 'browser_flow_pass', proof: proof.artifact }));
} catch (error) {
  failure = error;
  // Keep the paid live calls inspectable even when a step does not pass.
  try {
    const response = await fetch(`${origin}/__fixture-state`);
    if (response.ok) {
      const state = await response.json();
      const dumpPath = path.join(evidenceRoot, `neko-study-ui-failure-${ready.correlation_id}.json`);
      failureDump = relative(dumpPath);
      await writeFile(dumpPath, JSON.stringify({
        error: String(error?.message || error).slice(0, 600),
        ui_error: await page.evaluate(() => window.__nekoStudyUiError || '').catch(() => ''),
        active_mode: state.active_mode, session_id: state.session_id,
        runs: state.runs.map(run => ({
          entry_id: run.entry_id, args_text: String(run.args?.text || run.args?.answer || '').slice(0, 200),
          reply: String(run.data?.reply || run.data?.question || run.data?.summary || '').slice(0, 900),
          degraded: run.data?.degraded, verdict: run.data?.verdict, score: run.data?.score,
        })),
        model_calls: state.model_calls, ocr: state.ocr, ocr_failure: state.ocr_failure,
      }, null, 2) + '\n');
      failureArtifact = relative(dumpPath);
    }
  } catch {}
} finally {
  try { if (context) await context.close(); cleanup.browser_context_closed = true; } catch { cleanup.browser_context_closed = false; }
  try { if (browser) await browser.close(); cleanup.browser_closed = true; } catch { cleanup.browser_closed = false; }
  if (ready && !adapterExited) {
    try {
      const response = await fetch(`${new URL(ready.url).origin}/__fixture-stop/${ready.correlation_id}`, { method: 'POST' });
      cleanup.graceful_stop_requested = response.ok;
    } catch { cleanup.graceful_stop_requested = false; }
  }
  await Promise.race([closed, delay(5000)]);
  if (!adapterExited) { adapter.kill(); await closed; cleanup.forced_adapter_stop = true; }
  cleanup.adapter_exited = adapterExited;
  if (ready) cleanup.listener_closed = !(await portOpen(Number(new URL(ready.url).port)));
}

let persistence;
if (proof && !failure) {
  try {
    persistence = await command(python, ['-I', '-B', 'scripts/neko_study_ui_persistence_check.py', proof.artifact]);
    assert.equal(persistence.result, 'PASS_REOPENED_TEMP_SQLITE');
    assert.ok(cleanup.browser_closed && cleanup.adapter_exited && cleanup.listener_closed && cleanup.graceful_stop_requested);
  } catch (error) { failure = error; }
}
const final = {
  timestamp_utc: new Date().toISOString(),
  result: failure
    ? (realMode ? 'FAIL_UNIFIED_OCR_STUDY_UI_REAL_MODEL_LOOP' : 'FAIL_UNIFIED_OCR_STUDY_UI_LOOP')
    : (realMode ? 'PASS_UNIFIED_OCR_STUDY_UI_REAL_MODEL_LOOP' : 'PASS_UNIFIED_OCR_STUDY_UI_LOOP'),
  model_backend: realMode ? 'real' : 'mock',
  failure: failure?.message, session_id: ready?.session_id, correlation_id: ready?.correlation_id,
  plugin_proof: proof?.artifact, failure_dump: failureDump, pixel_manifest: pixelManifest && relative(pixelManifest),
  screenshot: finalScreenshot && relative(finalScreenshot), persistence, cleanup,
  page_errors: pageErrors, console_errors: consoleErrors, blocked_non_loopback_requests: blockedRequests,
  runtime: realMode
    ? 'shared web-inspector CLI/Playwright Core; fresh headless Chrome; temporary SQLite; live provider (api.deepseek.com) through the genuine plugin lifecycle'
    : 'shared web-inspector CLI/Playwright Core; fresh headless Chrome; temporary SQLite; deterministic Mock LLM',
};
const finalArtifact = path.join(evidenceRoot, `neko-study-unified-${ready?.correlation_id || Date.now()}.json`);
await writeFile(finalArtifact, JSON.stringify(final, null, 2) + '\n');
console.log(JSON.stringify({ ...final, artifact: relative(finalArtifact) }, null, 2));
if (failure) process.exitCode = 1;
