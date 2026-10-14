"""Give explicit source-reasoning requests an immediate existing Focus signal."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = 'main_logic/activity/focus_scorer.py'
BASE = '361fe50e2122d0a8a7bfec3b24116d68d6159f00b55db01bbf976092ab6b1a1e'
MARKER = '# daily-source-focus-v1'
SIGNAL = '''# daily-source-focus-v1
_SOURCE_CUE = re.compile(
    r"源码|源代码|\\bsource\\s+code\\b|\\bcode\\b|"
    r"\\b[\\w.-]+\\.(?:dart|js|ts|tsx|jsx|py|kt|java|cpp|cs|go|rs)\\b", re.I)
_REASONING_CUE = re.compile(
    r"解释|推理|条件|校验|改名|改动|调换|交换|影响|纠正|追踪|调用|流程|为什么|"
    r"\\b(?:explain|why|trace|swap|rename|change|impact|validate|validation|condition|calls?|flow|correct)\\b", re.I)
_READ_ONLY_CUE = re.compile(
    r"只(?:读|显示|展示)|不要(?:解释|推理|思考)|不(?:用|必)(?:解释|推理|思考)|"
    r"\\b(?:just\\s+(?:read|show)|no\\s+reasoning|do\\s+not\\s+(?:explain|reason))\\b", re.I)


def _source_reasoning_request(user_text: str) -> bool:
    return bool(_SOURCE_CUE.search(user_text) and _REASONING_CUE.search(user_text)
                and not _READ_ONLY_CUE.search(user_text))


'''
EDITS = [
    ('from collections import deque\n', 'from collections import deque\nimport re\n'),
    ('class FocusScorer:\n', SIGNAL+'class FocusScorer:\n'),
    ('        question = self._signal_question(emotion_reading)\n',
     '        question = self._signal_question(emotion_reading)\n'
     '        if _source_reasoning_request(user_text):\n'
     '            question = 1.0  # Current explicit request; no stale reading needed.\n'),
]


def patch_scorer(source):
    if MARKER in source:
        ast.parse(source)
        return source
    for old,new in EDITS:
        if source.count(old)!=1:
            raise ValueError('Source Focus anchor changed; preserve source')
        source=source.replace(old,new,1)
    ast.parse(source)
    return source


def apply_to(host_root):
    expected=ROOT/'benchmarks/raw/neko-product-host'
    if host_root.is_symlink() or host_root.resolve()!=expected.resolve():
        raise ValueError('Source Focus patch is for the actual source host only')
    target=host_root/RELATIVE
    if target.is_symlink() or not target.resolve().is_relative_to(host_root.resolve()):
        raise ValueError('Source Focus target escapes host')
    manifest=json.loads((ROOT/'patches/neko-study-2026-10-10-host/manifest.json').read_text(encoding='utf-8'))
    pin=next(e['patched_sha256'] for e in manifest['files'] if e['path']==RELATIVE)
    original=target.read_bytes();digest=hashlib.sha256(original).hexdigest()
    if digest==pin:return 'source Focus ready'
    if digest!=BASE:raise ValueError('Unknown source Focus code; preserve it')
    updated=patch_scorer(original.decode('utf-8')).encode('utf-8')
    if hashlib.sha256(updated).hexdigest()!=pin:raise ValueError('Source Focus patch differs from pin')
    target.write_bytes(updated)
    return 'source Focus patched'
