"""Opt-in pause hold for the free Realtime uplink (NEKO_PAUSE_HOLD=1).

The free proxy ends a user turn at a mid-sentence pause of roughly 0.5-0.9 s and ignores
client turn_detection settings (docs/evidence/claude-m3-split-asr-analysis-2026-10-15.md).
So the uplink keeps the first KEEP seconds of a pause, holds the next HOLD seconds locally,
and then either drops the held silence (speech resumed: one turn, shorter pause) or sends
it all at once (the learner really stopped: the provider ends the turn as before).

Speech frames are never delayed, so local barge-in and onset handling are unchanged; the
hold only ever touches frames the existing speech verdict calls quiet. Replays, activation
receipts, phrase mode and every other provider keep the original path.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from neko_voice_host_patch import HOSTS

ROOT = Path(__file__).resolve().parents[1]
TARGET = "main_logic/omni_realtime_client/_transport.py"
HUNKS = (
    ('''            if self._is_gemini:
                await self._stream_audio_gemini(
''', '''            if (not _native_barge_in_replay and not require_output_commit
                    and getattr(self, "_is_free_proxy", False) and not self._is_gemini
                    and __import__("os").environ.get("NEKO_PAUSE_HOLD") == "1"):
                audio_chunk = self._livetutor_pause_hold(audio_chunk, bool(
                    speech_active if speech_active is not None else (
                        audio_processor.speech_probability > 0.4 if _rnnoise_vad_live else raw_loud)))
                if not audio_chunk:
                    return None  # Held locally; nothing reaches the provider yet.
            if self._is_gemini:
                await self._stream_audio_gemini(
'''),
    ('''    async def _analyze_image_with_vision_model(
''', '''    def _livetutor_pause_hold(self, chunk: bytes, voiced: bool) -> bytes:
        """What to send now for one 16 kHz PCM16 frame: b"" while a pause is held."""
        os_env = __import__("os").environ
        # Counted in 16 kHz samples, so pacing and float drift cannot move the limits.
        keep = int(os_env.get("NEKO_PAUSE_HOLD_KEEP_MS", "300")) * 16
        hold = int(os_env.get("NEKO_PAUSE_HOLD_MS", "1000")) * 16
        state = getattr(self, "_livetutor_hold", None)
        if state is None or state["generation"] != self._connection_generation:
            state = self._livetutor_hold = {"generation": self._connection_generation,
                                            "quiet": 0, "speech": False, "held": []}
        if voiced:
            if state["held"]:
                dropped = sum(len(part) for part in state["held"]) // 2
                state["held"].clear()
                logger.info("[pause-hold] speech resumed; dropped %.2fs of a %.2fs pause",
                            dropped / 16000, state["quiet"] / 16000)
            state["quiet"] = 0
            state["speech"] = True
            return chunk
        state["quiet"] += len(chunk) // 2
        if not state["speech"] or state["quiet"] <= keep:
            return chunk
        if state["quiet"] <= keep + hold:
            state["held"].append(chunk)
            return b""
        released = b"".join(state["held"]) + chunk
        state["held"].clear()
        state["speech"] = False
        return released

    async def _analyze_image_with_vision_model(
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
