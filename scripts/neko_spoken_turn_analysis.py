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
import re
from pathlib import Path
import sys
import wave


def _timestamp(value):
    try:
        return float(value) if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def parse_study_text_records(log_text):
    """Keep opt-in digest evidence in order, refusing content-bearing records."""
    fields={'stage','t','mono','cid','chars','utf8_bytes','sha256','gen','response_id','scope','token',
            'stream_chars','stream_chunks','stream_sha256','cumulative_available','bytes','delivery'}
    stages={'grade_reply','relay_write','relay_envelope_write','provider_delta','provider_done',
            'omni_callback','core_entry','core_queue','core_ws'}
    records=[]
    for line in log_text.splitlines():
        if '[study-text] ' not in line:continue
        try:value=json.loads(line.split('[study-text] ',1)[1])
        except (ValueError,RecursionError):continue
        if (not isinstance(value,dict) or not set(value)<=fields
                or not isinstance(value.get('stage'),str) or value['stage'] not in stages
                or _timestamp(value.get('t')) is None
                or not isinstance(value.get('cid'),str) or not re.fullmatch('[0-9a-f]{8}',value['cid'])
                or not isinstance(value.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',value['sha256'])):
            continue
        if any(key in value and (type(value[key]) is not int or value[key]<0)
               for key in ('chars','utf8_bytes','stream_chars','stream_chunks','bytes')):
            continue
        if (any(value.get(key) is not None and (type(value[key]) is not int or value[key]<0)
                for key in ('gen','scope'))
                or 'mono' in value and _timestamp(value['mono']) is None
                or 'cumulative_available' in value and type(value['cumulative_available']) is not bool
                or 'delivery' in value and value['delivery']!='local_socket_write_only'):
            continue
        if any(value.get(key) is not None and (not isinstance(value[key],str) or len(value[key])>160)
               for key in ('response_id','token')):
            continue
        if 'stream_sha256' in value and (not isinstance(value['stream_sha256'],str)
                or not re.fullmatch('[0-9a-f]{64}',value['stream_sha256'])):
            continue
        records.append(value)
    return records


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


def parse_phrase_deliveries(log_text):
    """Keep only the existing count/clock diagnostic, never arbitrary log content."""
    fields = ("connection_generation", "source_samples", "output_samples", "compressed_zero_samples",
              "written_samples", "speech_end_estimated_wall", "sealed_estimated_wall", "sealed_wall",
              "queue_wait_ms", "started_wall", "first_write_wall", "first_write_completed_ms",
              "completed_wall", "write_elapsed_ms")
    records = []
    for line in log_text.splitlines():
        if "native phrase delivery " not in line:
            continue
        try:
            raw = json.loads(line.split("native phrase delivery ", 1)[1])
            if (not isinstance(raw, dict) or raw.get("result") != "written_waiting_provider_boundary"
                    or raw.get("input_timebase") != "arrival_derived_sample_estimate"):
                continue
            public = {key: raw[key] for key in fields}
            if not all(_timestamp(v) is not None and v >= 0 for v in public.values()):
                continue
            public.update(result="written_waiting_provider_boundary", input_timebase=raw["input_timebase"])
            if 'output_pcm_sha256' in raw:
                extra = {key: raw[key] for key in ('input_sequence', 'output_pcm_sha256', 'captured_start_estimated_wall',
                    'compressed_zero_intervals', 'compressed_intervals_truncated', 'local_append_count',
                    'local_append_writes', 'local_append_writes_truncated')}
                if (not isinstance(extra['output_pcm_sha256'], str)
                        or not re.fullmatch('[0-9a-f]{64}', extra['output_pcm_sha256'])
                        or _timestamp(extra['captured_start_estimated_wall']) is None
                        or extra['captured_start_estimated_wall'] < 0
                        or type(extra['input_sequence']) is not int or extra['input_sequence'] < 0
                        or any(type(extra[k]) is not bool for k in
                               ('compressed_intervals_truncated', 'local_append_writes_truncated'))):
                    continue
                intervals, writes = extra['compressed_zero_intervals'], extra['local_append_writes']
                if (not isinstance(intervals, list) or len(intervals) > 32
                        or any(not isinstance(pair, list) or len(pair) != 2
                               or any(type(n) is not int for n in pair)
                               or not 0 <= pair[0] < pair[1] <= public['source_samples'] for pair in intervals)
                        or any(a[1] > b[0] for a, b in zip(intervals, intervals[1:]))
                        or not isinstance(writes, list) or len(writes) > 32
                        or type(extra['local_append_count']) is not int or extra['local_append_count'] < len(writes)):
                    continue
                if any(not isinstance(w, dict) or set(w) != {'samples', 'written_wall', 'elapsed_ms'}
                       or type(w['samples']) is not int or w['samples'] <= 0
                       or any(_timestamp(w[k]) is None or w[k] < 0 for k in ('written_wall', 'elapsed_ms'))
                       for w in writes):
                    continue
                removed = sum(end - start for start, end in intervals)
                written = sum(w['samples'] for w in writes)
                if (public['source_samples'] - public['output_samples'] != public['compressed_zero_samples']
                        or public['written_samples'] != public['output_samples']
                        or removed > public['compressed_zero_samples'] or written > public['written_samples']
                        or not extra['compressed_intervals_truncated'] and removed != public['compressed_zero_samples']
                        or not extra['local_append_writes_truncated'] and
                           (written != public['written_samples'] or extra['local_append_count'] != len(writes))):
                    continue
                public.update(extra)
            if public not in records:  # The host has two logging handlers for the same record.
                records.append(public)
        except (KeyError, ValueError, TypeError):
            continue
    return records


def analyze_grade_latency(scene):
    """Observed single-turn clocks, not service-only latency or an acceptance gate."""
    result = {"status": "unavailable", "seconds": {}, "phrase_status": "unavailable",
              "physical_playback_start": "unverified", "external_calls": 0,
              "scope": "fixed input / local writes / provider receive / Native schedule; no provider ACK or physical clock"}
    try:
        turn, = scene["turns"]
        start, end, stop = (turn[k] for k in ("input_wall", "fixed_speech_end_wall", "observation_end_wall"))
        if not all(_timestamp(v) is not None and v > 0 for v in (start, end, stop)) or not start <= end < stop:
            return result
        markers = scene["grade_markers"]
        if len(markers) != 3 or {m["stage"] for m in markers} != {"accepted", "grade_complete", "relay_written"}:
            return result
        accepted, graded, relay = (next(m for m in markers if m["stage"] == stage)
                                   for stage in ("accepted", "grade_complete", "relay_written"))
        if (not all(_timestamp(m.get("wall")) is not None for m in markers)
                or not end <= accepted["wall"] <= graded["wall"] <= relay["wall"] <= stop
                or not all(isinstance(accepted.get(k), str) and accepted[k]
                           and all(m.get(k) == accepted[k] for m in markers)
                           for k in ("course_id", "session_id", "question_id", "attempt_id"))
                or not all(type(m.get(k)) is int and m[k] >= 0 for m in markers for k in ("connection", "scope"))
                or accepted["connection"] < 1
                or graded["connection"] != accepted["connection"] or graded["scope"] != accepted["scope"]
                or relay["connection"] != accepted["connection"] + 1 or relay["scope"] <= accepted["scope"]
                or not isinstance(accepted.get("token"), str) or not accepted["token"]
                or graded.get("token") != accepted["token"]
                or not isinstance(relay.get("token"), str) or not relay["token"]
                or relay["token"] == accepted.get("token")):
            return result
        events = [e for e in scene["native_final"]["trace"]["events"] if isinstance(e, dict)
                  and _timestamp(e.get("wall")) is not None and start <= e["wall"] <= stop]
        pcm = [e["wall"] for e in events if e.get("type") == "audio_frame"
               and e.get("correlation_id") == relay["token"] and type(e.get("bytes")) is int and e["bytes"] > 0
               and e["wall"] >= graded["wall"]]
        schedule = [e["wall"] for e in events if e.get("type") == "speech_playback_state"
                    and e.get("reason") == "chunk_scheduled" and e.get("active") is True
                    and e.get("correlationId") == relay["token"] and pcm and e["wall"] >= min(pcm)]
        seconds = result["seconds"]
        seconds.update(input_end_to_accepted_asr=accepted["wall"] - end,
                       accepted_asr_to_grade=graded["wall"] - accepted["wall"],
                       grade_to_relay_write=relay["wall"] - graded["wall"])
        if pcm:
            seconds.update(input_end_to_native_pcm=min(pcm) - end,
                           relay_write_to_native_pcm=min(pcm) - relay["wall"])
        if schedule:
            seconds.update(pcm_to_native_schedule=min(schedule) - min(pcm),
                           input_end_to_native_schedule=min(schedule) - end)
        for name, candidates in (
            ("native_asr", [e["wall"] for e in events if e.get("type") == "user_transcript"]),
            ("provider_asr", [e["t"] for e in scene.get("wire_trace", []) if isinstance(e, dict)
                and e.get("dir") == "recv" and e.get("type") == "conversation.item.input_audio_transcription.completed"
                and _timestamp(e.get("t")) is not None and end <= e["t"] <= stop]),
        ):
            if len(candidates) == 1 and candidates[0] >= end:
                seconds["input_end_to_" + name] = candidates[0] - end
        deliveries = []
        for item in scene.get("phrase_deliveries", []):
            if not isinstance(item, dict):
                continue
            clocks = [item.get(k) for k in ("speech_end_estimated_wall", "sealed_wall", "started_wall",
                                            "first_write_wall", "completed_wall", "sealed_estimated_wall")]
            if not all(_timestamp(v) is not None for v in clocks):
                continue
            speech, sealed, began, first, completed, estimated_seal = clocks
            if (not start <= speech <= sealed <= began <= first <= completed <= accepted["wall"]
                    or estimated_seal < speech):
                continue
            counts = [item.get(k) for k in ("connection_generation", "source_samples", "output_samples", "written_samples")]
            if (not all(type(v) is int and v > 0 for v in counts)
                    or counts[0] != accepted.get("connection") or counts[1] < counts[2] or counts[2] != counts[3]
                    or item.get("result") != "written_waiting_provider_boundary"
                    or item.get("input_timebase") != "arrival_derived_sample_estimate"):
                continue
            if item not in deliveries:
                deliveries.append(item)
        if len(deliveries) == 1:
            item = deliveries[0]
            result["phrase_status"] = "one_completed_write_in_this_turn"
            seconds.update(estimated_phrase_quiet=item["sealed_estimated_wall"] - item["speech_end_estimated_wall"],
                           input_end_to_phrase_seal=item["sealed_wall"] - end,
                           phrase_seal_to_write_start=item["started_wall"] - item["sealed_wall"],
                           phrase_write=item["completed_wall"] - item["started_wall"],
                           phrase_write_to_accepted_asr=accepted["wall"] - item["completed_wall"])
        elif deliveries:
            result["phrase_status"] = "ambiguous_multiple_writes"
        result["status"] = "observed_single_grade_turn"
        result["seconds"] = {k: round(v, 6) for k, v in seconds.items()}
    except (KeyError, TypeError, ValueError, IndexError):
        result.update(status="unavailable", seconds={}, phrase_status="unavailable")
    return result


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
                       **analyze_scene(scene, input_kind=args.input_kind),
                       "grade_latency": analyze_grade_latency(scene)})
    print(json.dumps({"wave": amplitude, "scenes": scenes, "external_calls": 0}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
