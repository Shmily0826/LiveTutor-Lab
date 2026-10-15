"""A visible retry hint when a complete spoken question gets an empty answer.

The free provider sometimes ends the response to a complete user transcript with no audio,
no text and no tool call, and never answers afterwards (2 of 11 single-transcript runs,
docs/evidence/claude-m2-voice-entry-2026-10-15.md). Without a cue the learner just waits.
Three seconds after such an empty answer, if nothing else happened (no new response, no new
transcript, no tool call, the learner not speaking, same connection), the existing status
toast says so. No request is re-sent and the response arbiter is untouched.
NEKO_EMPTY_TURN_NOTICE=0 turns it off.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from neko_voice_host_patch import HOSTS

ROOT = Path(__file__).resolve().parents[1]
TARGET = "main_logic/omni_realtime_client/_transport.py"
HUNKS = (
    ('''                    name = event.get("name") or ""
                    raw_args = event.get("arguments") or ""
''', '''                    self._livetutor_call_seen_at = time.time()
                    name = event.get("name") or ""
                    raw_args = event.get("arguments") or ""
'''),
    ('''                    if finalize_response is False:
                        continue
                    self._clear_turn_response_state()
''', '''                    if finalize_response is False:
                        continue
                    self._livetutor_note_empty_answer()
                    self._clear_turn_response_state()
'''),
    ('''    def _take_response_transcript(self) -> str:
''', '''    def _livetutor_note_empty_answer(self) -> None:
        """LiveTutor: a complete question answered with nothing gets a visible retry hint."""
        if __import__("os").environ.get("NEKO_EMPTY_TURN_NOTICE", "1") != "1":
            return
        asked = getattr(self, "_late_raw_transcript_at", 0.0) or 0.0
        if (self._audio_delta_count or self._current_response_transcript
                or getattr(self, "_livetutor_call_seen_at", 0.0) >= asked
                or not 0 < time.time() - asked < 8.0
                or getattr(self, "_livetutor_empty_notice_for", None) == asked
                or self.on_status_message is None):
            return
        self._livetutor_empty_notice_for = asked
        done_before = self._response_done_total
        generation = self._connection_generation

        async def notice():
            await asyncio.sleep(3.0)
            if (self._connection_generation != generation
                    or self._response_done_total != done_before
                    or self._is_responding or self._audio_delta_count
                    or getattr(self, "_late_raw_transcript_at", 0.0) != asked
                    or getattr(self, "_livetutor_call_seen_at", 0.0) >= asked
                    or time.time() - getattr(self, "_user_recent_activity_time", 0.0) < 2.0):
                return
            logger.info("[empty-turn] question at %.3f got an empty answer; showing retry hint", asked)
            await self.on_status_message("角色这次没有回应，请再说一遍。")

        task = asyncio.get_running_loop().create_task(notice())
        task.add_done_callback(lambda done: done.cancelled() or done.exception())

    def _take_response_transcript(self) -> str:
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
