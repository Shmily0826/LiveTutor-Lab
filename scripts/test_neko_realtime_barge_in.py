"""Talking over the character: what is reachable on the free route, and what is not.

Two claims live in this file, and they are deliberately kept apart.

1. The provider's own cancellation is unreachable here. `handle_interruption` returns unless
   `_is_responding`; that is set only by `_begin_response_lifecycle`, whose two callers are a
   `response.created` the proxy never sends, and an id-bearing-content fallback that this route's
   protocol profile disqualifies for function calls and that needs an owner ticket for a response
   we asked for. Three drafts wired to that path were inert and were withdrawn; the tests below
   keep the reason executable instead of remembered.

2. Stopping the *playback* does not need any of that. The host already gates every outgoing delta
   behind `not self._skip_until_next_response and not self._interrupted`, and it writes
   `_ai_recent_activity_time` at that delivery site - so a local, self-clearing mute beside that
   gate works on a route that is silent about turn boundaries. That is what
   `TRANSPORT_REPLACEMENTS` installs, and what the second half of this file tests.

Offline, no devices, no model, no network. These tests decide *whether to mute* and *when to stop
muting*. Whether the learner hears the difference - and how much audio the OS had already queued -
is L3/L4 and belongs to the listening test, not to this file.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "benchmarks" / "raw" / "neko-product-host"
sys.path.insert(0, str(HOST))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main_logic.omni_realtime_client import OmniRealtimeClient  # noqa: E402
from main_logic.omni_realtime_client._protocol_capabilities import (  # noqa: E402
    LANLAN_APP_REALTIME_PROTOCOL_CAPABILITIES,
    STRICT_REALTIME_PROTOCOL_CAPABILITIES,
)
from main_logic.omni_realtime_client._response_arbiter import RealtimeResponseArbiter  # noqa: E402
from main_logic.omni_realtime_client import _transport as transport_mod  # noqa: E402

from test_neko_tool_result_lifecycle import LogRecorder, QueueSocket  # noqa: E402

LOUD_48K = b"\x00\x40" * 480    # one RNNoise frame
LOUD_16K = b"\x00\x40" * 512    # the desktop uplink frame - the path production runs on
QUIET_16K = b"\x00\x00" * 512
TRANSPORT = HOST / "main_logic" / "omni_realtime_client" / "_transport.py"


FRAME_STEP = 0.032         # the uplink cadence the desktop route feeds `stream_audio` at


def barge_in_frames(client) -> int:
    """Frames of unbroken loud audio that pass the sustained window the mute asks for.

    The first loud frame only opens the window, so the arming lands one frame later.
    """
    return int(client._LOCAL_BARGE_IN_SECONDS / FRAME_STEP) + 2


class RealtimeClientFixture(unittest.TestCase):
    def _client(self, *, talking: bool = True, server_vad: bool = False,
                gemini: bool = False) -> tuple[OmniRealtimeClient, QueueSocket]:
        client = OmniRealtimeClient("wss://example.invalid/realtime", "test-key",
                                     api_type="gpt", on_tool_call=None)
        socket = QueueSocket()
        client.ws = socket
        client._on_connection_attached()
        client._has_server_vad = server_vad
        client._is_gemini = gemini
        client._is_responding = False
        client._interrupted = False
        client._fatal_error_occurred = False
        client._ai_recent_activity_time = time.time() if talking else 0.0
        client._last_delivered_response_id = "resp_old"

        async def passthrough(chunk: bytes) -> bytes:
            return chunk

        client.process_audio_chunk_async = passthrough  # type: ignore[assignment]
        return client, socket

    async def _speak(self, client: OmniRealtimeClient, frames: int, *, quiet: bool = False,
                     chunk: bytes = LOUD_16K, start: float = 100.0,
                     speech_active: bool | None = None) -> None:
        for index in range(frames):
            await client.stream_audio(QUIET_16K if quiet else chunk,
                                      captured_at=start + index * 0.032,
                                      speech_active=speech_active)


class ProviderCancellationIsUnreachableTest(RealtimeClientFixture):
    """Claim 1: the existing cancellation cannot be reached on this route."""

    def test_the_gate_only_opens_for_a_response_the_host_believes_is_live(self) -> None:
        async def scenario() -> None:
            quiet, quiet_socket = self._client()
            await quiet.handle_interruption()
            self.assertEqual([event.get("type") for event in quiet_socket.sent].count(
                "response.cancel"), 0, "a response the host does not know about was cancelled")

            client, socket = self._client()
            client._is_responding = True
            client._current_response_id = "resp_new"
            await client.handle_interruption()
            self.assertEqual([event.get("type") for event in socket.sent].count(
                "response.cancel"), 1,
                "the host's own cancellation is broken, which would make this blocker read as a "
                "different bug than it is")

        asyncio.run(scenario())

    def test_function_call_evidence_is_not_start_evidence_on_the_free_route(self) -> None:
        sent: list[dict] = []
        arbiter = RealtimeResponseArbiter(lambda payload: sent.append(payload),
                                          protocol_capabilities=LANLAN_APP_REALTIME_PROTOCOL_CAPABILITIES)
        self.assertTrue(arbiter._protocol_capabilities.accepts_id_bearing_content_start)
        self.assertFalse(arbiter._protocol_capabilities.function_call_ids_match_terminal)
        for event_type in ("response.function_call_arguments.delta",
                           "response.function_call_arguments.done"):
            self.assertFalse(
                arbiter.notify_response_content({"type": event_type, "response_id": "resp_1"}),
                f"{event_type} was allowed to open a response lifecycle",
            )
        self.assertEqual(sent, [], "the refusal also wrote to the wire")

    def test_an_unrequested_response_cannot_open_a_lifecycle(self) -> None:
        arbiter = RealtimeResponseArbiter(lambda payload: None,
                                          protocol_capabilities=LANLAN_APP_REALTIME_PROTOCOL_CAPABILITIES)
        self.assertIsNone(arbiter._response_owner, "the arbiter is no longer idle when unasked")
        self.assertFalse(
            arbiter.notify_response_content({"type": "response.audio.delta",
                                             "response_id": "resp_1", "delta": "AA"}),
            "a response nobody asked for opened a lifecycle, which would make the mute redundant")

    def test_strict_routes_do_not_have_the_fallback_at_all(self) -> None:
        arbiter = RealtimeResponseArbiter(lambda payload: None,
                                          protocol_capabilities=STRICT_REALTIME_PROTOCOL_CAPABILITIES)
        self.assertFalse(arbiter._protocol_capabilities.accepts_id_bearing_content_start)
        self.assertFalse(arbiter.notify_response_content({"type": "response.text.delta",
                                                          "response_id": "resp_1", "delta": "x"}))


class LocalPlaybackMuteTest(RealtimeClientFixture):
    """Claim 2: the local mute arms on sustained speech, keys to a response, and lets go."""

    def setUp(self) -> None:
        self.recorder = LogRecorder()
        self._real_logger = transport_mod.logger
        transport_mod.logger = self.recorder  # type: ignore[attr-defined]

    def tearDown(self) -> None:
        transport_mod.logger = self._real_logger  # type: ignore[attr-defined]

    def test_sustained_speech_mutes_the_answer_and_a_new_response_releases_it(self) -> None:
        async def scenario() -> None:
            client, _socket = self._client()
            frames = barge_in_frames(client)
            await self._speak(client, frames - 1)
            self.assertFalse(client._output_locally_muted({"response_id": "resp_old"}),
                             "the answer went silent on an unfinished utterance")
            await self._speak(client, 1, start=100.0 + (frames - 1) * 0.032)
            self.assertEqual(client._muted_response_id, "resp_old",
                             "sustained speech over a live answer armed nothing")
            self.assertTrue(client._output_locally_muted({"response_id": "resp_old"}),
                            "the old answer is still being delivered")
            # The guard asks the bookkeeping call first, then decides - mirror that order, because
            # releasing is the bookkeeping's job, not the predicate's.
            client._note_output_delivery({"response_id": "resp_new"})
            self.assertIsNone(client._muted_response_id, "the mute did not release on the new id")
            self.assertFalse(client._output_locally_muted({"response_id": "resp_new"}),
                             "the learner's next answer was muted along with the old one")
            self.assertTrue(any("suppressing the rest of response=resp_old" in line
                                for _, line in self.recorder.lines), self.recorder.text())
            self.assertTrue(any("released on a new response" in line
                                for _, line in self.recorder.lines), self.recorder.text())

        asyncio.run(scenario())

    def test_owner_trace_reports_dispatch_and_current_speech_without_rotating_the_turn(self) -> None:
        async def scenario() -> None:
            for current in ("speech-next", "speech-old"):
                client, _socket = self._client()
                client.get_host_turn_id = lambda: current
                client._local_audio_dispatch_owner = (client._connection_generation, "speech-old", "resp_old")
                scope = client._tool_scope_generation
                await client._handle_local_speech_onset("speech-sustained")
                self.assertIn(f"dispatch_speech=speech-old current_speech={current}", self.recorder.text())
                self.assertEqual(client.get_host_turn_id(), current)
                self.assertEqual(client._tool_scope_generation, scope)
                self.assertFalse(client._is_responding)
        asyncio.run(scenario())

    def test_one_loud_moment_and_a_broken_streak_arm_nothing(self) -> None:
        async def scenario() -> None:
            client, _socket = self._client()
            frames = barge_in_frames(client)
            await self._speak(client, 1)
            await self._speak(client, 1, quiet=True, start=200.0)
            self.assertIsNone(getattr(client, "_muted_response_id", None),
                              "a keyboard click silenced the teacher")
            await self._speak(client, frames - 1, start=300.0)
            await self._speak(client, 1, quiet=True, start=300.0 + (frames - 1) * 0.032)
            await self._speak(client, frames - 1, start=400.0)
            self.assertIsNone(getattr(client, "_muted_response_id", None),
                              "two bursts of noise, each short of the window, added up into one "
                              "interruption")
            await self._speak(client, 1, start=400.0 + (frames - 1) * 0.032)
            self.assertEqual(getattr(client, "_muted_response_id", None), "resp_old",
                             "speech that really did hold for half a second never cut in")

        asyncio.run(scenario())

    def test_a_sentence_that_breathes_arms_and_a_single_word_does_not(self) -> None:
        """Speech is not an unbroken tone, so the window tolerates short gaps.

        Measured 2026-10-12 by replaying a real recorded question through the host's own
        `utils.audio_processor.AudioProcessor`: 39% of the 48 kHz frames clear the int16 RMS
        gate, but the longest run with no dip at all is 0.45 s (0.16 s after denoising). A
        half-second of *unbroken* loudness is therefore not a thing a learner does, which is why
        five live sessions armed nothing while every test here stayed green on a constant tone.
        """
        step = 0.010

        async def say(client, words: int, breath: float, run: float) -> None:
            t = 900.0
            for _ in range(words):
                for _ in range(int(run / step)):
                    await client.stream_audio(LOUD_16K, captured_at=t)
                    t += step
                for _ in range(int(breath / step)):
                    await client.stream_audio(QUIET_16K, captured_at=t)
                    t += step

        async def scenario() -> None:
            client, _socket = self._client()
            await say(client, 3, client._LOCAL_BARGE_IN_GAP_SECONDS - 0.02, 0.25)
            self.assertEqual(getattr(client, "_muted_response_id", None), "resp_old",
                             "a sentence interrupted by nothing because it took a breath")

            quiet_client, _ = self._client()
            await say(quiet_client, 1, 1.0, 0.4)
            self.assertIsNone(getattr(quiet_client, "_muted_response_id", None),
                              "one word, then a real pause, silenced the teacher")

        asyncio.run(scenario())

    def test_nothing_being_spoken_arms_nothing(self) -> None:
        """The echo gate: if no output went by recently, there is nothing to stop."""
        async def scenario() -> None:
            client, _socket = self._client(talking=False)
            await self._speak(client, barge_in_frames(client) * 2)
            self.assertIsNone(getattr(client, "_muted_response_id", None),
                              "the character was muted while it was already silent")
            self.assertTrue(any("onset declined" in line for _, line in self.recorder.lines),
                            self.recorder.text())

        asyncio.run(scenario())

    def test_without_a_response_anchor_it_refuses_and_says_so(self) -> None:
        """Muting output we cannot attribute would silence the wrong answer."""
        async def scenario() -> None:
            client, _socket = self._client()
            client._last_delivered_response_id = None
            await self._speak(client, barge_in_frames(client))
            self.assertIsNone(getattr(client, "_muted_response_id", None))
            self.assertTrue(any("no response anchor" in line for _, line in self.recorder.lines),
                            self.recorder.text())

        asyncio.run(scenario())

    def test_the_mute_expires_even_if_no_new_response_id_arrives(self) -> None:
        """A wedge is the failure this project already paid for; the mute must be temporary."""
        async def scenario() -> None:
            client, _socket = self._client()
            await self._speak(client, barge_in_frames(client))
            self.assertEqual(client._muted_response_id, "resp_old")
            client._muted_at = time.monotonic() - client._LOCAL_MUTE_MAX_SECONDS - 1
            self.assertFalse(client._output_locally_muted({"response_id": "resp_old"}),
                             "the mute outlived its deadline and the character stayed silent")
            self.assertTrue(any("mute expired" in line for _, line in self.recorder.lines),
                            self.recorder.text())

        asyncio.run(scenario())

    def test_routes_that_already_own_their_boundaries_are_left_alone(self) -> None:
        async def scenario() -> None:
            for kwargs in ({"server_vad": True},):
                client, _socket = self._client(**kwargs)
                # The guard is against a server that owns its boundaries, so give it one.
                client._speech_started_total = 3
                await self._speak(client, barge_in_frames(client) * 2)
                self.assertIsNone(getattr(client, "_muted_response_id", None),
                                  f"double interruption on {kwargs}")
                self.assertFalse(client._interrupted, f"{kwargs} interrupted anyway")

        asyncio.run(scenario())

    def test_the_gemini_route_raises_the_products_own_interrupt_flag(self) -> None:
        """The route the learner is on is `lanlan_app_gemini`; it needs the shipped flag.

        Verified from a live session at 2026-10-12 03:14: that client delivers audio through
        `_gemini_support.py`, whose gate already reads `_interrupted` and whose own turn
        detection clears it - so arming the id-keyed mute here (or returning early, as the
        first three drafts did) silenced nothing. Nothing is sent to the provider either:
        no `response.create`, no `response.cancel`, no arbiter change.
        """
        async def scenario() -> None:
            client, socket = self._client(gemini=True)
            armed = barge_in_frames(client)
            await self._speak(client, armed - 1)
            self.assertFalse(client._interrupted, "interrupted before the sustain window")
            await self._speak(client, 1, start=100.0 + (armed - 1) * 0.032)
            self.assertTrue(client._interrupted,
                            "the free route is the one that needs this and it still played on")
            self.assertEqual([event.get("type") for event in socket.sent], [],
                             "a local stop-playback must not send anything to the provider")
            self.assertTrue(any("interrupting the answer in the speaker" in line
                                 for _, line in self.recorder.lines), self.recorder.text())
            stamp = client._local_onset_armed_at
            await self._speak(client, armed * 2, start=101.0)
            self.assertEqual(client._local_onset_armed_at, stamp,
                             "one utterance re-armed the interruption frame after frame")

        asyncio.run(scenario())

    def test_advertised_server_vad_that_never_delivers_a_boundary_still_arms(self) -> None:
        """The desktop route asks for `turn_detection: server_vad` and gets zero events.

        Measured 2026-10-12 03:45: 300 s, 24 answered turns, `speech_started` count 0. Standing
        aside on `_has_server_vad` was therefore standing aside from the only route the learner
        is on, which is how four sessions produced audio, an interruption, and no onset line.
        """
        async def scenario() -> None:
            client, _socket = self._client(server_vad=True)
            await self._speak(client, barge_in_frames(client) + 1)
            self.assertIsNotNone(getattr(client, "_muted_response_id", None),
                                 "the route that needs it still cannot interrupt itself")

        asyncio.run(scenario())

    def test_the_pc_pipeline_arms_on_denoiser_probability_not_raw_loudness(self) -> None:
        """The desktop mic is 48 kHz and RNNoise scores it; the raw int16 RMS is not the signal.

        Measured 2026-10-12 03:50 live: `[voice-rnnoise] probability_peak=0.9995` and
        `peak_ge_0_5_chunks=194/202` in a two-second window, while an earlier draft of the arming
        watched only `raw_loud` (int16 RMS over `_client_vad_threshold` = 500) and never fired.
        This feeds frames that are quiet enough to fail the RMS test on purpose.
        """
        class Processor:
            noise_reduce_enabled = True
            _denoiser = object()
            speech_probability = 0.9

        async def scenario() -> None:
            client, _socket = self._client(server_vad=True)
            client._audio_processor = Processor()
            quiet_48k = b"\x00\x01" * 480          # RMS 256: below the 500 loudness threshold
            frames = int(client._LOCAL_BARGE_IN_SECONDS / 0.010) + 2
            for index in range(frames):
                await client.stream_audio(quiet_48k, captured_at=700.0 + index * 0.010)
            self.assertIsNotNone(getattr(client, "_muted_response_id", None),
                                 "the RNNoise-scored speech the live route reports cannot interrupt")

        asyncio.run(scenario())

    def test_the_desktop_route_arms_on_the_callers_verdict_when_its_own_rms_sees_nothing(self) -> None:
        """The learner's real microphone: the host has already decided this frame is speech.

        Measured on the learner's own session 2026-10-12 11:35-11:48 - the first session recorded
        through a real microphone instead of a fake device - and the result was **zero** onset
        lines in 18 turns. Not because audio did not arrive: `asr_runtime.py` counts
        `omni_mic_audio_bytes` only after a successful `stream_audio`, and that counter reached
        8,450,820. The frames were here; what failed is that this route hands the client audio the
        host already denoised to 16 kHz, so `is_48khz` is false, RNNoise is not live here, and the
        only remaining signal was an absolute int16 RMS > 500, which a real microphone at desk
        distance does not hold for half a second. So the caller now passes its own verdict, and it
        is quiet on purpose below: this fixture cannot arm on loudness.
        """
        async def scenario() -> None:
            client, _socket = self._client()
            below_gate = b"\x00\x01" * 512          # RMS 256, under the 500 loudness threshold
            frames = barge_in_frames(client)
            await self._speak(client, frames, chunk=below_gate, speech_active=True)
            self.assertIsNotNone(getattr(client, "_muted_response_id", None),
                                 "speech the host itself flagged cannot interrupt the answer")

        asyncio.run(scenario())

    def test_energy_the_host_does_not_call_speech_arms_nothing(self) -> None:
        """Loud without a speech verdict is the echo case, and it must stay unarmed.

        Trading RMS for the caller's probability also trades away the one thing loudness gave us:
        RNNoise does not know whether the sound came from the learner or from the speaker. Keeping
        the caller's `False` authoritative is what stops the character interrupting itself the
        moment the room gets loud.
        """
        async def scenario() -> None:
            client, _socket = self._client()
            frames = barge_in_frames(client)
            await self._speak(client, frames * 2, speech_active=False)
            self.assertIsNone(getattr(client, "_muted_response_id", None),
                              "the teacher's own voice through the microphone silenced it")

        asyncio.run(scenario())

    def test_the_kill_switch_restores_the_shipped_behaviour(self) -> None:
        async def scenario() -> None:
            client, _socket = self._client()
            with mock_patch.dict(os.environ, {"NEKO_LOCAL_BARGE_IN": "0"}):
                await self._speak(client, barge_in_frames(client) * 2)
            self.assertIsNone(getattr(client, "_muted_response_id", None),
                              "the documented off switch does not turn this off")

        asyncio.run(scenario())


class PatchIsTheDeliverableTest(unittest.TestCase):
    def test_the_runtime_tree_carries_the_mute_and_nothing_else_spooky(self) -> None:
        """The wiring is present, and it is the wiring the repo can reproduce."""
        import neko_voice_host_patch as patch

        text = TRANSPORT.read_text(encoding="utf-8")
        for marker in ("_handle_local_speech_onset", "_output_locally_muted",
                       "_note_output_delivery", "_LOCAL_BARGE_IN_SECONDS",
                       "NEKO_LOCAL_BARGE_IN", "_note_barge_in_meter", "speech_active"):
            # assertTrue, not assertIn: the transport is 220 KB and a failure must not dump it.
            self.assertTrue(marker in text, f"{marker} is missing from the runtime transport")
        self.assertIn("and not self._output_locally_muted(event)", text,
                      "the mute is defined but never consulted at the delivery site")
        asr = (HOST / "main_logic" / "core" / "asr_runtime.py").read_text(encoding="utf-8")
        self.assertIn("speech_active = self._voice_session_activation_has_speech(", asr,
                      "the desktop route still asks the client to judge loudness it cannot see")
        self.assertIn("speech_active=speech_active,", asr,
                      "the verdict is computed but never handed to the client")
        self.assertEqual([relative for relative, _ in patch.TARGETS],
                         ["main_logic/omni_realtime_client/_tools.py",
                          "main_logic/omni_realtime_client/_transport.py",
                          "main_logic/omni_realtime_client/_gemini_support.py",
                          "main_logic/core/asr_runtime.py",
                          "main_logic/core/session_lifecycle.py",
                          "main_logic/core/lifecycle.py",
                          "main_logic/core/tts_runtime.py",
                          "main_routers/websocket_router.py",
                          "static/app/app-websocket.js",
                          "static/app/app-audio-playback.js",
                          "main_logic/core/tts_lifecycle.py",
                          "main_logic/core/tool_calling.py",
                          "app/main_server/character_runtime.py",
                          "main_logic/omni_realtime_client/_audio.py",
                          "main_logic/core/turn.py",
                          "main_logic/omni_realtime_client/_wire_trace.py",
                          "main_logic/omni_realtime_client/_response_arbiter.py"])
        # ...and the Gemini gate is the one the free route plays through. Patching only the
        # transport is what left three sessions with zero onset lines while 56 s of answer
        # came out of the speaker.
        gemini = (HOST / "main_logic/omni_realtime_client/_gemini_support.py").read_text(
            encoding="utf-8")
        self.assertTrue("self._count_gemini_local_onset_suppression()" in gemini,
                        "the delivery site the learner's route uses is not instrumented")
        self.assertTrue("if not self._skip_until_next_response and not self._interrupted "
                        "and self.on_audio_delta:" in gemini,
                        "the counting hunk replaced the shipped gate instead of joining it")
        # The local onset must not reach for the cancellation that cannot be reached: that is the
        # mistake the three withdrawn drafts made. Scoped to the onset method itself, because the
        # upstream `speech_started` handler further down the file legitimately still calls it.
        onset = text.split("async def _handle_local_speech_onset")[1]
        onset = onset.split("\n    async def stream_audio")[0]
        self.assertTrue("handle_interruption" not in onset,
                        "the local onset wired itself to the unreachable cancellation again")


if __name__ == "__main__":
    unittest.main(verbosity=2)
