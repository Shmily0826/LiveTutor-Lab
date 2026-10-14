"""Replay the bounded DSML display guard; never interpret text as executable tools."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = '# daily-dsml-output-v1'
FALLBACK = '这次没有生成有效回答，暂时无法确认结论。'

FILTER_EDITS = [
    ('_DEFAULT_TOOL_NAMES =', '''# daily-dsml-output-v1
_DSML_START_RE = re.compile(r"</?[｜]{1,2}DSML[｜]{1,2}", re.IGNORECASE)
_DSML_CLOSE_RE = re.compile(r"</[｜]{1,2}DSML[｜]{1,2}\\s*(?:function_calls|calls)\\s*>", re.IGNORECASE)
_DSML_PREFIXES = tuple("<" + slash + "｜" * left + "DSML" + "｜" * right
                       for slash in ("", "/") for left in (1, 2) for right in (1, 2))


_DEFAULT_TOOL_NAMES ='''),
    ('r"<\\s*parameter\\b[^>]*\\bname\\s*=[^>]*>|<\\s*/\\s*parameter\\s*>",',
     'r"<\\s*(?:[｜]{1,2}DSML[｜]{1,2}\\s*)?parameter\\b[^>]*\\bname\\s*=[^>]*>|<\\s*/\\s*(?:[｜]{1,2}DSML[｜]{1,2}\\s*)?parameter\\s*>",'),
    ('        self._pending = ""\n        self._suppressing = False',
     '        self._pending = ""\n        self.dsml_filtered = False\n        self._suppressing = False'),
    ('            self._suppression_pattern = pattern\n',
     '            self._suppression_pattern = pattern\n            self.dsml_filtered = self.dsml_filtered or pattern == "dsml_tool_call"\n'),
    ('        visible = self._pending\n        self._pending = ""\n        return visible, None', '''        if self._pending.startswith(("<｜", "</｜")) and any(
            prefix.lower().startswith(self._pending.lower()) for prefix in _DSML_PREFIXES
        ):
            self.dsml_filtered = True
            self._suppression_pattern = "dsml_tool_call"
            self._suppressed_chars = len(self._pending)
            self._pending = ""
            return "", self._finish_event(finalized=True)
        visible = self._pending
        self._pending = ""
        return visible, None'''),
    ('        if self._suppression_pattern != "structured_tool_call":', '''        if self._suppression_pattern == "dsml_tool_call":
            for match in _DSML_CLOSE_RE.finditer(text):
                if self._suppressed_parameter_depth_after(text[:match.start()]) == 0:
                    return match
            return None
        if self._suppression_pattern != "structured_tool_call":'''),
    ('    def _suppression_close_tail_len(self, text: str) -> int:\n', '''    def _suppression_close_tail_len(self, text: str) -> int:
        if self._suppression_pattern == "dsml_tool_call":
            start = text.rfind("<", max(0, len(text) - self._max_tail))
            return len(text) - start if start >= 0 and ">" not in text[start:] else 0
'''),
    ('        if self._tool_names:\n            lower_text = text.lower()', '''        dsml = _DSML_START_RE.search(text)
        if dsml and (best is None or dsml.start() < best[0]):
            best = (dsml.start(), dsml.end(), "dsml_tool_call")

        if self._tool_names:
            lower_text = text.lower()'''),
    ('        return max(best, self._structured_marker_tail_len(text))', '''        for start in range(max(0, len(text) - self._max_tail), len(text)):
            tail = text[start:].lower()
            if any(prefix.lower().startswith(tail) for prefix in _DSML_PREFIXES):
                best = max(best, len(tail))
                break
        return max(best, self._structured_marker_tail_len(text))'''),
]

TOOLS_EDITS = [
    ('        leak_filter = ToolLeakFilter(tool_names=tool_names)\n', '''        # daily-dsml-output-v1
        leak_filter = ToolLeakFilter(tool_names=tool_names)
        final_visible = False
        generation_is_active = _generation_check(self, overrides.get("_response_generation"))
'''),
    ('                if getattr(chunk, "_tool_leak_filtered", False):\n                    yield chunk', '''                if getattr(chunk, "tool_round_persisted", False):
                    final_visible = False
                if getattr(chunk, "_tool_leak_filtered", False):
                    final_visible = final_visible or bool(str(getattr(chunk, "content", "") or "").strip())
                    yield chunk'''),
    ('                    setattr(chunk, "_tool_leak_filtered", True)\n                yield chunk',
     '                    setattr(chunk, "_tool_leak_filtered", True)\n                    final_visible = final_visible or bool(chunk.content.strip())\n                yield chunk'),
    ('        chunk = _finalize_filter_chunk()\n        if chunk is not None:\n            yield chunk\n\n    def _filter_tool_leak_content(', '''        chunk = _finalize_filter_chunk()
        if chunk is not None:
            final_visible = final_visible or bool(chunk.content.strip())
            yield chunk
        if leak_filter.dsml_filtered and not final_visible and generation_is_active():
            yield LLMStreamChunk(content="这次没有生成有效回答，暂时无法确认结论。")

    def _filter_tool_leak_content('''),
]


def _patch(source, edits):
    if MARKER in source:
        ast.parse(source)
        return source
    for old, new in edits:
        # The state initializer is intentionally shared by __init__ and reset.
        expected = 2 if '        self._pending = ""\n        self._suppressing = False' == old else 1
        if source.count(old) != expected:
            raise ValueError('DSML patch anchor changed; preserve source')
        source = source.replace(old, new)
    ast.parse(source)
    return source


def patch_filter(source):
    return _patch(source, FILTER_EDITS)


def patch_tools(source):
    return _patch(source, TOOLS_EDITS)


TARGETS = {
    'utils/llm_tool_leak_filter.py': ('1acba9dc630dee64d5f1b005bc007054d8eef72af5442464a288d2f84a24ac4a', patch_filter),
    'main_logic/omni_offline_client/_tools.py': ('44d93874b56d175a53bc1c3fbaf583b126e3dd0c63f62519b5e157a5c6724c01', patch_tools),
}


def apply_to(host_root):
    if host_root.is_symlink() or not host_root.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('DSML host escapes project; preserve source')
    manifest = json.loads((ROOT/'patches/neko-study-2026-10-10-host/manifest.json').read_text(encoding='utf-8'))
    pins = {item['path']: item['patched_sha256'] for item in manifest['files']}
    plan = []
    for relative, (base, patch) in TARGETS.items():
        target = host_root/relative
        if target.is_symlink() or not target.resolve().is_relative_to(host_root.resolve()):
            raise ValueError('DSML target escapes host; preserve source')
        original = target.read_bytes()
        digest = hashlib.sha256(original).hexdigest()
        if relative not in pins:
            raise ValueError('DSML target is not pinned in the host manifest')
        if digest == pins[relative]:
            continue
        if digest != base:
            raise ValueError('Unknown DSML host source; preserve it: '+relative)
        updated = patch(original.decode('utf-8')).encode('utf-8')
        if hashlib.sha256(updated).hexdigest() != pins[relative]:
            raise ValueError('DSML patch result differs from pinned source')
        plan.append((target, updated))
    for target, updated in plan:
        target.write_bytes(updated)
    return 'DSML display guard ready'
