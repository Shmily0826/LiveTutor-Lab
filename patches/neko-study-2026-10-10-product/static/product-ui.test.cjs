const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(`${__dirname}/main.js`, 'utf8');
const block = (start, end) => {
  const from = source.indexOf(start), to = source.indexOf(end, from);
  assert.ok(from >= 0 && to > from, `Current source block missing: ${start} -> ${end}`);
  return source.slice(from, to);
};

function harness() {
  const calls = [];
  const status = [];
  const delays = [];
  const input = () => ({value: '', textContent: '', hidden: true, focus() { this.focused = true; }});
  const elements = new Map([['windowCaptureOptions', {open: true}]]);
  const context = vm.createContext({
    studyInput: input(), ocrWindowTitle: input(), ocrExpectedMarkers: input(),
    ocrSelectedWindow: input(), studyCourseId: input(), selectedStudyCourse: input(),
    answerInput: input(), usePreviousExplanation: {checked: true, disabled: false},
    setStatus: (value) => status.push(value), setReply: () => {},
    t: (_key, fallback) => fallback, $id: (id) => elements.get(id) || null,
    setPasteError: () => {}, studyMaterialControlNotice: input(),
    questionAttemptMeta: input(), document: {},
    sleep: async (ms) => delays.push(ms), setImagePreview: () => {},
    setGeneratedQuestion: () => {}, setQuestionContext: () => {}, clearFeedback: () => {},
    refreshStatus: async () => {},
    callPlugin: async (entry, args) => {
      calls.push({entry, args});
      return entry === 'study_get_practice_scope' ? {no_data: true} : context.response;
    },
  });
  vm.runInContext("let ocrN='old title', ocrT='old OCR', previousExplanation={input:'Flutter'}, currentQuestion={}, currentSelectionContext={}, currentPracticeScope={}; let studyMaterialRevision=0, lastStatusPayload={}, studyServiceReady=true, hasInitializedCourseInput=false;", context);
  vm.runInContext(block('function studySessionId(', 'async function refreshMaterialControl('), context);
  vm.runInContext(block('function studyContextIsCurrent(', 'function normalizeVisionMaxImagePx('), context);
  vm.runInContext(block('async function refreshAfterSuccess(', 'async function loadQuestionContext('), context);
  vm.runInContext(block('function clearOcrAttribution(', 'function buildFollowupText('), context);
  context.studyInput.value = 'old OCR';
  context.ocrWindowTitle.value = 'LiveTutor Flutter Lesson';
  context.ocrExpectedMarkers.value = 'ChangeNotifier\ncontext.watch';
  context.response = {status: 'ok', text: 'raw OCR\nChangeNotifier context.watch',
    capture_mode_used: 'target_window', target_window_title: 'LiveTutor Flutter Lesson', target_window_markers_matched: 2};
  return {context, calls, status, delays, elements};
}

(async () => {
  const good = harness();
  await good.context.runOcr();
  assert.equal(good.calls.length, 1);
  assert.equal(good.calls[0].entry, 'study_ocr_snapshot');
  assert.equal(good.calls[0].args.capture_mode, 'target_window');
  assert.equal(good.calls[0].args.allow_fullscreen_fallback, false);
  assert.equal(good.calls[0].args.min_marker_matches, 2);
  assert.deepEqual(good.delays, [1000, 1000, 1000, 1000, 1000]);
  assert.equal(good.context.studyInput.value, good.context.response.text);
  assert.equal(good.context.ocrSelectedWindow.hidden, false);

  const closed = harness(); closed.elements.get('windowCaptureOptions').open = false;
  await closed.context.runOcr();
  assert.equal(closed.elements.get('windowCaptureOptions').open, true);
  assert.equal(closed.context.ocrWindowTitle.focused, true);
  assert.equal(closed.calls.length, 0, 'Opening the window fields must not request capture');
  assert.deepEqual(closed.delays, []);

  for (const invalid of ['', '\n ', Array.from({length: 13}, (_, i) => `marker${i}`).join('\n')]) {
    const h = harness(); h.context.ocrExpectedMarkers.value = invalid;
    await assert.rejects(h.context.runOcr());
    assert.equal(h.calls.length, 0);
    assert.equal(h.context.studyInput.value, '');
    assert.equal(h.context.ocrSelectedWindow.hidden, true);
  }
  const missingTitle = harness(); missingTitle.context.ocrWindowTitle.value = '';
  await assert.rejects(missingTitle.context.runOcr());
  assert.equal(missingTitle.calls.length, 0);
  for (const change of [{status:'empty'}, {capture_mode_used:'fullscreen'}, {target_window_title:'Personal'}, {target_window_markers_matched:1}]) {
    const h = harness(); Object.assign(h.context.response, change);
    await assert.rejects(h.context.runOcr());
    assert.equal(h.calls.length, 1);
    assert.equal(h.context.studyInput.value, '');
    assert.equal(h.context.ocrSelectedWindow.hidden, true);
  }
  const transport = harness(); transport.context.callPlugin = async () => { throw new Error('TARGET_WINDOW_NOT_FOREGROUND'); };
  await assert.rejects(transport.context.runOcr());
  assert.equal(transport.context.studyInput.value, '');
  assert.equal(transport.context.ocrSelectedWindow.hidden, true);

  const course = harness(); course.context.studyCourseId.value = 'flutter-provider';
  course.context.response = {course_id:'flutter-provider'};
  await course.context.startCourseSession();
  assert.equal(course.calls[0].entry, 'study_start_session');
  assert.equal(course.calls[0].args.course_id, 'flutter-provider');
  assert.equal(course.context.usePreviousExplanation.checked, false);
  assert.equal(course.context.usePreviousExplanation.disabled, true);
  assert.equal(vm.runInContext('previousExplanation', course.context), null);
  assert.equal(course.context.studyInput.value, '');

  const busy = vm.createContext({t: (_key, fallback) => fallback, setStatus: () => {},
    setReply: () => {}, formatPluginError: String, $id: () => ({setAttribute: () => {}})});
  vm.runInContext('let uiActionInFlight=false;', busy);
  vm.runInContext(block('function bindButton(', 'async function handleNekoCoachAction('), busy);
  const button = () => ({textContent: 'Explain', disabled: false, addEventListener(_event, handler) { this.click = handler; }});
  const first = button(), second = button();
  let release, secondCalls = 0;
  busy.bindButton(first, () => new Promise((resolve) => { release = resolve; }));
  busy.bindButton(second, async () => { secondCalls += 1; });
  const pending = first.click();
  assert.equal(first.textContent, '处理中…');
  assert.equal(first.disabled, true);
  await second.click();
  assert.equal(secondCalls, 0, 'Concurrent UI actions must not mix capture and provider requests');
  release(); await pending;
  assert.equal(first.textContent, 'Explain');
  assert.equal(first.disabled, false);
  await second.click();
  assert.equal(secondCalls, 1);

  const courseStatus = harness().context;
  Object.assign(courseStatus, {modeLabel: String,
    setStatus: () => {}, syncLearningProfileUi: () => {}, renderDiagnosis: () => {},
    renderFirstRunGuide: () => {}, updateStudySummaries: () => {}, renderNekoCoach: () => {},
    setModeButtons: () => {}, setStudyState: () => {}});
  courseStatus.studyCourseId.value = 'flutter-provider';
  vm.runInContext(block('function syncStatusQuestion(', 'function setStatusLine('), courseStatus);
  vm.runInContext(block('function setStatusLine(', 'function setAdvancedSettingsOpen('), courseStatus);
  courseStatus.setStatusLine({study_course_id: 'networking'});
  assert.equal(courseStatus.studyCourseId.value, 'networking', 'Existing selected course takes priority over demo default');
  courseStatus.studyCourseId.value = 'my-next-course';
  courseStatus.setStatusLine({study_course_id: 'networking'});
  assert.equal(courseStatus.studyCourseId.value, 'my-next-course', 'Status refresh must preserve user edits');
  assert.equal(courseStatus.selectedStudyCourse.textContent, '当前课程：networking');

  for (const fromMaterial of [false, true]) {
    const quiz = harness();
    Object.assign(quiz.context, {t: (_key, fallback) => fallback, openPracticePanel: () => {},
      setPracticeScopeState: () => {}, loadQuestionContext: async () => ({no_data: true})});
    vm.runInContext(block('function buildFollowupText(', 'async function explainText('), quiz.context);
    vm.runInContext(block('async function generateQuestion(', 'async function evaluateAnswer('), quiz.context);
    quiz.context.studyInput.value = 'COMPSCI 734 风格：请针对 context.watch 出一道选择题';
    quiz.context.response = {question: 'Which widget rebuilds?', question_id: 'q1', attempt_id: 'a1'};
    await quiz.context.generateQuestion({fromMaterial});
    assert.deepEqual(quiz.calls.map(call => call.entry), fromMaterial
      ? ['study_generate_question'] : ['study_get_practice_scope', 'study_generate_question']);
    const generated = quiz.calls.find(call => call.entry === 'study_generate_question');
    assert.ok(generated.args.text.includes('COMPSCI 734'));
    assert.ok(generated.args.text.includes('context.watch'));
  }

  const coach = block('async function handleNekoCoachAction(', 'const documentController');
  assert.ok(!coach.includes('runOcr('), 'Coach explanation must not start capture');
  assert.ok(!source.includes("capture_mode: 'interactive'"));
  assert.ok(!source.includes('interactiveOcrFallbackMessage'));
  console.log('PASS: safe OCR args/countdown/raw text/refusals; capture uses one OCR entry and no provider; course resets context; coach has no capture chain.');
})().catch((error) => { console.error(error); process.exitCode = 1; });
