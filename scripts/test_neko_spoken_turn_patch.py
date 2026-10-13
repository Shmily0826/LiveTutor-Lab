"""Offline checks of the diagnostic candidate against actual current trace source."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import types
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from neko_spoken_turn_patch import patch_wire_trace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates/N.E.K.O/main_logic/omni_realtime_client/_wire_trace.py"


class SpokenTurnTraceTest(unittest.TestCase):
    def setUp(self):
        self.original = SOURCE.read_text(encoding="utf-8")
        self.patched = patch_wire_trace(self.original)
        self.module = types.ModuleType("spoken_turn_trace_candidate")
        exec(compile(self.patched, str(SOURCE), "exec"), self.module.__dict__)

    def test_replay_idempotent_and_unknown_source_refused(self):
        self.assertEqual(patch_wire_trace(self.patched), self.patched)
        with self.assertRaises(ValueError):
            patch_wire_trace("# wrong revision\n")

    def test_request_and_provider_report_are_distinct_without_inventing_acceptance(self):
        requested = self.module.summarize_send_event({"type": "session.update", "session": {
            "turn_detection": {"type": "server_vad", "silence_duration_ms": 650, "threshold": .5,
                               "secret": "SECRET", "instructions": "SECRET"}, "tools": []}})
        reported = self.module.summarize_recv_event({"type": "session.updated", "session": {"tools": []}})
        self.assertEqual(requested["turn_config_source"], "client_requested")
        self.assertEqual(requested["turn_detection.silence_duration_ms"], 650)
        self.assertEqual(reported["turn_config_source"], "provider_reported")
        self.assertFalse(reported["turn_detection_present"])
        self.assertNotIn("turn_detection.silence_duration_ms", reported)
        self.assertNotIn("SECRET", json.dumps(requested))

    def test_google_and_nested_config_whitelist_never_dumps_payloads(self):
        event = {"type": "session.updated", "session": {
            "audio": {"input": {"turn_detection": {"type": "server_vad", "silence_duration_ms": 800}}},
            "realtimeInputConfig": {"automaticActivityDetection": {
                "silenceDurationMs": 1000, "endOfSpeechSensitivity": "END_SENSITIVITY_LOW", "disabled": False,
                "threshold": "SECRET", "api_key": "SECRET", "prefixPaddingMs": float("nan")}},
            "instructions": "SECRET"}}
        record = self.module.summarize_recv_event(event)
        self.assertEqual(record["audio.input.turn_detection.silence_duration_ms"], 800)
        self.assertEqual(record["realtimeInputConfig.automaticActivityDetection.silenceDurationMs"], 1000)
        self.assertNotIn("SECRET", json.dumps(record))
        self.assertNotIn("NaN", json.dumps(record))

    def test_speech_offsets_and_transcript_size_keep_ids_but_not_text(self):
        started = self.module.summarize_recv_event({"type": "input_audio_buffer.speech_started", "item_id": "i1", "audio_start_ms": 1234})
        stopped = self.module.summarize_recv_event({"type": "input_audio_buffer.speech_stopped", "item_id": "i1", "audio_end_ms": 2345})
        transcript = self.module.summarize_recv_event({"type": "conversation.item.input_audio_transcription.completed",
            "item_id": "i1", "transcript": "PRIVATE WORDS", "audio": "SECRET"})
        self.assertEqual(started["audio_start_ms"], 1234)
        self.assertEqual(stopped["audio_end_ms"], 2345)
        self.assertEqual(transcript["transcript_chars"], 13)
        self.assertEqual(transcript["item_id"], "i1")
        self.assertNotIn("PRIVATE", json.dumps(transcript))
        self.assertNotIn("SECRET", json.dumps(transcript))

    def test_both_clocks_and_existing_audio_append_throttle_remain(self):
        records = []
        logger = types.SimpleNamespace(info=lambda prefix, marker, payload: records.append(json.loads(payload)))
        trace = self.module.RealtimeWireTrace(logger)
        trace.record_send({"type": "input_audio_buffer.append", "audio": "SECRET"}, generation=1)
        self.assertEqual(records, [])
        trace.record_send({"type": "input_audio_buffer.commit"}, generation=1)
        trace.record_recv({"type": "conversation.item.input_audio_transcription.completed", "transcript": "PRIVATE"}, generation=1)
        self.assertEqual(records[0]["audio_appends_total"], 1)
        for record in records:
            self.assertIn("t", record)
            self.assertIn("mono", record)
            self.assertEqual(record["gen"], 1)
        self.assertNotIn("PRIVATE", json.dumps(records))
        self.assertNotIn("SECRET", json.dumps(records))


if __name__ == "__main__":
    unittest.main(verbosity=2)
