import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('./neko_capture_policy.js', import.meta.url), 'utf8');
const flag = '__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__';
const modern = ['getUserMedia', 'getDisplayMedia', 'enumerateDevices'];
const legacy = ['getUserMedia', 'webkitGetUserMedia', 'mozGetUserMedia'];

function fixture(options = {}) {
    let originalsCalled = 0;
    let outputsCalled = 0;
    const original = () => { originalsCalled++; throw new Error('Real capture called'); };
    const output = function FakeOutputOnly() { outputsCalled++; };
    const devices = Object.fromEntries(modern.map(key => [key, original]));
    devices.selectAudioOutput = output;
    const nav = {mediaDevices: devices, ...Object.fromEntries(legacy.map(key => [key, original]))};
    const sandbox = {navigator: nav, DOMException, AudioContext: output, webkitAudioContext: output,
        Audio: output, speechSynthesis: {speak: output}, HTMLMediaElement: {prototype: {play: output}},
        SpeechRecognition:original, webkitSpeechRecognition:original};
    options.configure?.(sandbox, nav, devices);
    const context = vm.createContext(sandbox);
    vm.runInContext(source, context);
    return {context, sandbox, nav, devices, output, original, called: () => originalsCalled,
        outputCalled: () => outputsCalled,
        install: () => vm.runInContext('NekoCapturePolicy.installOutputOnly({enabled:true})', context)};
}

function expectFailure(env) {
    assert.throws(env.install, error => error.code === 'NEKO_CAPTURE_POLICY_INSTALL_FAILED' &&
        error.receipt.status === 'failed' && error.receipt.captureBlocked === false);
    assert.notEqual(env.sandbox[flag], true);
    assert.equal(env.sandbox.NekoCapturePolicy.getResult().status, 'failed');
    assert.equal(env.called(), 0);
}

test('plain load and non-boolean opt-in do not publish safety or change capture', () => {
    const env = fixture();
    assert.equal(env.sandbox.NekoCapturePolicy.getResult(), null);
    assert.equal(Object.hasOwn(env.sandbox, flag), false);
    for (const option of ['undefined', '{}', '{enabled:false}', '{enabled:1}', '{enabled:"true"}']) {
        const result = vm.runInContext(`NekoCapturePolicy.installOutputOnly(${option})`, env.context);
        assert.equal(result.status, 'disabled');
        assert.equal(result.captureBlocked, false);
    }
    assert.equal(env.devices.getUserMedia, env.original);
    assert.equal(Object.hasOwn(env.sandbox, flag), false);
    assert.equal(env.called(), 0);
    assert.equal(env.outputCalled(), 0);
});

test('modern APIs reject all constraints without invoking originals', async () => {
    const env = fixture();
    const receipt = env.install();
    assert.equal(receipt.status, 'installed');
    for (const name of modern) {
        for (const constraints of [undefined, {audio:true}, {video:true}, {audio:false, video:false}]) {
            await assert.rejects(env.devices[name](constraints), error => error.name === 'NotAllowedError');
        }
    }
    assert.equal(env.called(), 0);
    assert.equal(receipt.blocked.length, 8);
});

test('browser speech recognition cannot initialize an independent microphone', () => {
    const env=fixture();env.install();
    for (const name of ['SpeechRecognition','webkitSpeechRecognition']) {
        assert.throws(() => new env.sandbox[name](),error=>error.name==='NotAllowedError');
        assert.equal(Object.getOwnPropertyDescriptor(env.sandbox,name).writable,false);
    }
    assert.equal(env.called(),0);
});

test('legacy APIs only call error callback and reject missing callbacks', async () => {
    const env = fixture();
    env.install();
    for (const name of legacy) {
        let success = false;
        const error = await new Promise(resolve => env.nav[name]({audio:true}, () => {success=true;}, resolve));
        assert.equal(error.name, 'NotAllowedError');
        assert.equal(success, false);
        assert.throws(() => env.nav[name]({video:true}), error => error.name === 'NotAllowedError');
    }
    assert.equal(env.called(), 0);
});

test('successful API/reference/flag locks cannot be overwritten; repeat install is idempotent', () => {
    const env = fixture();
    const receipt = env.install();
    assert.equal(env.install(), receipt);
    assert.equal(env.sandbox[flag], true);
    assert.equal(Object.isFrozen(receipt), true);
    assert.equal(Object.isFrozen(receipt.blocked), true);
    for (const [target, key] of [[env.sandbox, flag], [env.sandbox, 'navigator'],
        [env.nav, 'mediaDevices'], ...modern.map(key => [env.devices,key]), ...legacy.map(key => [env.nav,key])]) {
        const descriptor = Object.getOwnPropertyDescriptor(target, key);
        assert.equal(descriptor.writable, false);
        assert.equal(descriptor.configurable, false);
        assert.throws(() => Object.defineProperty(target, key, {value: env.original}), TypeError);
    }
});

test('output constructors and playback APIs retain exact references and are never constructed', () => {
    const env = fixture();
    const before = [env.sandbox.AudioContext, env.sandbox.webkitAudioContext, env.sandbox.Audio,
        env.sandbox.speechSynthesis.speak, env.sandbox.HTMLMediaElement.prototype.play, env.devices.selectAudioOutput];
    env.install();
    assert.deepEqual([env.sandbox.AudioContext, env.sandbox.webkitAudioContext, env.sandbox.Audio,
        env.sandbox.speechSynthesis.speak, env.sandbox.HTMLMediaElement.prototype.play, env.devices.selectAudioOutput], before);
    assert.equal(env.called(), 0);
    assert.equal(env.outputCalled(), 0);
});

test('missing optional method is locked denial, including future prototype implementations', async () => {
    const env = fixture({configure(_sandbox, nav, devices) {
        for (const key of modern) delete devices[key];
        for (const key of legacy) delete nav[key];
    }});
    env.install();
    Object.setPrototypeOf(env.devices, {getUserMedia: env.original});
    await assert.rejects(env.devices.getUserMedia(), error => error.name === 'NotAllowedError');
    assert.equal(env.called(), 0);
});

test('missing navigator or mediaDevices fails closed without a successful flag', () => {
    for (const configure of [s => {delete s.navigator;}, (_s,n) => {delete n.mediaDevices;}]) expectFailure(fixture({configure}));
});

test('readonly own capture method fails preflight before any mutation', () => {
    const env = fixture({configure(_s,_n,d) {Object.defineProperty(d,'getDisplayMedia',{value:d.getDisplayMedia,writable:false,configurable:false});}});
    expectFailure(env);
    assert.equal(env.devices.getUserMedia, env.original);
    assert.equal(env.nav.getUserMedia, env.original);
    assert.throws(env.install, error => error.receipt.status === 'failed');
});

test('readonly mediaDevices accessor, frozen owner, or absent DOMException fails closed', () => {
    const configurations = [
        (_s,n,d) => Object.defineProperty(n,'mediaDevices',{get:()=>d,configurable:false}),
        (_s,n) => Object.freeze(n),
        s => {delete s.DOMException;}
    ];
    for (const configure of configurations) expectFailure(fixture({configure}));
});

test('inherited readonly methods can be safely shadowed without calling them', async () => {
    const env = fixture({configure(_s,_n,d) {
        const proto = {};
        Object.defineProperty(proto,'getUserMedia',{value:d.getUserMedia,writable:false,configurable:false});
        delete d.getUserMedia;
        Object.setPrototypeOf(d,proto);
    }});
    env.install();
    await assert.rejects(env.devices.getUserMedia(), error => error.name === 'NotAllowedError');
    assert.equal(env.called(), 0);
});

test('non-configurable but writable own methods may be replaced and locked', async () => {
    const env = fixture({configure(_s,_n,d) {
        Object.defineProperty(d,'getUserMedia',{value:d.getUserMedia,writable:true,configurable:false,enumerable:true});
    }});
    env.install();
    await assert.rejects(env.devices.getUserMedia(), error => error.name === 'NotAllowedError');
    assert.equal(Object.getOwnPropertyDescriptor(env.devices,'getUserMedia').writable, false);
    assert.equal(Object.getOwnPropertyDescriptor(env.devices,'getUserMedia').enumerable, true);
    assert.equal(env.called(), 0);
});

test('late host-object define failure never claims success or restores live capture', async () => {
    const env = fixture({configure(_s,n,d) {
        n.mediaDevices = new Proxy(d, {defineProperty(target,key,descriptor) {
            if (key === 'getDisplayMedia') throw new Error('Host object refused');
            return Reflect.defineProperty(target,key,descriptor);
        }});
    }});
    expectFailure(env);
    await assert.rejects(env.nav.mediaDevices.getUserMedia(), error => error.name === 'NotAllowedError');
    assert.equal(env.called(), 0);
});

test('conflicting policy markers are rejected, never treated as an installed receipt', () => {
    const env = fixture({configure(s) {s.__NEKO_CAPTURE_POLICY_RESULT__ = {status:'installed'};}});
    expectFailure(env);
    assert.equal(env.devices.getUserMedia, env.original);
});
