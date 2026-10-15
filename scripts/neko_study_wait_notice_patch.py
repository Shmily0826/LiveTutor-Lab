"""A visible 'still working' toast while a slow Study tool runs (avatar status channel).

A source explanation keeps the learner in 7-10 s of silence between their question and the
first audio. Asking the realtime model to say a short acknowledgement first was not followed
(docs/evidence/claude-m2-voice-entry-2026-10-15.md), so the cue comes from the host instead:
the existing status toast, repeated while the tool is still running, cancelled when it returns.
NEKO_STUDY_WAIT_NOTICE=0 turns it off.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from neko_voice_host_patch import HOSTS

ROOT = Path(__file__).resolve().parents[1]
TARGET = "main_logic/core/tool_calling.py"
HUNKS = (
    ('''        async def _handle(call: ToolCall) -> ToolResult:
            return await self._on_tool_call(call, invoking_session=session)
''', '''        async def _handle(call: ToolCall) -> ToolResult:
            wait_notice = self._start_study_wait_notice(call, session)
            try:
                return await self._on_tool_call(call, invoking_session=session)
            finally:
                if wait_notice is not None:
                    wait_notice.cancel()
'''),
    ('''    async def _route_tool_images(
''', '''    def _start_study_wait_notice(self, call, invoking_session):
        """LiveTutor: keep a short status toast up while a slow Study tool works."""
        definition = self.tool_registry.get(call.name)
        if (os.environ.get("NEKO_STUDY_WAIT_NOTICE", "1") != "1"
                or call.name not in ("study_explain", "study_quiz", "study_summary")
                or definition is None or definition.metadata.get("source") != "plugin:study_companion"
                or invoking_session is None or invoking_session is not self.session):
            return None
        arguments = getattr(call, "arguments", None) or {}
        english = str(arguments.get("language") or "").lower().startswith("en")
        if call.name == "study_quiz":
            text = "Preparing a question..." if english else "正在出题……"
        elif call.name == "study_summary":
            text = "Reading your study record..." if english else "正在查看学习记录……"
        elif arguments.get("material_source") == "project_code":
            text = "Reading the source code..." if english else "正在查看源码……"
        else:
            text = "Looking at the material..." if english else "正在查看学习材料……"

        async def notice():
            await asyncio.sleep(1.5)  # Fast answers need no toast.
            for _ in range(8):
                await self.send_status(text)
                await asyncio.sleep(4.0)

        task = asyncio.create_task(notice())
        task.add_done_callback(lambda done: done.cancelled() or done.exception())
        return task

    async def _route_tool_images(
'''),
)


def apply_to(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if all(new in text for _, new in HUNKS):
        return "already patched"
    for old, new in HUNKS:
        if new in text:
            continue
        if text.count(old) != 1:
            raise RuntimeError(f"{path}: anchor moved for {old[:40]!r}; not patching")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")
    return "patched"


def main() -> int:
    report = {str((host / TARGET).relative_to(ROOT)): apply_to(host / TARGET) for host in HOSTS}
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
