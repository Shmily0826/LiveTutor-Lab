// Actual canonical UI functions with local DOM/RPC stubs; no browser/host/audio.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../patches/neko-study-2026-10-10-product/static/main.js'), 'utf8');
function section(first, next) {
  const start = source.indexOf(first);
  const end = source.indexOf(next, start + first.length);
  assert.ok(start >= 0 && end > start, first);
  return source.slice(start, end);
}
const code = [
  section('function setPasteError(', 'function setImagePreview('),
  section('function studyContextIsCurrent(', 'function normalizeVisionMaxImagePx('),
  section('async function exportRunResult(', 'async function callPlugin('),
  section('async function refreshStatus(', 'async function loadQuestionContext('),
  section('function buildFollowupText(', 'async function generateQuestion('),
].join('\n');
const notice = () => ({textContent: '', hidden: true});
function host() {
  const controls = notice();
  const imageStatus = notice();
  const calls = [];
  const ui = {
    studyMaterialControlNotice: controls, studyInputImageValue: 'data:image/png;base64,fixture',
    studyInput: {value: 'Explain current image'}, previousExplanation: null,
    usePreviousExplanation: {checked: false, disabled: true},
    studyMaterialRevision: 1, statusRefreshRevision: 0, studyServiceReady: true,
    lastStatusPayload: {study_course_id: 'A', study_session_id: 'session-A'},
    pastePendingCount: 0, ocrT: '', ocrN: '', replies: [], calls,
    $id: () => imageStatus, setStatus: () => {},
    setReply: reply => ui.replies.push(reply), scrollReplyIntoView: () => {},
    t: (_, fallback) => fallback, tf: (_, fallback) => fallback,
    formatTutorDiagnostic: diagnostic => diagnostic,
    outcomeFormatters: {formatKnowledgeGuidanceEvidence: () => '',
      formatSolutionNarrationNotice: () => '', formatGeneralNarrationNotice: () => ''},
    applyRuntimeConfig: () => {}, setStatusLine: data => {ui.lastStatusPayload = data;},
    isStudyConnectionError: () => false,
    RUNS_URL: '/runs', RUN_TIMEOUT_MS: 15000, RUN_EXPORT_RETRY_COUNT: 1,
    timeLeft: () => 10000,
  };
  ui.callPlugin = async (entry, args) => {
    calls.push({entry, args});
    if (entry === 'study_status') return {study_course_id: 'A', study_session_id: 'session-A'};
    if (entry === '__llm_tool__study_material') return {output: ui.material || {course_id: 'A', material_control_submission: []}, is_error: false};
    if (entry === 'study_submit_image') return ui.result || {reply: 'Accepted explanation', material_control_submission: []};
    throw new Error(`unexpected entry ${entry}`);
  };
  vm.createContext(ui);
  vm.runInContext(code, ui);
  return ui;
}
function pending() {
  let resolve;
  const promise = new Promise(done => {resolve = done;});
  return {promise, resolve};
}
async function verify() {
  let checks = 0;
  for (const status of ['unavailable', 'not_submitted', 'exception', 'submission_unknown']) {
    const ui = host();
    const records = [{status}];
    ui.result = {reply: 'Accepted explanation', material_control_submission: records};
    ui.material = {course_id: 'A', material_control_submission: records};
    await ui.explainText();
    assert.match(ui.studyMaterialControlNotice.textContent, /材料已更新，但尚未确认旧语音停止；必要时重新开始语音/);
    assert.equal(ui.studyInputImageValue, 'data:image/png;base64,fixture');
    assert.equal(ui.previousExplanation.reply, 'Accepted explanation');
    assert.ok(ui.replies.includes('Accepted explanation'));
    assert.equal(ui.calls.filter(call => call.entry === 'study_submit_image').length, 1);
    assert.equal(ui.calls.filter(call => call.entry === 'study_explain_text').length, 0);
    checks += 1;
  }
  {
    const ui = host();
    ui.renderMaterialControlSubmission({success: true, data: {material_control_submission: [{status: 'submitted'}]}});
    assert.match(ui.studyMaterialControlNotice.textContent, /通知已提交，尚未确认/);
    assert.doesNotMatch(ui.studyMaterialControlNotice.textContent, /已经停止|取消完成|已停止播放/);
    ui.renderMaterialControlSubmission({output: JSON.stringify({material_control_submission: [{status: 'submitted'}, {status: 'exception'}]}), is_error: false});
    assert.match(ui.studyMaterialControlNotice.textContent, /必要时重新开始语音/);
    ui.renderMaterialControlSubmission({value: {material_control_submission: []}});
    assert.equal(ui.studyMaterialControlNotice.hidden, true);
    ui.renderMaterialControlSubmission({reply: 'legacy'});
    assert.equal(ui.studyMaterialControlNotice.hidden, true);
    ui.renderMaterialControlSubmission({material_control_submission: [{status: 'unknown-future-status'}]});
    assert.match(ui.studyMaterialControlNotice.textContent, /尚未确认/);
    const remembered = ui.studyMaterialControlNotice.textContent;
    for (const err of [{success: false, error: {message: 'Err'}}, {is_error: true, output: {material_control_submission: [{status: 'submitted'}]}}, {reply: 'legacy'}]) {
      ui.renderMaterialControlSubmission(err);
      assert.equal(ui.studyMaterialControlNotice.textContent, remembered);
    }
    checks += 1;
  }
  {
    const ui = host();
    ui.fetchWithTimeout = async () => ({ok: true, json: async () => ({items: [{type: 'json', json: {
      success: true, data: {reply: 'SDK explanation', material_control_submission: [{status: 'exception'}]}
    }}]})});
    const exported = await ui.exportRunResult('fixture-run');
    ui.renderMaterialControlSubmission(exported);
    assert.match(ui.studyMaterialControlNotice.textContent, /尚未确认/);
    ui.fetchWithTimeout = async () => ({ok: true, json: async () => ({items: [{type: 'json', json: {
      success: false, error: {message: 'old-context', code: 'course_context_changed'}
    }}]})});
    await assert.rejects(ui.exportRunResult('fixture-run'), error => error.message === 'old-context' && error.code === 'course_context_changed');
    checks += 1;
  }
  {
    const ui = host();
    ui.material = {course_id: 'A', material_control_submission: [{status: 'submission_unknown'}]};
    await ui.refreshStatus();
    assert.match(ui.studyMaterialControlNotice.textContent, /必要时重新开始语音/);
    assert.deepEqual(ui.calls.map(call => call.entry), ['study_status', '__llm_tool__study_material']);
    const prior = ui.studyMaterialControlNotice.textContent;
    ui.callPlugin = async () => {throw new Error('local metadata unavailable');};
    await ui.refreshMaterialControl(ui.statusRefreshRevision);
    assert.equal(ui.studyMaterialControlNotice.textContent, prior);
    assert.equal(ui.studyInputImageValue, 'data:image/png;base64,fixture');
    checks += 1;
  }
  for (const changed of ['course', 'session', 'image', 'refresh']) {
    const ui = host();
    ui.statusRefreshRevision = 1;
    const wait = pending();
    ui.callPlugin = async () => wait.promise;
    const read = ui.refreshMaterialControl(1);
    if (changed === 'course') ui.lastStatusPayload.study_course_id = 'B';
    else if (changed === 'session') ui.lastStatusPayload.study_session_id = 'session-B';
    else if (changed === 'image') ui.studyMaterialRevision += 1;
    else ui.statusRefreshRevision += 1;
    ui.studyMaterialControlNotice.textContent = 'current context';
    wait.resolve({course_id: 'A', material_control_submission: [{status: 'exception'}]});
    await read;
    assert.equal(ui.studyMaterialControlNotice.textContent, 'current context');
    checks += 1;
  }
  for (const changed of ['course', 'session', 'image']) {
    const ui = host();
    const baseCall = ui.callPlugin;
    const wait = pending();
    let entered;
    const submission = new Promise(done => {entered = done;});
    ui.callPlugin = async (entry, args) => {
      if (entry === 'study_submit_image') {entered(); return wait.promise;}
      return baseCall(entry, args);
    };
    const request = ui.explainText();
    await submission;
    if (changed === 'course') ui.lastStatusPayload.study_course_id = 'B';
    else if (changed === 'session') ui.lastStatusPayload.study_session_id = 'session-B';
    else ui.studyMaterialRevision += 1;
    ui.studyMaterialControlNotice.textContent = 'new context notice';
    wait.resolve({reply: 'old explanation', material_control_submission: [{status: 'exception'}]});
    await request;
    assert.equal(ui.studyMaterialControlNotice.textContent, 'new context notice');
    assert.equal(ui.previousExplanation, null);
    assert.ok(!ui.replies.includes('old explanation'));
    checks += 1;
  }
  assert.match(fs.readFileSync(path.join(__dirname, '../patches/neko-study-2026-10-10-product/static/index.html'), 'utf8'),
    /id="studyMaterialControlNotice"[^>]+role="status"[^>]+aria-live="polite"[^>]+hidden/);
  new vm.Script(source); // Entire canonical file remains valid JavaScript.
  console.log(`${checks} actual UI DOM/stub checks passed; no host, network or model calls.`);
}
verify().catch(error => {console.error(error); process.exitCode = 1;});
