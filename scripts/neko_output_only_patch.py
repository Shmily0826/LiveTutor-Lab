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
CAPTURE_ANCHORS = (
    ('    async function startMicCapture() {\n',
     '        if (globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ === true) return false;\n'),
    ('    async function ensureMicrophonePermission() {\n',
     '        if (globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ === true) return [];\n'),
    ('    async function enumerateAndCacheMediaDevices() {\n',
     '        if (globalThis.__NEKO_OUTPUT_ONLY_CAPTURE_BLOCKED__ === true) return {devices: [], generation: ++mediaDeviceEnumerationGeneration};\n'),
)


def patched_capture(text):
    original=text
    for anchor, addition in CAPTURE_ANCHORS:
        original=original.replace(anchor+addition,anchor)
    if hashlib.sha256(original.encode('utf-8')).hexdigest()!=CAPTURE_BASE_SHA:
        raise ValueError('unknown capture source; preserve source')
    for anchor, addition in CAPTURE_ANCHORS:
        applied=anchor+addition
        if text.count(applied)==1 and text.count(anchor)==1:
            continue
        if text.count(anchor)!=1 or addition.strip() in text:
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
