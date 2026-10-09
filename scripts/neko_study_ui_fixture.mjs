import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import http from 'node:http';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const staticRoot = path.join(root, 'benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/static');
const evidenceRoot = path.join(root, 'benchmarks/raw/evidence');
const gateScript = String.raw`(() => {
  const counts = { audio_context_attempted: 0, audio_context_blocked: 0, speech_synthesis_attempted: 0, speech_synthesis_blocked: 0, media_play_attempted: 0, media_play_blocked: 0, microphone_attempted: 0, microphone_blocked: 0, websocket_attempted: 0, websocket_blocked: 0, external_fetch_attempted: 0, external_fetch_blocked: 0 };
  const denied = (route) => { const error = new Error('N.E.K.O isolated fixture blocked ' + route); error.name = 'NotAllowedError'; return Promise.reject(error); };
  const BlockedAudioContext = class { constructor() { counts.audio_context_attempted++; counts.audio_context_blocked++; throw new Error('audio context blocked by N.E.K.O lab'); } };
  window.AudioContext = BlockedAudioContext;
  window.webkitAudioContext = BlockedAudioContext;
  if (window.speechSynthesis) window.speechSynthesis.speak = function() { counts.speech_synthesis_attempted++; counts.speech_synthesis_blocked++; throw new Error('speech synthesis blocked by N.E.K.O lab'); };
  if (typeof HTMLMediaElement !== 'undefined') HTMLMediaElement.prototype.play = function() { counts.media_play_attempted++; counts.media_play_blocked++; return denied('media playback'); };
  if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = function() { counts.microphone_attempted++; counts.microphone_blocked++; return denied('microphone'); };
  window.WebSocket = class { constructor() { counts.websocket_attempted++; counts.websocket_blocked++; throw new Error('websocket blocked by N.E.K.O lab'); } };
  const localFetch = window.fetch.bind(window);
  window.fetch = function(input, init) {
    const url = new URL(typeof input === 'string' ? input : input.url, window.location.href);
    if (url.origin !== window.location.origin || !(/^\/runs(?:\/|$)/.test(url.pathname) || url.pathname === '/__fixture-state')) {
      counts.external_fetch_attempted++; counts.external_fetch_blocked++;
      return denied('non-fixture network request');
    }
    return localFetch(input, init);
  };
  window.__nekoAudioGate = counts;
})();`;

const scenarioScript = String.raw`(async () => {
  const events = [];
  const overlay = document.createElement('aside');
  overlay.id = 'neko-fixture-run';
  overlay.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:99999;max-width:360px;padding:10px 12px;background:#112126;color:#d8f3e8;border:1px solid #6ab69b;border-radius:10px;font:12px/1.45 system-ui;box-shadow:0 8px 28px #0005';
  overlay.textContent = 'Synthetic local fixture · audio/network sinks blocked';
  document.body.append(overlay);
  const mark = (step) => events.push({ step, at: new Date().toISOString(), visible_reply: document.querySelector('#replyText')?.textContent || '',
    question: document.querySelector('#questionText')?.textContent || '', evaluation: document.querySelector('#evaluationStatus')?.textContent || '' });
  const waitFor = async (check, label) => {
    const deadline = Date.now() + 12000;
    while (Date.now() < deadline) { if (check()) return; await new Promise(r => setTimeout(r, 50)); }
    throw new Error('fixture UI wait timed out: ' + label);
  };
  const setText = (selector, value) => { const el = document.querySelector(selector); if (!el) throw new Error('missing UI control ' + selector); el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); };
  try {
    await waitFor(() => document.querySelector('#studyInput') && !/refreshing/i.test(document.querySelector('#statusLine')?.textContent || ''), 'study UI ready');
    if (new URLSearchParams(location.search).get('scenario') === 'reuse') {
      document.querySelector('#summarizeBtn').click();
      await waitFor(() => (document.querySelector('#replyText')?.textContent || '').includes('本次练习'), 'session reuse after page reload');
      mark('session_reused_after_ui_reload');
      overlay.textContent = 'Fixture complete · session reused after reload · synthetic API';
      window.__nekoStudyUiEvidence = events;
      return;
    }
    document.querySelector('#modeTeachingBtn').click();
    setText('#studyInput', '例题：令 u=x²，求含 x dx 的积分代换。du=2x dx。');
    document.querySelector('#explainBtn').click();
    await waitFor(() => (document.querySelector('#replyText')?.textContent || '').includes('令 u=x²'), 'initial explanation');
    mark('initial_explanation_visible');

    setText('#studyInput', '为什么例题2有1/2？');
    document.querySelector('#explainBtn').click();
    await waitFor(() => (document.querySelector('#replyText')?.textContent || '').includes('½du'), 'follow-up explanation');
    mark('followup_visible');

    document.querySelector('#generateQuestionBtn').click();
    await waitFor(() => (document.querySelector('#questionText')?.textContent || '').includes('若 u=x²'), 'retrieval question');
    mark('question_visible');

    setText('#answerInput', '1/2 du');
    document.querySelector('#evaluateAnswerBtn').click();
    await waitFor(() => /100/.test(document.querySelector('#evaluationStatus')?.textContent || ''), 'answer evaluation');
    mark('answer_evaluated_visible');

    document.querySelector('#summarizeBtn').click();
    await waitFor(() => (document.querySelector('#replyText')?.textContent || '').includes('本次练习'), 'session summary');
    mark('session_summary_visible');
    window.__nekoStudyUiEvidence = events;
    overlay.textContent = 'Fixture complete · explanation → follow-up → question → score → saved session';
    history.replaceState(null, '', '/?scenario=reuse');
    await new Promise(r => setTimeout(r, 250));
    location.reload();
  } catch (error) {
    window.__nekoStudyUiError = String(error?.stack || error);
    overlay.textContent = 'Fixture stopped: ' + String(error?.message || error);
    overlay.style.background = '#4b1f25';
    console.error('N.E.K.O study fixture:', error);
  }
})();`;

function gateProbe() {
  let downstreamExternalCalls = 0;
  let fixtureCalls = 0;
  class Media { play() { downstreamExternalCalls++; return Promise.resolve(); } }
  const speechSynthesis = { speak() { downstreamExternalCalls++; } };
  const calls = [];
  const window = {
    location: { href: 'http://127.0.0.1:41234/' , origin: 'http://127.0.0.1:41234' },
    fetch: async (input) => { const value = String(input); calls.push(value); if (value.startsWith('https://')) downstreamExternalCalls++; else fixtureCalls++; return { ok: true }; },
  };
  window.fetch = window.fetch.bind(window);
  window.speechSynthesis = speechSynthesis;
  const context = { window, navigator: { mediaDevices: { getUserMedia: async () => { downstreamExternalCalls++; } } }, HTMLMediaElement: Media,
    WebSocket: class { constructor() { downstreamExternalCalls++; } }, URL, Error, Promise };
  vm.runInNewContext(gateScript, context, { timeout: 1000 });
  const g = window.__nekoAudioGate;
  for (const attempt of [
    () => new window.AudioContext(),
    () => window.speechSynthesis.speak({ text: 'synthetic test' }),
    () => new Media().play(),
    () => navigator.getUserMedia?.(),
    () => context.navigator.mediaDevices.getUserMedia(),
    () => new window.WebSocket('ws://provider.invalid/audio'),
    () => window.fetch('https://provider.invalid/tts'),
  ]) { try { const result = attempt(); if (result?.catch) result.catch(() => {}); } catch {} }
  window.fetch('/runs', { method: 'POST' });
  if (downstreamExternalCalls !== 0 || fixtureCalls !== 1 || g.audio_context_attempted !== 1 || g.speech_synthesis_attempted !== 1 || g.speech_synthesis_blocked !== 1 || g.media_play_blocked !== 1 ||
      g.microphone_blocked !== 1 || g.websocket_blocked !== 1 || g.external_fetch_blocked !== 1) {
    throw new Error(`audio-gate self-check failed: ${JSON.stringify({ g, downstreamExternalCalls, fixtureCalls })}`);
  }
  if (calls.length !== 1) throw new Error('local fixture route was not preserved by the gate');
  return { ...g, external_downstream_calls: downstreamExternalCalls, local_fixture_requests_observed: fixtureCalls };
}

const browserGateCheckScript = String.raw`(async () => {
  const outcomes = [];
  try { new window.AudioContext(); outcomes.push('audio_context_blocked'); } catch (e) { outcomes.push(e.message.includes('blocked') ? 'audio_context_blocked' : 'audio_context_error'); }
  try { window.speechSynthesis.speak(new SpeechSynthesisUtterance('synthetic test')); outcomes.push('speech_synthesis_open'); } catch { outcomes.push('speech_synthesis_blocked'); }
  const media = document.createElement('audio');
  const actions = [
    media.play().then(() => 'media_play_open').catch(() => 'media_play_blocked'),
    navigator.mediaDevices?.getUserMedia({ audio: true }).then(() => 'microphone_open').catch(() => 'microphone_blocked') ?? Promise.resolve('microphone_unavailable'),
    Promise.resolve().then(() => { new window.WebSocket('wss://provider.invalid/audio'); return 'websocket_open'; }).catch(() => 'websocket_blocked'),
    window.fetch('https://provider.invalid/tts').then(() => 'external_fetch_open').catch(() => 'external_fetch_blocked'),
  ];
  outcomes.push(...await Promise.all(actions));
  const evidence = { at: new Date().toISOString(), outcomes, sinks: window.__nekoAudioGate };
  document.body.textContent = 'N.E.K.O browser audio/network gate check\n' + JSON.stringify(evidence, null, 2);
  window.__nekoBrowserGateEvidence = evidence;
})();`;

let statePath;
let state;
const runs = new Map();
const timestamp = () => new Date().toISOString();
const persist = () => {
  if (statePath) fs.writeFileSync(statePath, JSON.stringify(state, null, 2) + '\n', 'utf8');
};

function responseFor(entry, args = {}) {
  state.api_events.push({ at: timestamp(), entry_id: entry, args: JSON.parse(JSON.stringify(args)) });
  if (entry === 'study_status') return { mode: 'teaching', current_mode: 'teaching', session_id: state.session_id,
    session_count: state.explanations.length, history_count: state.explanations.length, mastery: state.mastery,
    session: { id: state.session_id, state: 'active', turn_count: state.explanations.length },
    screen_type: 'synthetic_lesson', question_status: state.evaluations.length ? 'evaluated' : 'ready' };
  if (entry === 'study_set_mode') return { changed: true, new_mode: 'teaching', transition_phrase: '进入教学模式。' };
  if (entry === 'study_explain_text') {
    const text = String(args.text || '');
    const followup = /为什么.*1\s*\/\s*2|例题2/.test(text);
    const reply = followup
      ? '令 u=x²，则 du=2x dx，因此 x dx=½du。原积分中的 x dx 要替换成 ½du，所以会出现 1/2。'
      : '令 u=x²，那么 du=2x dx，故 x dx=½du。把原积分中对应的 x dx 换成 ½du，就得到这个 1/2。';
    state.explanations.push({ at: timestamp(), text, reply });
    persist();
    return { reply, history_persisted: true, session_id: state.session_id, topic_id: 'substitution' };
  }
  if (entry === 'study_question_context') return { no_data: false, selection_context_id: 'fixture-context-substitution',
    selected_topic_id: 'substitution', selected_topic_name: 'u-substitution', session_id: state.session_id,
    recent_context: state.explanations.slice(-2) };
  if (entry === 'study_generate_targeted_question') return { question_id: 'fixture-q-1', attempt_id: 'fixture-attempt-1',
    selected_topic_id: 'substitution', selected_topic_name: 'u-substitution', difficulty: 'introductory',
    question: '若 u=x²，du=2x dx。积分中 x dx 应替换成什么？', hint: '先把 du=2x dx 两边同时除以 2。' };
  if (entry === 'study_evaluate_answer') {
    const answer = String(args.answer || '');
    const correct = /1\s*\/\s*2|½|0\.5/.test(answer);
    const before = Number(state.mastery.substitution || 0);
    const after = correct ? Math.min(1, before + 0.35) : before;
    state.mastery.substitution = after;
    const result = { verdict: correct ? '正确' : '再想一步', score: correct ? 100 : 20,
      mastery_before: before, mastery_after: after, feedback: correct ? '正确：x dx=½du，因此系数是 1/2。' : '由 du=2x dx，可得 x dx=½du。',
      reference_answer: '½du', covered_points: correct ? ['由 du=2x dx 两边除以 2'] : [],
      missing_points: correct ? [] : ['除以 2'], next_action: '稍后用同一关系再练一次。' };
    state.evaluations.push({ at: timestamp(), answer, ...result });
    persist();
    return result;
  }
  if (entry === 'study_summarize_session') return { summary: `本次练习：${state.explanations.length} 次讲解，${state.evaluations.length} 次作答；u-substitution 掌握度 ${(state.mastery.substitution * 100).toFixed(0)}%。` };
  if (entry === 'study_ocr_snapshot') return { status: 'unavailable', diagnostic: 'fixture_no_screen_capture' };
  if (entry === 'study_get_settings_config') return { config: {}, communication_status: {}, model_runtime: {} };
  if (entry === 'study_memory_list_decks' || entry === 'study_memory_deck') return { decks: [], items: [] };
  if (entry === 'study_dependency_status') return { dependencies: {} };
  return { success: true, fixture: true };
}

function sendJson(res, status, data, headers = {}) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', ...headers });
  res.end(JSON.stringify(data));
}

function createServer() {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    const cors = { 'Access-Control-Allow-Origin': 'http://127.0.0.1' };
    if (url.pathname === '/__audio-gate.js') {
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'no-store' });
      return res.end(gateScript);
    }
    if (url.pathname === '/__study-scenario.js') {
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'no-store' });
      return res.end(scenarioScript);
    }
    if (url.pathname === '/__gate-check.js') {
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'no-store' });
      return res.end(browserGateCheckScript);
    }
    if (url.pathname === '/__audio-gate-check.html') {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8',
        'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'none'; connect-src 'self'; object-src 'none'; base-uri 'none'",
        'permissions-policy': 'microphone=(), camera=(), speaker-selection=()', 'cache-control': 'no-store' });
      return res.end('<!doctype html><html><head><meta charset="utf-8"><title>Audio Gate Check</title><script src="/__audio-gate.js"></script></head><body><script src="/__gate-check.js"></script></body></html>');
    }
    if (url.pathname === '/__fixture-state' && req.method === 'GET') return sendJson(res, 200, state);
    if (url.pathname === '/favicon.ico') { res.writeHead(204); return res.end(); }
    if (url.pathname === '/runs' && req.method === 'POST') {
      let body = '';
      req.on('data', chunk => { body += chunk; if (body.length > 200000) req.destroy(); });
      req.on('end', () => {
        try {
          const request = JSON.parse(body);
          if (request.plugin_id !== 'study_companion' || typeof request.entry_id !== 'string') return sendJson(res, 400, { error: 'fixture_invalid_call' }, cors);
          const id = crypto.randomUUID();
          runs.set(id, responseFor(request.entry_id, request.args || {}));
          return sendJson(res, 200, { run_id: id }, cors);
        } catch { return sendJson(res, 400, { error: 'fixture_invalid_json' }, cors); }
      });
      return;
    }
    const match = url.pathname.match(/^\/runs\/([0-9a-f-]+)(?:\/(export))?$/i);
    if (match && req.method === 'GET') {
      const result = runs.get(match[1]);
      if (!result) return sendJson(res, 404, { error: 'fixture_unknown_run' }, cors);
      if (match[2]) return sendJson(res, 200, { items: [{ type: 'json', json: { success: true, data: result } }] }, cors);
      return sendJson(res, 200, { status: 'succeeded' }, cors);
    }
    if (req.method === 'GET') {
      const rel = url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname.slice(1));
      const normalized = path.normalize(rel);
      if (normalized.startsWith('..') || path.isAbsolute(normalized)) return sendJson(res, 403, { error: 'fixture_path_denied' });
      const filename = path.join(staticRoot, normalized);
      if (!fs.existsSync(filename) || !fs.statSync(filename).isFile()) return sendJson(res, 404, { error: 'fixture_not_found' });
      let body = fs.readFileSync(filename);
      if (normalized === 'index.html') {
        let html = body.toString('utf8');
        html = html.replace('</head>', '<script src="/__audio-gate.js"></script>\n</head>');
        if (url.searchParams.has('scenario')) html = html.replace('</body>', '<script src="/__study-scenario.js"></script>\n</body>');
        body = Buffer.from(html);
      }
      const ext = path.extname(filename).toLowerCase();
      const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' };
      res.writeHead(200, { 'content-type': `${types[ext] || 'application/octet-stream'}; charset=utf-8`,
        'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; style-src-attr 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; media-src 'none'; connect-src 'self'; object-src 'none'; base-uri 'none'",
        'permissions-policy': 'microphone=(), camera=(), speaker-selection=()', 'cache-control': 'no-store' });
      return res.end(body);
    }
    return sendJson(res, 403, { error: 'fixture_route_denied' }, cors);
  });
  server.on('upgrade', (_req, socket) => socket.destroy());
  return server;
}

function main() {
  if (process.argv.includes('--gate-probe')) {
    console.log(JSON.stringify({ phase: 'restart', counts: gateProbe() }));
    return;
  }
  const initial = gateProbe();
  const reload = gateProbe();
  const child = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--gate-probe'], { encoding: 'utf8', timeout: 10000 });
  if (child.status !== 0) throw new Error(`restart audio-gate proof failed: ${child.stderr || child.stdout}`);
  const restart = JSON.parse(child.stdout.trim());
  for (const phase of [initial, reload, restart.counts]) {
    if (phase.audio_context_blocked !== 1 || phase.speech_synthesis_blocked !== 1 || phase.media_play_blocked !== 1 || phase.microphone_blocked !== 1 ||
        phase.websocket_blocked !== 1 || phase.external_fetch_blocked !== 1 || phase.external_downstream_calls !== 0 || phase.local_fixture_requests_observed !== 1) {
      throw new Error(`audio-gate proof failed: ${JSON.stringify(phase)}`);
    }
  }
  const runId = new Date().toISOString().replaceAll(':', '-');
  statePath = process.env.NEKO_STUDY_FIXTURE_STATE || path.join(evidenceRoot, `neko-study-ui-state-${runId}.json`);
  state = fs.existsSync(statePath)
    ? JSON.parse(fs.readFileSync(statePath, 'utf8'))
    : { synthetic_only: true, session_id: 'fixture-substitution-001', explanations: [], evaluations: [], mastery: { substitution: 0.25 }, api_events: [] };
  if (!fs.existsSync(statePath)) persist();
  const stateFile = statePath;
  const manifest = { timestamp_utc: new Date().toISOString(), result: 'AUDIO_GATE_PASS_FIXTURE_ONLY',
    source_ui: 'benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/static',
    audio_gate: { initial, reload, restart: restart.counts }, state_file: stateFile,
    backend: 'synthetic local JSON fixture; no N.E.K.O host, provider, OCR, real study database, or external network',
    allowed_routes: ['GET static assets', 'POST /runs', 'GET /runs/:id', 'GET /runs/:id/export', 'GET /__fixture-state'] };
  fs.mkdirSync(evidenceRoot, { recursive: true });
  const manifestFile = path.join(evidenceRoot, `neko-study-ui-run-${runId}.json`);
  fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
  const server = createServer();
  server.listen(0, '127.0.0.1', () => {
    const address = server.address();
    console.log(JSON.stringify({ ready: true, url: `http://127.0.0.1:${address.port}/`, manifest: manifestFile, state: stateFile,
      audio_gate_verified_before_listen: true, restart_gate: restart.counts }, null, 2));
  });
}

main();
