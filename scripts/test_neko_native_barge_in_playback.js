// Offline production playback module with an in-memory Web Audio sink; no browser/devices.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../benchmarks/raw/neko-product-host/static/app/app-audio-playback.js'), 'utf8');
const websocketSource = fs.readFileSync(path.join(__dirname, '../benchmarks/raw/neko-product-host/static/app/app-websocket.js'), 'utf8');
function websocketBranch(start, end) {
    const from = websocketSource.indexOf(start), to = websocketSource.indexOf(end, from);
    assert.ok(from >= 0 && to > from, 'production WebSocket branch must still be present');
    return websocketSource.slice(from, to);
}
const headerBranch = websocketBranch('                    var speechId = response.speech_id;', '                // -------- audio_done');
const stopBranch = websocketBranch('                    var cancelledCorrelationId = String(', '                // -------- cozy_audio');
function deferred() { let resolve; const promise = new Promise(r => resolve = r); return {promise, resolve}; }
function fixture() {
    const signals = [], sources = [], updates = [];
    const graph = () => ({connect() {}, disconnect() {}, gain: {value: 1}});
    const context = {state: 'running', currentTime: 1, sampleRate: 48000, destination: {},
        createBuffer(_channels, length, rate) { return {duration: length / rate, sampleRate: rate, copyToChannel() {}}; },
        createGain: graph,
        createBufferSource() { const node = {...graph(), stopped: false, start(at) { this.startAt = at; }, stop() { this.stopped = true; }}; sources.push(node); return node; }};
    const S = {scheduledSources: [], audioBufferQueue: [], incomingAudioBlobQueue: [], pendingAudioChunkMetaQueue: [],
        incomingAudioEpoch: 4, seqCounter: 0, audioPlayerContext: context, nextChunkTime: 1,
        globalAnalyser: graph(), lipSyncActive: true, currentPlayingSpeechId: 'reused-speech',
        currentPlayingSpeechCorrelationId: 'native_connection_A', socket: {send(text) { signals.push(JSON.parse(text)); }}};
    const window = {appState: S, appConst: {}, addEventListener() {}, dispatchEvent(event) {
        if (event.type === 'neko-speech-playback-state') updates.push(event.detail);
    }, syncAudioGlobals() {},
        setTimeout() { return 1; }, clearTimeout() {}};
    const sandbox = {window, S, document: {getElementById() { return null; }}, console: {log() {}, warn() {}, error() {}},
        localStorage: {setItem() {}}, CustomEvent: class {
            constructor(type, options) { this.type = type; this.detail = options.detail; }
        }, setTimeout: window.setTimeout, clearTimeout() {},
        logAssistantLifecycle() {}, resolveAssistantLifecycleTurnId() { return ''; },
        applyUserActivityCancel() { throw new Error('native handoff must not enter the global cancellation path'); },
        cancelAnimationFrame() {}, decodeOggOpusChunk: async () => ({float32Data: new Float32Array(2), sampleRate: 48000})};
    vm.createContext(sandbox); vm.runInContext(source, sandbox);
    return {S, api: window.appAudioPlayback, sandbox, sources, signals, updates};
}
const pcm = () => ({arrayBuffer: async () => new Int16Array([1, 2]).buffer});
const ogg = () => ({arrayBuffer: async () => new Uint8Array([79, 103, 103, 83]).buffer});
const tokens = items => Array.from(items, item => item.correlationId);
async function run() {
    let f = fixture();
    await f.api.handleAudioBlob(pcm(), 4, 'reused-speech', '', 1, 'native_connection_A');
    const feedback = f.signals.filter(s => s.action === 'native_speech_playback_state');
    assert.ok(feedback.length > 0);
    assert.ok(feedback.every(s => typeof s.audible === 'boolean'), 'every receipt must preserve audible eligibility');
    assert.equal(feedback.length, f.updates.filter(s => s.correlationId === 'native_connection_A').length,
        'one complete socket receipt per playback update');
    f.S.currentPlayingSpeechCorrelationId = 'native_connection_B';
    await f.api.handleAudioBlob(pcm(), 4, 'reused-speech', '', 1, 'native_connection_B');
    f.api.scheduleAudioChunks(); // advance the existing scheduler's next timer tick
    assert.equal(f.sources.length, 2);
    f.S.audioBufferQueue.push({correlationId: 'native_connection_A'}, {correlationId: 'native_connection_B'});
    f.S.incomingAudioBlobQueue.push({correlationId: 'native_connection_A'}, {correlationId: 'native_connection_B'});
    f.api.cancelNativeConnectionPlayback('native_connection_A');
    f.api.cancelNativeConnectionPlayback('native_connection_A'); // delayed duplicate stop
    assert.equal(f.sources[0].stopped, true);
    assert.equal(f.sources[1].stopped, false);
    assert.deepEqual(tokens(f.S.audioBufferQueue), ['native_connection_B']);
    assert.deepEqual(tokens(f.S.incomingAudioBlobQueue), ['native_connection_B']);
    assert.equal(f.S.incomingAudioEpoch, 4);

    for (const duringDecode of [false, true]) {
        f = fixture(); const gate = deferred(); const entered = deferred();
        const blob = duringDecode ? ogg() : {arrayBuffer() { entered.resolve(); return gate.promise; }};
        if (duringDecode) f.sandbox.decodeOggOpusChunk = async () => { entered.resolve(); return gate.promise; };
        const pending = f.api.handleAudioBlob(blob, 4, 'reused-speech', '', 1, 'native_connection_A');
        await entered.promise;
        f.api.cancelNativeConnectionPlayback('native_connection_A');
        gate.resolve(duringDecode ? {float32Data: new Float32Array(2), sampleRate: 48000} : new Int16Array([1, 2]).buffer);
        await pending;
        assert.equal(f.sources.length, 0, 'retired decode must never reach a playing source');
        f.S.currentPlayingSpeechCorrelationId = 'native_connection_B';
        await f.api.handleAudioBlob(pcm(), 4, 'reused-speech', '', 1, 'native_connection_B');
        assert.equal(f.sources.length, 1, 'new reply survives old in-flight decoding');
        assert.equal(f.sources[0]._nekoSpeechCorrelationId, 'native_connection_B');
        f.api.cancelNativeConnectionPlayback('native_connection_A');
        assert.equal(f.sources[0].stopped, false);
    }
    f = fixture(); f.S.isProcessingIncomingAudioBlob = true;
    f.S.pendingAudioChunkMetaQueue.push(
        {speechId: 'reused-speech', correlationId: 'native_connection_A', epoch: 4},
        {speechId: 'reused-speech', correlationId: 'native_connection_B', epoch: 4});
    f.api.cancelNativeConnectionPlayback('native_connection_A');
    f.api.enqueueIncomingAudioBlob(pcm());
    assert.equal(f.S.incomingAudioBlobQueue.length, 0);
    f.api.enqueueIncomingAudioBlob(pcm());
    assert.deepEqual(tokens(f.S.incomingAudioBlobQueue), ['native_connection_B'], 'old blob consumes only its own metadata');
    f.S.isProcessingIncomingAudioBlob = false;
    await f.api.processIncomingAudioBlobQueue();
    assert.equal(f.sources.length, 1);
    f.api.cancelNativeConnectionPlayback('native_connection_A');
    assert.equal(f.sources[0].stopped, false);

    f = fixture(); const gate = deferred();
    const pending = f.api.handleAudioBlob({arrayBuffer: () => gate.promise}, 4, 'reused-speech', '', 1, 'native_connection_A');
    f.S.incomingAudioEpoch = 5; // existing frontend reconnect fence
    gate.resolve(new Int16Array([1, 2]).buffer); await pending;
    f.S.currentPlayingSpeechCorrelationId = 'native_connection_C';
    await f.api.handleAudioBlob(pcm(), 5, 'reused-speech', '', 1, 'native_connection_C');
    f.api.cancelNativeConnectionPlayback('native_connection_A');
    assert.equal(f.sources.length, 1); assert.equal(f.sources[0].stopped, false);
    assert.ok(f.signals.some(s => s.action === 'native_speech_playback_state' && s.active), 'Electron-style socket heartbeat is forwarded');
    console.log('PASS: queued/playing old audio, late stop, same speech ID, arrayBuffer/decoder in flight, metadata pairing, reconnect, next reply');
}
async function handoff(messages) {
    const old = messages.stop.sdk_speech_correlation_id, next = messages.header.sdk_speech_correlation_id;
    const f = fixture();
    async function audio(header) {
        f.sandbox.response = header;
        vm.runInContext(headerBranch, f.sandbox);
        f.S.isProcessingIncomingAudioBlob = true;
        f.api.enqueueIncomingAudioBlob(pcm());
        f.S.isProcessingIncomingAudioBlob = false;
        await f.api.processIncomingAudioBlobQueue();
    }
    function stop() {
        f.sandbox.response = messages.stop;
        vm.runInContext(stopBranch, f.sandbox);
    }
    await audio({...messages.header, sdk_speech_correlation_id: old});
    stop();
    assert.equal(f.S.isPlaying, false, 'retired playback must release the old speaking flag');
    await audio(messages.header);
    f.api.scheduleAudioChunks();
    stop();
    assert.equal(f.sources[0].stopped, true); assert.equal(f.sources[1].stopped, false);
    assert.equal(f.sources[1]._nekoSpeechCorrelationId, next);
    console.log('PASS: production host handoff events -> production frontend cancellation and surviving answer');
}
(process.argv.includes('--handoff') ? handoff(JSON.parse(fs.readFileSync(0, 'utf8'))) : run()).catch(error => { console.error(error); process.exitCode = 1; });
