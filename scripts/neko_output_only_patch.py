"""Replay the opt-in output-only bootstrap onto both pinned source trees."""
import ast
import hashlib
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
HOSTS = (ROOT/'benchmarks/raw/neko-product-host', ROOT/'candidates/N.E.K.O')
RELATIVE = 'app/main_server/web_app.py'
BEFORE = 'app = runtime.app\nlogger = runtime.logger\n'
AFTER = BEFORE + '\nfrom main_logic.livetutor_output_only import install_output_only\ninstall_output_only(app)\n'
BASE_SHA = '2eb8e78f6a7c49e75a574bee575b22b03ca6409013a6bc7794832599bba7f861'
CAPTURE_RELATIVE = 'static/app/app-audio-capture.js'
CAPTURE_BASE_SHA = 'e609d90cb6731a9edb20a41997007ebd299ad2ac911d162d0eb5a9308d9940ad'
FIXED_INPUT_HELPERS = '''    // Memory PCM participates in the existing controller; it never opens capture.
    let fixedInputSource = null;
    let fixedInputSequence = 0;

    function fixedInputBlocked(socket) {
        return globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ !== true
            || !socket || socket !== S.socket || socket.readyState !== WebSocket.OPEN
            || S.isRecording === true || S.voiceStartPending === true || window.isMicStarting === true
            || S.isMicMuted === true || S.gameVoiceSttGateActive === true
            || (S.focusModeEnabled === true && S.isPlaying === true)
            || S.voiceInputRouteBlocked === true || isVoiceInputRecoveryPending()
            || (window.nekoVoiceCaptureReadiness && window.nekoVoiceCaptureReadiness.blocked())
            || S.voiceInputRecoveryState === 'failed';
    }

    function fixedInputIsCurrent() {
        if (fixedInputSource) {
            let blocked = true;
            try { blocked = fixedInputBlocked(fixedInputSource.socket); } catch (_) {}
            if (blocked) fixedInputSource = null;
        }
        return fixedInputSource !== null;
    }

    function beginFixedInput() {
        if (fixedInputIsCurrent() || fixedInputBlocked(S.socket)) {
            throw new Error('Fixed input refused by current controller state');
        }
        fixedInputSource = {id: ++fixedInputSequence, socket: S.socket};
        try {
            refreshMicLease();
            return fixedInputState(fixedInputSource.id);
        } catch (error) {
            fixedInputSource = null;
            throw error;
        }
    }

    function fixedInputState(id) {
        refreshMicLease();
        const current = fixedInputIsCurrent();
        return {
            active: current && fixedInputSource.id === id,
            id: current ? fixedInputSource.id : null,
            lease_generation: S.voiceInputCurrentLeaseGeneration,
            owner: resolveMicLeaseOwner(),
            capture_started: S.isRecording === true
        };
    }

    function sendFixedInputFrame(id, samples) {
        if (!Array.isArray(samples) || samples.length < 1 || samples.length > 480
                || samples.some(x => !Number.isInteger(x) || x < -32768 || x > 32767)) return false;
        const state = fixedInputState(id);
        if (!state.active || state.owner !== MIC_LEASE.CORE || !canUploadOrdinaryMicFrame()) return false;
        if (!fixedInputIsCurrent() || fixedInputSource.id !== id) return false;
        // No await between identity validation and submission to this exact socket.
        fixedInputSource.socket.send(JSON.stringify({action: 'stream_data', input_type: 'audio', data: samples}));
        return true;
    }

    function endFixedInput(id) {
        if (!fixedInputSource || fixedInputSource.id !== id) return false;
        const socket = fixedInputSource.socket;
        fixedInputSource = null;
        if (socket === S.socket && socket.readyState === WebSocket.OPEN) refreshMicLease();
        return true;
    }

'''
FIXED_CONTROL_HELPERS = '''    function sendFixedInputControl(id, command) {
        if (!command || !['start_session', 'end_session', 'end_audio_turn', 'ping'].includes(command.action)) return false;
        if (command.action === 'start_session' && command.input_type !== 'audio') return false;
        const state = fixedInputState(id);
        if (!state.active || !fixedInputIsCurrent() || fixedInputSource.id !== id) return false;
        const socket = fixedInputSource.socket;
        socket.send(JSON.stringify(command));
        // End and release share one synchronous validated-source operation.
        if (command.action === 'end_session') endFixedInput(id);
        return true;
    }

'''
FIXED_INPUT_HELPERS += FIXED_CONTROL_HELPERS
FIXED_EXPORTS_OLD = '    mod.beginFixedInput = beginFixedInput;\n    mod.fixedInputState = fixedInputState;\n    mod.sendFixedInputFrame = sendFixedInputFrame;\n    mod.endFixedInput = endFixedInput;\n'
FIXED_EXPORTS = FIXED_EXPORTS_OLD + '    mod.sendFixedInputControl = sendFixedInputControl;\n'
CAPTURE_ANCHORS = (
    ('    async function startMicCapture() {\n',
     '        if (globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ === true) return false;\n'),
    ('    async function ensureMicrophonePermission() {\n',
     '        if (globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ === true) return [];\n'),
    ('    async function enumerateAndCacheMediaDevices() {\n',
     '        if (globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ === true) return {devices: [], generation: ++mediaDeviceEnumerationGeneration};\n'),
    ('    let microphoneSelectionGeneration = 0;\n\n', FIXED_INPUT_HELPERS),
    ('            engaged: (\n', '                fixedInputIsCurrent() ||\n'),
    ('    function resolveMicLeaseOwner() {\n', '        if (fixedInputIsCurrent()) return MIC_LEASE.CORE;\n'),
    ('    mod.refreshMicLease = refreshMicLease;\n',
     FIXED_EXPORTS),
)


def patched_capture(text):
    # Exact replay of the sole local draft, retaining fail-closed base validation.
    pre_exception_helpers = FIXED_INPUT_HELPERS.replace(
        '        if (fixedInputSource) {\n            let blocked = true;\n            try { blocked = fixedInputBlocked(fixedInputSource.socket); } catch (_) {}\n            if (blocked) fixedInputSource = null;\n        }',
        '        if (fixedInputSource && fixedInputBlocked(fixedInputSource.socket)) fixedInputSource = null;')
    previous_helpers = pre_exception_helpers.replace(FIXED_CONTROL_HELPERS, '').replace(
        '            || (window.nekoVoiceCaptureReadiness && window.nekoVoiceCaptureReadiness.blocked())\n', '').replace(
        '        const socket = fixedInputSource.socket;\n        fixedInputSource = null;\n        if (socket === S.socket && socket.readyState === WebSocket.OPEN) refreshMicLease();',
        '        fixedInputSource = null;\n        refreshMicLease();')
    earliest_helpers = previous_helpers.replace(
        '        refreshMicLease();\n        const current = fixedInputIsCurrent();',
        '        const current = fixedInputIsCurrent();\n        refreshMicLease();').replace(
        '        if (!fixedInputIsCurrent() || fixedInputSource.id !== id) return false;\n', '')
    helper_anchor = '    let microphoneSelectionGeneration = 0;\n\n'
    for known in (pre_exception_helpers, previous_helpers, earliest_helpers):
        text = text.replace(helper_anchor + known, helper_anchor + FIXED_INPUT_HELPERS)
    export_anchor = '    mod.refreshMicLease = refreshMicLease;\n'
    # Only the full old export block qualifies; do not match a current prefix.
    text = text.replace(export_anchor + FIXED_EXPORTS_OLD + '    mod.sendVoiceInputControlState',
                        export_anchor + FIXED_EXPORTS + '    mod.sendVoiceInputControlState')
    original=text
    for anchor, addition in CAPTURE_ANCHORS:
        original=original.replace(anchor+addition,anchor)
    if hashlib.sha256(original.encode('utf-8')).hexdigest()!=CAPTURE_BASE_SHA:
        raise ValueError('unknown capture source; preserve source')
    for anchor, addition in CAPTURE_ANCHORS:
        applied=anchor+addition
        if text.count(applied)==1 and text.count(anchor)==1:
            continue
        if text.count(anchor)!=1:
            raise ValueError('unknown capture-skip anchor; preserve source')
        text=text.replace(anchor,applied,1)
    return text


def patched_web_app(text):
    if text.count(AFTER) == 1 and text.count(BEFORE) == 1:
        if hashlib.sha256(text.replace(AFTER, BEFORE, 1).encode('utf-8')).hexdigest() != BASE_SHA:
            raise ValueError('unknown previously patched web app; preserve source')
        return text
    if (text.count(BEFORE) != 1 or 'livetutor_output_only' in text
            or hashlib.sha256(text.encode('utf-8')).hexdigest() != BASE_SHA):
        raise ValueError('unknown output-only bootstrap anchor; preserve source')
    result = text.replace(BEFORE, AFTER, 1)
    ast.parse(result)
    return result


def apply_to(path):
    target = path/RELATIVE
    current = target.read_bytes()
    text = current.decode('utf-8').replace('\r\n', '\n')
    result = patched_web_app(text).encode('utf-8')
    capture_target=path/CAPTURE_RELATIVE
    capture_current=capture_target.read_bytes()
    capture_result=patched_capture(capture_current.decode('utf-8').replace('\r\n','\n')).encode('utf-8')
    # Validate before replacing either target or copying any helper.
    for name in ('neko_output_only_runtime.py', 'neko_capture_policy.js'):
        source = ROOT/'scripts'/name
        if not source.is_file():
            raise FileNotFoundError(name)
        if source.suffix == '.py':
            ast.parse(source.read_text(encoding='utf-8'))
    if result != current:
        target.write_bytes(result)
    if capture_result != capture_current:
        capture_target.write_bytes(capture_result)
    for source, relative in ((ROOT/'scripts/neko_output_only_runtime.py', 'main_logic/livetutor_output_only.py'),
                             (ROOT/'scripts/neko_capture_policy.js', 'static/app/neko-capture-policy.js')):
        output = path/relative
        output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,output)
    return hashlib.sha256(result).hexdigest()


if __name__ == '__main__':
    for path in HOSTS:
        print(path.name, apply_to(path))
