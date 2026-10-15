"""Local-only PCM/chunk/clock checks; existing WAV is read, never rewritten."""
import hashlib
from pathlib import Path
import struct
import unittest
import wave

from neko_phrase_input_buffer import (
    PhraseBufferError, PhraseInputBuffer, PhraseOwnership, PhraseState,
)

ROOT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def pcm(seconds, value=0):
    return struct.pack("<h", value) * round(seconds * 16_000)


class CollectorChecks(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.owner = PhraseOwnership("session-A", ("socket-A", "activation-A", "core"), 1)
        self.buffer = PhraseInputBuffer(self.owner, clock=self.clock)

    def feed(self, data, speech, *, size=640):
        for offset in range(0, len(data), size):
            chunk = data[offset:offset + size]
            self.buffer.feed(chunk, speech_active=speech, ownership=self.owner,
                             captured_at=self.clock.now)
            self.clock.now += len(chunk) / 32_000
        return self.buffer.state

    def finish(self):
        self.feed(pcm(1.2), False)
        self.assertIs(self.buffer.state, PhraseState.SEALED)
        return self.buffer.take(ownership=self.owner)

    def test_900ms_internal_zero_pause_then_end_seals_once_and_preserves_speech(self):
        first = pcm(.3, 512) + pcm(.2, -327)
        second = pcm(.2, 13) + pcm(.3, 1700)
        self.feed(first, True)
        self.feed(pcm(.9), False)
        self.assertIs(self.buffer.state, PhraseState.OPEN)
        self.feed(second, True)
        result = self.finish()
        self.assertEqual(result.pcm16, first + pcm(.1) + second + pcm(1.2))
        self.assertEqual(result.compressed_zero_samples, 12_800)
        self.assertEqual(result.compressed_zero_intervals, ((9600, 22400),))
        self.assertFalse(result.compressed_intervals_truncated)
        self.assertEqual(result.source_samples - result.output_samples, 12_800)
        self.assertTrue(result.local_phrase_id.startswith("local_phrase_"))
        self.assertEqual(result.ownership, self.owner)
        self.assertEqual(self.buffer.buffered_bytes, 0)
        with self.assertRaisesRegex(PhraseBufferError, "already_taken"):
            self.buffer.take(ownership=self.owner)

    def test_compression_coordinates_reconstruct_bytes_with_leading_and_trailing_silence(self):
        parts = [(pcm(.2), False), (pcm(.1, 40), True), (pcm(.3), False),
                 (pcm(.1, 70), True), (pcm(.5), False), (pcm(.1, 90), True)]
        for data, speech in parts:
            self.feed(data, speech)
        result = self.finish()
        original = b''.join(data for data, _ in parts) + pcm(1.2)
        self.assertEqual(result.compressed_zero_intervals, ((6400, 9600), (12800, 19200)))
        rebuilt = bytearray()
        previous = 0
        for start, end in result.compressed_zero_intervals:
            rebuilt.extend(original[previous * 2:start * 2])
            self.assertFalse(any(original[start * 2:end * 2]))
            previous = end
        rebuilt.extend(original[previous * 2:])
        self.assertEqual(bytes(rebuilt), result.pcm16)
        self.assertEqual(sum(end - start for start, end in result.compressed_zero_intervals),
                         result.compressed_zero_samples)

    def test_diagnostic_interval_limit_does_not_limit_actual_compression(self):
        for _ in range(35):
            self.feed(pcm(.01, 50), True)
            self.feed(pcm(.2), False)
        self.feed(pcm(.01, 80), True)
        result = self.finish()
        self.assertEqual(len(result.compressed_zero_intervals), 32)
        self.assertTrue(result.compressed_intervals_truncated)
        self.assertEqual(result.compressed_zero_samples, 35 * 1600)
        self.assertEqual(result.source_samples - result.output_samples, 35 * 1600)

    def test_soft_nonzero_vad_false_pause_not_cut(self):
        first, last = pcm(.2, 640), pcm(.2, -640)
        soft = struct.pack("<hhh", 1, -1, 256) * 4800  # .9s, quiet by VAD only.
        self.feed(first, True)
        self.feed(soft, False)
        self.assertIs(self.buffer.state, PhraseState.OPEN)
        self.feed(last, True)
        result = self.finish()
        self.assertEqual(result.pcm16, first + soft + last + pcm(1.2))
        self.assertEqual(result.compressed_zero_samples, 0)

    def test_one_nonzero_sample_prevents_whole_frame_compression(self):
        self.feed(pcm(.2, 700), True)
        frame = pcm(.02)[:-2] + struct.pack("<h", 1)
        pause = frame * 45
        self.feed(pause, False)
        self.feed(pcm(.2, 800), True)
        result = self.finish()
        self.assertIn(pause, result.pcm16)
        self.assertEqual(result.compressed_zero_samples, 0)

    def test_zero_pcm_marked_speech_is_preserved(self):
        self.feed(pcm(.2, 4), True)
        self.feed(pcm(.9), True)
        self.feed(pcm(.2, 8), True)
        result = self.finish()
        self.assertEqual(result.pcm16, pcm(.2, 4) + pcm(.9) + pcm(.2, 8) + pcm(1.2))
        self.assertEqual(result.compressed_zero_samples, 0)

    def test_clock_tick_end_is_bounded_and_requires_observed_quiet(self):
        self.feed(pcm(.5, 10), True)
        self.clock.now += 1.3
        self.assertIs(self.buffer.tick(ownership=self.owner), PhraseState.OPEN)
        self.buffer.feed(pcm(.02), speech_active=False, ownership=self.owner, captured_at=self.clock.now)
        self.clock.now += 1.199
        self.assertIs(self.buffer.tick(ownership=self.owner), PhraseState.OPEN)
        self.clock.now += .001
        self.assertIs(self.buffer.tick(ownership=self.owner), PhraseState.SEALED)
        result = self.buffer.take(ownership=self.owner)
        # Tick seals owned bytes; it never manufactures 1.2s audio or new frames.
        self.assertEqual(result.pcm16, pcm(.5, 10) + pcm(.02))

    def test_exact_20_seconds_then_extra_sample_fails_without_truncation(self):
        self.feed(pcm(20, 42), True)
        self.assertIs(self.buffer.state, PhraseState.OPEN)
        self.assertEqual(self.buffer.buffered_bytes, 640_000)
        self.assertEqual(self.buffer.peak_buffered_bytes, 640_000)
        with self.assertRaisesRegex(PhraseBufferError, "phrase_byte_limit"):
            self.feed(struct.pack("<h", 42), True)
        self.assertIs(self.buffer.state, PhraseState.FAILED)
        self.assertEqual(self.buffer.buffered_bytes, 0)
        with self.assertRaises(PhraseBufferError):
            self.buffer.take(ownership=self.owner)

    def test_capture_wall_limit_and_timer_limit_fail_even_without_byte_overflow(self):
        self.feed(pcm(.1, 12), True)
        self.clock.now = 120.01
        with self.assertRaisesRegex(PhraseBufferError, "phrase_duration_limit"):
            self.buffer.tick(ownership=self.owner)
        self.assertEqual(self.buffer.buffered_bytes, 0)
        self.buffer = PhraseInputBuffer(self.owner, clock=self.clock)
        self.feed(pcm(.1, 12), True)
        self.clock.now += 20
        with self.assertRaisesRegex(PhraseBufferError, "phrase_duration_limit"):
            self.feed(pcm(.02, 12), True)
        self.assertEqual(self.buffer.buffered_bytes, 0)

    def test_compression_never_increases_source_duration_budget(self):
        for _ in range(10):
            self.feed(pcm(.1, 15), True)
            self.feed(pcm(.9), False)
        self.feed(pcm(.1, 15), True)
        self.assertLess(self.buffer.buffered_bytes, 100_000)
        with self.assertRaises(PhraseBufferError):
            self.feed(pcm(10, 15), True)
        self.assertEqual(self.buffer.buffered_bytes, 0)

    def test_session_owner_connection_replacement_invalidates_even_sealed(self):
        alternatives = (PhraseOwnership("session-B", self.owner.owner_token, 1),
                        PhraseOwnership("session-A", ("socket-A", "activation-B", "core"), 1),
                        PhraseOwnership("session-A", self.owner.owner_token, 2))
        for changed in alternatives:
            for sealed in (False, True):
                with self.subTest(changed=changed, sealed=sealed):
                    self.buffer = PhraseInputBuffer(self.owner, clock=self.clock)
                    self.feed(pcm(.1, 17), True)
                    if sealed: self.feed(pcm(1.2), False)
                    with self.assertRaisesRegex(PhraseBufferError, "ownership_changed"):
                        self.buffer.take(ownership=changed)
                    self.assertEqual(self.buffer.buffered_bytes, 0)
                    with self.assertRaises(PhraseBufferError):
                        self.buffer.take(ownership=self.owner)

    def test_worker_ownership_check_after_take_and_close_refuses_old_snapshot(self):
        self.feed(pcm(.1, 21), True)
        self.finish()
        self.buffer.assert_current(self.owner)  # Ownership can be checked between writes.
        changed = PhraseOwnership("session-A", self.owner.owner_token, 2)
        with self.assertRaisesRegex(PhraseBufferError, "ownership_changed"):
            self.buffer.assert_current(changed)
        with self.assertRaises(PhraseBufferError):
            self.buffer.assert_current(self.owner)
        self.buffer = PhraseInputBuffer(self.owner, clock=self.clock)
        self.feed(pcm(.1, 21), True)
        self.feed(pcm(1.2), False)
        self.buffer.close()
        self.assertEqual(self.buffer.buffered_bytes, 0)
        for operation in (lambda: self.buffer.take(ownership=self.owner),
                          lambda: self.feed(pcm(.1), False)):
            with self.assertRaisesRegex(PhraseBufferError, "phrase_closed"):
                operation()

    def test_after_seal_feed_refused_does_not_reopen_or_replay(self):
        self.feed(pcm(.1, 28), True)
        self.feed(pcm(1.2), False)
        with self.assertRaisesRegex(PhraseBufferError, "phrase_not_open"):
            self.feed(pcm(.1, 99), True)
        result = self.buffer.take(ownership=self.owner)
        self.assertNotIn(pcm(.1, 99), result.pcm16)
        with self.assertRaisesRegex(PhraseBufferError, "phrase_not_open"):
            self.feed(pcm(.1, 99), True)

    def test_all_silent_never_seals_and_bad_frame_time_verdict_fail_closed(self):
        self.feed(pcm(1.5), False)
        self.assertIs(self.buffer.state, PhraseState.OPEN)
        with self.assertRaises(PhraseBufferError): self.buffer.take(ownership=self.owner)
        for data, speech, when in ((b"\x01", True, 100), (pcm(.01), None, 100),
                                   (pcm(.01), False, float("nan"))):
            self.buffer = PhraseInputBuffer(self.owner, clock=self.clock)
            with self.assertRaises(PhraseBufferError):
                self.buffer.feed(data, speech_active=speech, ownership=self.owner, captured_at=when)
            self.assertEqual(self.buffer.buffered_bytes, 0)
        self.buffer = PhraseInputBuffer(self.owner, clock=self.clock)
        self.buffer.feed(pcm(.01, 30), speech_active=True, ownership=self.owner, captured_at=100)
        with self.assertRaisesRegex(PhraseBufferError, "capture_time_reversed"):
            self.buffer.feed(pcm(.01, 30), speech_active=True, ownership=self.owner, captured_at=99)

    def test_existing_neighbor_wav_readonly_resample_chunks_preserve_nonzero_samples(self):
        import numpy as np
        import soxr
        path = ROOT / "benchmarks/raw/voice-input/daily-picture-constraints-single-utterance-20261014.wav"
        expected_sha = "6b6182d69b2a0ea0e12cb8bae72be5edee5629abe65f600c2201e16242eeb93d"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_sha)
        with wave.open(str(path)) as wav:
            self.assertEqual((wav.getnchannels(), wav.getsampwidth()), (1, 2))
            original = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
            # In-memory only, using the project's existing soxr/HQ dependency.
            normalized = soxr.resample(original.astype(np.float32) / 32768, wav.getframerate(), 16_000, quality="HQ")
        raw = (normalized * 32768).clip(-32768, 32767).astype("<i2").tobytes()
        for offset in range(0, len(raw), 640):
            chunk = raw[offset:offset + 640]
            # A conservative fixture verdict: every nonzero frame is speech.
            # This is not RNNoise/VAD or model acceptance evidence.
            self.feed(chunk, bool(any(chunk)))
        result = self.finish()
        source = np.frombuffer(raw, dtype="<i2")
        output = np.frombuffer(result.pcm16, dtype="<i2")
        np.testing.assert_array_equal(output[output != 0], source[source != 0])
        self.assertLessEqual(self.buffer.peak_buffered_bytes, 640_000)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_sha)


if __name__ == "__main__":
    unittest.main(verbosity=2)
