"""Remove the obsolete second-pipe stop from the actual source text stream."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = 'main_logic/omni_offline_client/_streaming.py'
BASE = '4b86ac819a00dd7c3a7881e8da369f3fa9f653f33e17e6d08736e0aec856c659'
MARKER = '# daily-pipe-output-v1'
EDITS = [
    ('        for variant in (f"{name} | ", f"{name} |", f"{name}| ", f"{name}|"):',
     '        leading = len(text) - len(text.lstrip())\n        text = text.lstrip()\n        for variant in (f"{name} | ", f"{name} |", f"{name}| ", f"{name}|"):'),
    ('                return len(variant)\n', '                return leading + len(variant)\n'),
    ('                        pipe_count = 0  # 围栏：追踪 | 字符的出现次数\n',
     '                        # daily-pipe-output-v1: math/code pipes are content, not speaker boundaries.\n'),
    ('                        fence_triggered = False  # 围栏是否已触发\n', ''),
    ('                                pipe_count = 0\n', ''),
    ('                            if fence_triggered:\n                                break\n\n', ''),
    ('''                                for idx, char in enumerate(truncated_content):
                                    if char == '|':
                                        pipe_count += 1
                                        if pipe_count >= 2:
                                            truncated_content = truncated_content[:idx]
                                            fence_triggered = True
                                            logger.info("OmniOfflineClient: 围栏触发 - 检测到第二个 | 字符，截断输出")
                                            break

''', ''),
    ('''                                for idx, char in enumerate(flush_text):
                                    if char == '|':
                                        pipe_count += 1
                                        if pipe_count >= 2:
                                            flush_text = flush_text[:idx]
                                            fence_triggered = True
                                            break
''', ''),
    ('# 重置围栏 / prefix buffer：下一段是新的语义', '# 重置 prefix buffer：下一段是新的语义'),
    ('# fence + length guard', '# length guard'),
    ('                            if content and content.strip():', '                            if content:'),
    ('                                    if len(prefix_buffer) >= self._prefix_buffer_size:',
     '                                    if not prefix_buffer.strip():\n                                        continue\n                                    if len(prefix_buffer.lstrip()) >= self._prefix_buffer_size:'),
    ('                                        if not (truncated_content and truncated_content.strip()):', '                                        if not truncated_content:'),
    ('                                if truncated_content and truncated_content.strip():', '                                if truncated_content:'),
    ('                                if flush_text and flush_text.strip():', '                                if flush_text and (assistant_message or flush_text.strip()):'),
    ('                                    if emit_content and emit_content.strip():', '                                    if emit_content:'),
    ('                                    if emit_flush_text and emit_flush_text.strip():', '                                    if emit_flush_text:'),
    ('                            elif content and not content.strip():\n                                logger.debug(f"OmniOfflineClient: 过滤空白内容 - content_repr: {repr(content)[:100]}")\n', ''),
    ('# 复用之前的 fence / prefix 状态。', '# 复用之前的 prefix 状态。'),
    ('\n                        prefix_checked = not bool(self._prefix_buffer_size)', '\n                        prefix_checked = False'),
    ('\n                                prefix_checked = not bool(self._prefix_buffer_size)', '\n                                prefix_checked = False'),
]


def patch_streaming(source):
    if MARKER in source:
        ast.parse(source)
        return source
    for old, new in EDITS:
        if source.count(old) != 1:
            raise ValueError('Pipe output anchor changed; preserve source')
        source = source.replace(old, new, 1)
    ast.parse(source)
    return source


def apply_to(host_root):
    expected = ROOT/'benchmarks/raw/neko-product-host'
    if host_root.is_symlink() or host_root.resolve() != expected.resolve():
        raise ValueError('Pipe output patch is for the actual source host only')
    target = host_root/RELATIVE
    if target.is_symlink() or not target.resolve().is_relative_to(host_root.resolve()):
        raise ValueError('Pipe output target escapes host; preserve source')
    manifest = json.loads((ROOT/'patches/neko-study-2026-10-10-host/manifest.json').read_text(encoding='utf-8'))
    pin = next(item['patched_sha256'] for item in manifest['files'] if item['path']==RELATIVE)
    original = target.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if digest == pin:
        return 'pipe output ready'
    if digest != BASE:
        raise ValueError('Unknown pipe output source; preserve it')
    updated = patch_streaming(original.decode('utf-8')).encode('utf-8')
    if hashlib.sha256(updated).hexdigest() != pin:
        raise ValueError('Pipe output result differs from pinned source')
    target.write_bytes(updated)
    return 'pipe output patched'
