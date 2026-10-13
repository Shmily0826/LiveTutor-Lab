"""Offline analysis of recorded turn events and a fixed WAV; never plays audio.

The intended input kind must be declared from the source stimulus. Early provider
transcription alone does not prove a single long sentence was cut short.
"""
from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave


def _timestamp(value):
    return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def analyze_scene(scene, *, input_kind="unknown"):
    if input_kind not in {"unknown", "command_sequence", "single_sentence"}:
        raise ValueError("input_kind must come from the known source stimulus")
    end = _timestamp(scene.get("fixed_speech_end_wall"))
    start = _timestamp(scene.get("input_audio_start_wall"))
    if end is None or start is None or end < start:
        raise ValueError("absolute input speech clocks are missing or invalid; do not mix relative origins")
    wire = [event for event in scene.get("wire_trace", []) if isinstance(event, dict)]
    completed = [event for event in wire if event.get("dir") == "recv"
                 and event.get("type") == "conversation.item.input_audio_transcription.completed"
                 and _timestamp(event.get("t")) is not None and event["t"] >= start]
    updates = [event for event in wire if event.get("dir") == "send" and event.get("type") == "session.update"]
    nulls = [event for event in updates if event.get("turn_detection_present") is True
             and event.get("turn_detection") is None and _timestamp(event.get("t")) is not None]
    later_partial_updates = [event for event in updates if nulls and _timestamp(event.get("t")) is not None
                             and event["t"] > nulls[-1]["t"] and event["t"] < start
                             and event.get("turn_detection_present") is False]
    transcripts = [str(event.get("text") or "")[:240]
                  for event in (scene.get("native_final", {}).get("trace") or {}).get("events", [])
                  if isinstance(event, dict) and event.get("type") == "user_transcript"
                  and _timestamp(event.get("wall")) is not None and event["wall"] >= start]
    tools = [event for event in wire if event.get("dir") == "recv"
             and event.get("type") == "response.function_call_arguments.done"
             and _timestamp(event.get("t")) is not None and event["t"] >= start]
    manual_end = _timestamp(scene.get("manual_end_sent_wall"))
    local_boundaries = [event["type"] for event in wire if event.get("dir") == "send"
                        and event.get("type") in {"input_audio_buffer.commit", "input_audio_buffer.clear"}
                        and _timestamp(event.get("t")) is not None and start <= event["t"] <= end]
    early = sum(event["t"] < end for event in completed)
    return {
        "declared_input_kind": input_kind,
        "provider_completed": [{"chars": event.get("transcript_chars"),
                                "seconds_from_speech_end": round(event["t"] - end, 3)} for event in completed],
        "provider_completions_before_speech_end": early,
        "recorded_native_transcripts": transcripts,
        "provider_requested_tools": [event.get("name") for event in tools],
        "local_commit_or_clear_before_speech_end": local_boundaries,
        "explicit_null_request_seen": bool(nulls),
        "provider_vad_echo_seen": any(event.get("type") == "session.updated"
                                      and event.get("turn_detection_present") is True for event in wire),
        "later_session_updates_omitting_vad_before_input": len(later_partial_updates),
        "provider_completed_before_manual_end": sum(event["t"] < manual_end for event in completed) if manual_end is not None else None,
        "single_sentence_status": ("not_tested_by_this_material" if input_kind != "single_sentence"
                                   else "early_provider_completion_observed" if early else "no_early_completion_observed"),
        "support_limit": "configuration sequence did not suppress observed completions; no protocol-wide support verdict",
    }


def analyze_wave(path, *, threshold=100, frame_ms=10, minimum_gap_ms=150):
    path = Path(path)
    if not math.isfinite(threshold) or threshold <= 0 or not 1 <= frame_ms <= 100 or minimum_gap_ms < frame_ms:
        raise ValueError("invalid amplitude analysis settings")
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2 or source.getnchannels() != 1:
            raise ValueError("this amplitude analysis supports only mono PCM16 WAV")
        rate, count = source.getframerate(), source.getnframes()
        pcm = array.array("h", source.readframes(count))
    if sys.byteorder != "little":
        pcm.byteswap()
    step = max(1, round(rate * frame_ms / 1000))
    active = []
    for offset in range(0, len(pcm), step):
        block = pcm[offset:offset + step]
        if math.sqrt(sum(value * value for value in block) / len(block)) > threshold:
            active.append((offset, min(offset + step, len(pcm))))
    gaps = [{"from": round(left[1] / rate, 3), "to": round(right[0] / rate, 3),
             "seconds": round((right[0] - left[1]) / rate, 3)} for left, right in zip(active, active[1:])
            if (right[0] - left[1]) / rate >= minimum_gap_ms / 1000]
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "seconds": count / rate,
            "sample_rate": rate, "threshold": threshold, "amplitude_gaps": gaps,
            "first_active": active[0][0] / rate if active else None,
            "last_active_end": active[-1][1] / rate if active else None,
            "proof": "raw amplitude only, not RNNoise verdict or semantic sentence boundaries"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, action="append", required=True)
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--input-kind", choices=("unknown", "command_sequence", "single_sentence"), default="unknown")
    args = parser.parse_args()
    amplitude = analyze_wave(args.wav)
    scenes = []
    for path in args.scene:
        scene = json.loads(path.read_text(encoding="utf-8"))
        scenes.append({"path": str(path), "wav_hash_matches": scene.get("input_wav_sha256") == amplitude["sha256"],
                       **analyze_scene(scene, input_kind=args.input_kind)})
    print(json.dumps({"wave": amplitude, "scenes": scenes, "external_calls": 0}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
