"""Offline evidence classification guards; synthesized amplitudes are never played."""
import array
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from neko_spoken_turn_analysis import analyze_scene, analyze_wave, parse_phrase_deliveries, analyze_grade_latency, parse_study_text_records


class SpokenTurnAnalysisTest(unittest.TestCase):
    def test_digest_capture_keeps_same_timestamp_deltas_in_actual_order_without_copying_body(self):
        first={'stage':'provider_delta','t':100.,'cid':'1234abcd','gen':2,'response_id':'r',
               'chars':3,'sha256':'a'*64}
        second={**first,'chars':4,'sha256':'b'*64}
        text='\n'.join('prefix [study-text] '+json.dumps(row) for row in (first,second))
        self.assertEqual(parse_study_text_records(text),[first,second])

    def test_malformed_or_content_bearing_diagnostics_are_not_copied_to_report(self):
        valid={'stage':'core_queue','t':100.,'cid':'1234abcd','chars':3,'sha256':'a'*64}
        invalid=[{**valid,'reply':'PRIVATE ANSWER'},{**valid,'t':True},{**valid,'chars':True},
                 {**valid,'stage':'unknown'},{**valid,'stage':[]},{**valid,'gen':True},
                 {**valid,'scope':'PRIVATE ANSWER'},{**valid,'sha256':'PRIVATE ANSWER'},
                 {**valid,'stream_sha256':'bad'},{**valid,'token':'x'*161}]
        text='[study-text] invalid\n'+ '\n'.join('[study-text] '+json.dumps(row) for row in invalid)
        self.assertEqual(parse_study_text_records(text),[])

    def test_pathological_json_cannot_abort_capture_or_hide_later_valid_record(self):
        valid={'stage':'core_queue','t':100.,'cid':'1234abcd','chars':3,'sha256':'a'*64}
        rows=[{**valid,'t':10**400},{**valid,'mono':10**400},valid]
        text='[study-text] '+'['*1100+'0'+']'*1100+'\n'
        text+='\n'.join('[study-text] '+json.dumps(row) for row in rows)
        self.assertEqual(parse_study_text_records(text),[valid])

    def scene(self):
        return {"input_audio_start_wall": 100., "fixed_speech_end_wall": 112., "manual_end_sent_wall": 113.2,
                "wire_trace": [
                    {"dir": "send", "type": "session.update", "t": 98., "turn_detection_present": True, "turn_detection": None},
                    {"dir": "send", "type": "session.update", "t": 99., "turn_detection_present": False},
                    *[{"dir": "recv", "type": "conversation.item.input_audio_transcription.completed", "t": t,
                       "transcript_chars": size} for t, size in ((105., 75), (111., 93), (113., 9))]],
                "native_final": {"trace": {"events": [{"type": "user_transcript", "wall": 105., "text": "Check material."},
                                                       {"type": "user_transcript", "wall": 111., "text": "Explain it."}]}}}

    def test_command_sequence_is_not_single_long_sentence_failure(self):
        result = analyze_scene(self.scene(), input_kind="command_sequence")
        self.assertEqual(result["provider_completions_before_speech_end"], 2)
        self.assertEqual(result["single_sentence_status"], "not_tested_by_this_material")
        self.assertEqual(analyze_scene(self.scene())["single_sentence_status"], "not_tested_by_this_material")

    def test_null_request_is_not_acceptance_and_later_partial_updates_remain_visible(self):
        result = analyze_scene(self.scene())
        self.assertTrue(result["explicit_null_request_seen"])
        self.assertFalse(result["provider_vad_echo_seen"])
        self.assertEqual(result["later_session_updates_omitting_vad_before_input"], 1)
        self.assertEqual(result["provider_completed_before_manual_end"], 3)

    def test_relative_clock_only_is_rejected_and_no_history_is_mixed(self):
        scene = self.scene()
        scene["native_final"]["trace"]["events"].append({"type": "user_transcript", "wall": 90., "text": "OLD HISTORY"})
        self.assertNotIn("OLD HISTORY", str(analyze_scene(scene)))
        del scene["fixed_speech_end_wall"]
        with self.assertRaises(ValueError): analyze_scene(scene)

    def test_declared_single_sentence_reports_observation_without_claiming_semantic_success(self):
        scene = self.scene()
        original = copy.deepcopy(scene)
        result = analyze_scene(scene, input_kind="single_sentence")
        self.assertEqual(result["single_sentence_status"], "early_provider_completion_observed")
        self.assertEqual(scene, original)
        self.assertNotIn("accepted", result)

    def test_wave_gap_measurement_uses_real_frame_rate_and_does_not_treat_silence_as_speech(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "amplitude.wav"
            for samples, expected in (([1000] * 500 + [0] * 900 + [1000] * 500, 1), ([0] * 1000, 0)):
                with wave.open(str(path), "wb") as output:
                    output.setparams((1, 2, 1000, 0, "NONE", "not compressed"))
                    output.writeframes(array.array("h", samples).tobytes())
                result = analyze_wave(path)
                self.assertEqual(len(result["amplitude_gaps"]), expected)
                if expected: self.assertEqual(result["amplitude_gaps"][0]["seconds"], .9)
                else: self.assertIsNone(result["last_active_end"])


class GradeLatencyTest(unittest.TestCase):
    def phrase(self):
        return dict(connection_generation=1, source_samples=17000, output_samples=16000,
                    compressed_zero_samples=1000, written_samples=16000,
                    input_timebase="arrival_derived_sample_estimate", speech_end_estimated_wall=110.07,
                    sealed_estimated_wall=111.28, sealed_wall=111.27, queue_wait_ms=0,
                    started_wall=111.27, first_write_wall=111.29, first_write_completed_ms=20,
                    completed_wall=111.31, write_elapsed_ms=40, result="written_waiting_provider_boundary")

    def rich_phrase(self):
        return dict(self.phrase(), input_sequence=1, output_pcm_sha256='b' * 64, captured_start_estimated_wall=100.,
                    compressed_zero_intervals=[[8000, 9000]], compressed_intervals_truncated=False,
                    local_append_count=2, local_append_writes_truncated=False,
                    local_append_writes=[{'samples': 8000, 'written_wall': 111.29, 'elapsed_ms': 20.},
                                         {'samples': 8000, 'written_wall': 111.30, 'elapsed_ms': 30.}])

    def test_extended_diagnostics_are_retained_without_raw_content_and_deduplicated(self):
        raw = dict(self.rich_phrase(), audio='PRIVATE PCM', owner_token='PRIVATE OWNER')
        line = 'native phrase delivery ' + json.dumps(raw)
        parsed = parse_phrase_deliveries(line + '\n' + line)
        self.assertEqual(parsed, [self.rich_phrase()])
        self.assertNotIn('PRIVATE', repr(parsed))

    def test_invalid_extended_diagnostics_cannot_smuggle_content_or_false_counts(self):
        raw = self.rich_phrase()
        cases = [('output_pcm_sha256', 'PRIVATE'), ('compressed_zero_intervals', [[8000, 19000]]),
                 ('compressed_zero_intervals', [[8000, 9000]] * 33),
                 ('local_append_writes', [{'samples': 16000, 'written_wall': 111.,
                                           'elapsed_ms': 3., 'token': 'PRIVATE'}]),
                 ('local_append_count', True), ('compressed_intervals_truncated', 'PRIVATE'),
                 ('input_sequence', 'PRIVATE'), ('source_samples', 18000),
                 ('captured_start_estimated_wall', float('inf'))]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.assertEqual(parse_phrase_deliveries('native phrase delivery ' +
                    json.dumps(dict(raw, **{key: value}))), [])

    def scene(self):
        ids = dict(course_id="course", session_id="session", question_id="q", attempt_id="a")
        return dict(turns=[dict(input_wall=100., fixed_speech_end_wall=110., observation_end_wall=130.)],
                    grade_markers=[dict(ids, stage=s, wall=w, token=t, connection=c, scope=scope) for s, w, t, c, scope in
                                   (("accepted", 120., "old", 1, 2), ("grade_complete", 124., "old", 1, 2),
                                    ("relay_written", 124.6, "new", 2, 4))],
                    native_final={"trace": {"events": [
                        dict(type="user_transcript", wall=120.01, text="PRIVATE ANSWER"),
                        dict(type="audio_frame", wall=125., correlation_id="new", bytes=0),
                        dict(type="audio_frame", wall=127., correlation_id="new", bytes=3200),
                        dict(type="speech_playback_state", wall=127.5, correlationId="new",
                             active=True, reason="chunk_scheduled")]}},
                    wire_trace=[dict(dir="recv", type="conversation.item.input_audio_transcription.completed", t=119.99)],
                    phrase_deliveries=[self.phrase()])

    def test_existing_count_log_duplicate_handlers_are_deduplicated_and_private_fields_dropped(self):
        raw = dict(self.phrase(), transcript="PRIVATE ANSWER", owner_token="PRIVATE TOKEN", audio="SECRET PCM")
        line = "host - native phrase delivery " + json.dumps(raw)
        parsed = parse_phrase_deliveries(line + "\n" + line.replace("host -", "other-handler -"))
        self.assertEqual(parsed, [self.phrase()])
        self.assertNotIn("PRIVATE", repr(parsed)); self.assertNotIn("SECRET", repr(parsed))
        self.assertEqual(parse_phrase_deliveries("unrelated credential=SECRET"), [])
        for key, value in (("result", "failed_without_retry"), ("written_samples", True),
                           ("first_write_wall", float("nan")), ("first_write_wall", -1),
                           ("input_timebase", "unknown")):
            self.assertEqual(parse_phrase_deliveries("native phrase delivery " + json.dumps(dict(raw, **{key: value}))), [])
        self.assertEqual(parse_phrase_deliveries("native phrase delivery []\nnative phrase delivery {bad"), [])

    def test_end_to_end_and_phrase_segments_use_distinct_observation_clocks(self):
        scene = self.scene(); before = copy.deepcopy(scene); result = analyze_grade_latency(scene)
        self.assertEqual(result["status"], "observed_single_grade_turn")
        self.assertEqual(result["phrase_status"], "one_completed_write_in_this_turn")
        values = result["seconds"]
        for key, expected in (("input_end_to_accepted_asr", 10.), ("accepted_asr_to_grade", 4.),
                              ("grade_to_relay_write", .6), ("input_end_to_native_pcm", 17.),
                              ("pcm_to_native_schedule", .5), ("input_end_to_native_schedule", 17.5),
                              ("input_end_to_native_asr", 10.01), ("input_end_to_provider_asr", 9.99),
                              ("estimated_phrase_quiet", 1.21), ("input_end_to_phrase_seal", 1.27), ("phrase_write", .04),
                              ("phrase_write_to_accepted_asr", 8.69)):
            self.assertEqual(values[key], expected, key)
        self.assertEqual(result["physical_playback_start"], "unverified")
        self.assertEqual(result["external_calls"], 0); self.assertEqual(scene, before)
        self.assertNotIn("PRIVATE ANSWER", repr(result)); self.assertNotIn("token", repr(result))

    def test_zero_bytes_old_owner_history_or_heartbeat_cannot_prove_pcm_or_schedule(self):
        scene = self.scene(); events = scene["native_final"]["trace"]["events"]
        events += [dict(type="audio_frame", wall=118., correlation_id="old", bytes=99),
                   dict(type="user_transcript", wall=90., text="OLD"),
                   dict(type="speech_playback_state", wall=126., correlationId="new", active=True, reason="heartbeat")]
        self.assertEqual(analyze_grade_latency(scene)["seconds"]["input_end_to_native_pcm"], 17.)
        for invalid in (0, True, -1, 3.5, float("nan")):
            events[2]["bytes"] = invalid
            result = analyze_grade_latency(scene)["seconds"]
            self.assertNotIn("input_end_to_native_pcm", result)
            self.assertNotIn("pcm_to_native_schedule", result)

    def test_missing_or_ambiguous_phrase_is_not_filled_from_another_turn_or_connection(self):
        scene = self.scene(); phrase = scene["phrase_deliveries"][0]
        for invalid in ([], [dict(phrase, connection_generation=2)], [dict(phrase, written_samples=1)],
                        [dict(phrase, sealed_wall=99.)], [dict(phrase, completed_wall=121.)],
                        [dict(phrase, source_samples=True)]):
            scene["phrase_deliveries"] = invalid
            result = analyze_grade_latency(scene)
            self.assertEqual(result["phrase_status"], "unavailable")
            self.assertNotIn("phrase_write_to_accepted_asr", result["seconds"])
        scene["phrase_deliveries"] = [phrase, dict(phrase, completed_wall=111.32)]
        self.assertEqual(analyze_grade_latency(scene)["phrase_status"], "ambiguous_multiple_writes")

    def test_ambiguous_asr_cannot_select_a_convenient_transcript(self):
        scene = self.scene(); scene["native_final"]["trace"]["events"].append(dict(type="user_transcript", wall=121.))
        scene["wire_trace"].append(dict(dir="recv", type="conversation.item.input_audio_transcription.completed", t=121.))
        result = analyze_grade_latency(scene)["seconds"]
        self.assertNotIn("input_end_to_native_asr", result)
        self.assertNotIn("input_end_to_provider_asr", result)
        for different in (False, True):
            scene = self.scene(); duplicate = dict(scene["wire_trace"][0])
            if different: duplicate["transcript_chars"] = 999
            scene["wire_trace"].append(duplicate)
            self.assertNotIn("input_end_to_provider_asr", analyze_grade_latency(scene)["seconds"])

    def test_missing_invalid_cross_question_or_multiturn_markers_never_get_full_metrics(self):
        scene = self.scene()
        for invalid in ({}, dict(scene, turns=[scene["turns"][0]] * 2), dict(scene, grade_markers=[])):
            self.assertEqual(analyze_grade_latency(invalid)["status"], "unavailable")
        for key, value in (("question_id", "foreign"), ("wall", 119.), ("wall", float("inf"))):
            modified = copy.deepcopy(scene); modified["grade_markers"][1][key] = value
            result = analyze_grade_latency(modified)
            self.assertEqual(result["status"], "unavailable"); self.assertEqual(result["seconds"], {})

    def test_foreign_missing_or_noninteger_connection_and_scope_cannot_attribute_latency(self):
        for index, key, value in ((0, "connection", True), (0, "connection", 0), (1, "connection", 9),
                                  (1, "scope", 3), (1, "scope", None), (1, "scope", 2.),
                                  (1, "token", "foreign"), (2, "connection", 3), (2, "scope", 2)):
            scene = self.scene(); scene["grade_markers"][index][key] = value
            self.assertEqual(analyze_grade_latency(scene)["status"], "unavailable")


if __name__ == "__main__": unittest.main(verbosity=2)
