"""Offline evidence classification guards; synthesized amplitudes are never played."""
import array
import copy
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from neko_spoken_turn_analysis import analyze_scene, analyze_wave


class SpokenTurnAnalysisTest(unittest.TestCase):
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


if __name__ == "__main__": unittest.main(verbosity=2)
