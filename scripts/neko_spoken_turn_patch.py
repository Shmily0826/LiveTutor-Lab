"""Candidate: replay safe turn-boundary diagnostics, without changing voice policy.

Default is inspection only. Integration/online sessions belong to the main agent.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

MARKER = "# daily-spoken-turn-diagnostics-v1"
HELPER = '''# daily-spoken-turn-diagnostics-v1
def _spoken_turn_config_fields(record, session):
    record["turn_config_source"] = (
        "client_requested" if record.get("type") == "session.update"
        else "provider_reported"
    )
    record["turn_detection_present"] = "turn_detection" in session
    configs = []
    if isinstance(session.get("turn_detection"), dict):
        configs.append(("turn_detection", session["turn_detection"]))
    audio = session.get("audio")
    audio_input = audio.get("input") if isinstance(audio, dict) else None
    if isinstance(audio_input, dict) and isinstance(audio_input.get("turn_detection"), dict):
        configs.append(("audio.input.turn_detection", audio_input["turn_detection"]))
    for name in ("realtime_input_config", "realtimeInputConfig"):
        realtime = session.get(name)
        if not isinstance(realtime, dict):
            continue
        for vad_name in ("automatic_activity_detection", "automaticActivityDetection"):
            if isinstance(realtime.get(vad_name), dict):
                configs.append((name + "." + vad_name, realtime[vad_name]))
    for prefix, values in configs:
        for key in ("silence_duration_ms", "prefix_padding_ms", "threshold",
                    "silenceDurationMs", "prefixPaddingMs"):
            value = values.get(key)
            if type(value) in (int, float) and abs(value) < 1_000_000_000:
                record[prefix + "." + key] = value
        for key in ("disabled", "create_response", "interrupt_response"):
            if type(values.get(key)) is bool:
                record[prefix + "." + key] = values[key]
        for key in ("end_of_speech_sensitivity", "endOfSpeechSensitivity",
                    "start_of_speech_sensitivity", "startOfSpeechSensitivity", "eagerness"):
            value = values.get(key)
            if value in ("END_SENSITIVITY_LOW", "END_SENSITIVITY_HIGH", "END_SENSITIVITY_UNSPECIFIED",
                         "START_SENSITIVITY_LOW", "START_SENSITIVITY_HIGH", "START_SENSITIVITY_UNSPECIFIED",
                         "low", "medium", "high", "auto"):
                record[prefix + "." + key] = value


'''


def patch_wire_trace(source: str) -> str:
    if MARKER in source:
        ast.parse(source)
        return source
    anchor = "def _session_fields(record: dict[str, Any], session: Any) -> None:\n"
    guarded = "    tools = session.get(\"tools\")\n"
    receive_anchor = '    _item_fields(record, event.get("item"))\n'
    for needle in (anchor, guarded, receive_anchor):
        if source.count(needle) != 1:
            raise ValueError("wire trace source changed; inspect before applying diagnostics")
    if source.count('                "t": trace_now(),\n') != 2:
        raise ValueError("wire trace clock anchors changed")
    result = source.replace(anchor, HELPER + anchor, 1)
    result = result.replace(guarded, '    _spoken_turn_config_fields(record, session)\n' + guarded, 1)
    result = result.replace(receive_anchor, '''    if type_text in ("input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"):
        for key in ("audio_start_ms", "audio_end_ms"):
            value = event.get(key)
            if type(value) in (int, float) and abs(value) < 1_000_000_000:
                record[key] = value
    if type_text == "conversation.item.input_audio_transcription.completed":
        transcript = event.get("transcript")
        if isinstance(transcript, str):
            record["transcript_chars"] = len(transcript)
''' + receive_anchor, 1)
    result = result.replace('                "t": trace_now(),\n',
                            '                "t": trace_now(),\n                "mono": round(time.monotonic(), 6),\n')
    ast.parse(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="explicit N.E.K.O source/deployment root")
    parser.add_argument("--apply", action="store_true", help="write the reviewed diagnostic candidate")
    args = parser.parse_args()
    target = args.root.resolve() / "main_logic/omni_realtime_client/_wire_trace.py"
    original = target.read_text(encoding="utf-8")
    patched = patch_wire_trace(original)
    state = "already_patched" if patched == original else "patch_available"
    if args.apply and patched != original:
        pending = target.with_suffix(".daily-turn.tmp")
        if pending.exists():
            raise RuntimeError("previous diagnostic temporary file exists; inspect it first")
        try:
            pending.write_text(patched, encoding="utf-8")
            pending.replace(target)
        finally:
            if pending.exists():
                pending.unlink()
        state = "patched"
    print(json.dumps({"path": str(target), "status": state, "policy_changed": False}))


if __name__ == "__main__":
    main()
