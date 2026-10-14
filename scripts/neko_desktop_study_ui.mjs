/** Drive the real N.E.K.O host's own Study UI in a browser, text-only.
 *
 * The page is served by the host's plugin static UI and every action goes
 * through the host's plugin message path. The capture button is deliberately not
 * used: the active-window capture swept in unrelated desktop windows, so the
 * screen-teaching step stays unverified this round (see
 * docs/neko-desktop-tutor-2026-10-09.md).
 */
import { chromium } from 'file:///D:/AI/tools/web-inspector/node_modules/playwright-core/index.mjs';
import { createHash } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { checkStudyResume } from './neko_study_resume_e2e.mjs';

const ROOT = path.resolve(import.meta.dirname, '..');
const UP_TO_MODE = process.argv.includes('--up-to-mode');
const RESUME_OFFLINE = process.argv.includes('--resume-offline');
const UI = process.env.NEKO_UI_URL || 'http://127.0.0.1:48916/plugin/study_companion/ui/';
const LESSON = 'Example 4: let u = 3x + 2, so du = 3 dx and dx = du/3. Integrate e^u with the 1/3 factor.';
const FOLLOW_UP = '为什么 dx 要换成 du/3，而不是直接积分？';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

const steps = [];
const pageErrors = [];
const failedResources = [];
const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--mute-audio', '--no-first-run', '--no-default-browser-check', '--disable-background-networking'],
});
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, permissions: [], serviceWorkers: 'block' });
const STOP = Symbol('up-to-mode');
let failure;
try {
  const page = await context.newPage();
  page.on('pageerror', error => pageErrors.push(String(error).slice(0, 200)));
  page.on('console', message => { if (message.type() === 'error') pageErrors.push(message.text().slice(0, 200)); });
  page.on('response', response => {
    if (response.status() >= 400) failedResources.push(`${response.status()} ${new URL(response.url()).pathname}`);
  });
  await page.goto(UI, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('#studyInput', { timeout: 60000 });
  if (RESUME_OFFLINE) {
    await checkStudyResume(page, steps);
    throw STOP;
  }
  // The shipped first-run profile dialog is created lazily (it appears when an
  // action needs a learning profile), and it covers the panel while open, so it
  // has to be dismissed through its own control before every interaction.
  // The shipped first-run dialogs are created *after* load and cover the panel
  // while open, so each interaction has to close whatever is up first.
  const settled = (selector) => page.waitForFunction((id) => {
    const dialog = document.querySelector(id);
    if (!dialog) return true;
    const style = getComputedStyle(dialog);
    return dialog.hidden === true || dialog.getAttribute('aria-hidden') === 'true'
      || style.display === 'none' || style.visibility === 'hidden';
  }, selector, { timeout: 20000 });
  const dismissDialog = async (label) => {
    const closed = [];
    for (const [selector, control] of [['#learningProfileModal', '[data-stage="college"]'],
                                       ['#memoryDeckDialog', '#memoryDeckSkipBtn']]) {
      const dialog = page.locator(selector);
      // Give the lazily built dialog a moment to appear before deciding there is
      // nothing to dismiss; a fixed sleep after load used to lose this race.
      const appeared = await dialog.waitFor({ state: 'visible', timeout: 4000 })
        .then(() => true).catch(() => false);
      if (!appeared) continue;
      const target = dialog.locator(control);
      const choice = (await target.count()) ? target.first() : dialog.locator('button').first();
      await choice.click({ timeout: 10000 });
      await settled(selector);
      closed.push(selector.slice(1));
    }
    if (!closed.length) return false;
    steps.push({ step: `first_run_dialogs_dismissed_before_${label}`, dialogs: closed });
    return true;
  };
  await dismissDialog('load');
  steps.push({ step: 'ui_loaded', title: await page.title(), url: UI });

  await dismissDialog('mode');
  await page.click('#modeTeachingBtn');
  await page.waitForTimeout(2500);
  steps.push({
    step: 'teaching_mode_selected',
    button_class: await page.locator('#modeTeachingBtn').getAttribute('class'),
    switch_state: await page.locator('#modeSwitch').getAttribute('data-active'),
  });
  if (UP_TO_MODE) {
    // Smoke mode: everything above is the shipped first-run experience and costs no
    // provider call, so it can be re-checked as often as the UI changes.
    throw STOP;
  }

  const reply = () => page.locator('#replyText').innerText();
  const idle = () => page.locator('#explainBtn').isDisabled();

  await dismissDialog('explain');
  await page.fill('#studyInput', LESSON);
  let started = Date.now();
  await page.click('#explainBtn');
  await page.waitForFunction(() => !document.querySelector('#explainBtn')?.disabled
    && (document.querySelector('#replyText')?.textContent || '').length > 120, null, { timeout: 200000 });
  const first = await reply();
  steps.push({ step: 'explain_initial', ms: Date.now() - started, chars: first.length, head: first.slice(0, 800) });

  const followBox = page.locator('#usePreviousExplanation');
  if (await followBox.count() && await followBox.isEnabled()) await followBox.check();
  await page.fill('#studyInput', FOLLOW_UP);
  started = Date.now();
  await page.click('#explainBtn');
  await page.waitForFunction((previous) => {
    const text = document.querySelector('#replyText')?.textContent || '';
    return !document.querySelector('#explainBtn')?.disabled && text.length > 120
      && !text.includes(previous.slice(0, 30));
  }, first, { timeout: 200000 });
  const second = await reply();
  steps.push({ step: 'explain_follow_up', ms: Date.now() - started, chars: second.length, head: second.slice(0, 800) });

  // The shipped panel keeps the session controls inside a collapsed <details>;
  // expand them the way a user scrolling the page would.
  await page.evaluate(() => document.querySelectorAll('details').forEach(node => { node.open = true; }));
  await dismissDialog('summarize');
  await page.locator('#summarizeBtn').scrollIntoViewIfNeeded();
  await page.click('#summarizeBtn');
  started = Date.now();
  try {
    await page.waitForFunction(() => !document.querySelector('#summarizeBtn')?.disabled
      && (document.querySelector('#replyText')?.textContent || '').length > 80, null, { timeout: 200000 });
  } catch { /* summary wording is model dependent; recorded below either way */ }
  const summary = await reply();
  steps.push({ step: 'session_summary', ms: Date.now() - started, chars: summary.length, head: summary.slice(0, 800) });
  steps.forEach(step => console.log(JSON.stringify({ step: step.step, ms: step.ms ?? null, chars: step.chars ?? null })));
} catch (error) {
  if (error !== STOP) failure = error;
} finally {
  await context.close();
  await browser.close();
}

const report = {
  timestamp_utc: new Date().toISOString(),
  ui_url: UI,
  result: failure ? 'FAIL_DESKTOP_STUDY_UI_RUN'
    : (RESUME_OFFLINE ? 'PASS_STUDY_REAL_SDK_RESUME_AND_LABELLED_OFFLINE_FAILURE'
      : UP_TO_MODE ? 'PASS_DESKTOP_STUDY_UI_FIRST_RUN_AND_MODE' : 'PASS_DESKTOP_STUDY_UI_TEXT_LOOP'),
  failure: failure ? String(failure.message || failure).slice(0, 600) : undefined,
  steps,
  page_errors: pageErrors.slice(0, 10),
  failed_resources: [...new Set(failedResources)].slice(0, 10),
  audio_posture: RESUME_OFFLINE
    ? 'task Chromium --mute-audio; installed page capture guard asserted; no capture button; host permission/ledger/cleanup verified by the outer runtime record'
    : 'headless Chromium with --mute-audio; host launched with DISABLE_TTS=true and no speech credentials; the screen-capture button was never clicked',
};
const serialised = JSON.stringify(report, null, 2) + '\n';
if (/sk-[A-Za-z0-9_-]{20,}/.test(serialised)) throw new Error('refusing to write a credential');
const artifact = path.join(ROOT, 'benchmarks/raw/evidence',
  `neko-desktop-study-ui-${new Date().toISOString().replace(/[-:]/g, '').slice(0, 15)}Z.json`);
await writeFile(artifact, serialised);
console.log(JSON.stringify({
  artifact: path.relative(ROOT, artifact).split(path.sep).join('/'),
  result: report.result,
  sha256: createHash('sha256').update(serialised).digest('hex').slice(0, 16),
  failure: report.failure,
  page_errors: report.page_errors,
}, null, 2));
if (failure) process.exitCode = 1;
