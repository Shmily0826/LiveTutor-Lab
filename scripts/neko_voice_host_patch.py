"""The tool-result-lifecycle host patch, kept in the repo instead of inside a gitignored tree.

N.E.K.O's realtime client lives in `benchmarks/raw/neko-product-host`, which this repository
ignores. A fix applied only there is invisible to review and silently lost on a fresh clone, so
the change lives here as the exact strings it replaces, and is replayed onto the host tree at
deploy time. `--check` is what the offline guard runs: it fails loudly if a vendored N.E.K.O
update moved the code out from under us, rather than shipping an unpatched host quietly.

Site of the change: `main_logic/omni_realtime_client/_tools.py`, the tool-scope retirement path.
Dropping a tool result whose turn was replaced is correct; doing it with no log line is what made
a question that never answered indistinguishable from a tool that failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Both trees must carry it: the runtime one the host imports, and the candidates copy the
# offline fixtures import. They were byte-identical before the patch, and stay so after.
HOSTS = (ROOT / "benchmarks/raw/neko-product-host", ROOT / "candidates/N.E.K.O")
RELATIVE = "main_logic/omni_realtime_client/_tools.py"

HELPERS = '''
    def _stale_fence(self, owner: _ToolTaskOwner) -> str:
        """Which ownership fence the tool tripped on - the reason its result is not sent."""

        if owner.connection_generation != self._connection_generation:
            return "connection_replaced"
        if owner.scope_generation != getattr(self, "_tool_scope_generation", 0):
            return "user_turn_replaced"
        live_session = self._gemini_session if self._is_gemini else self.ws
        if owner.provider_session is not live_session:
            return "provider_session_replaced"
        return "provider_turn_snapshot_mismatch"

    def _log_stale_tool_drop(self, stage: str, owner: _ToolTaskOwner, results, *,
                             batch: "_ToolBatch | None" = None) -> None:
        """Record a tool result that will never reach the provider.

        Dropping a result from a retired turn is correct - it would answer a function call the
        provider already abandoned and land inside somebody else's turn. The defect is the
        silence: without a line saying what was thrown away and why, "the tool was slow", "the
        tool failed" and "the answer was discarded" are indistinguishable from the outside, which
        is how a turn that never replies gets debugged by guessing. Fingerprints, never payloads.
        """

        items = [item for item in (results or []) if item is not None]
        call_ids = [str(getattr(item, "call_id", "") or "") for item in items]
        if not any(call_ids) and batch is not None:
            call_ids = [str(entry.call.call_id or "") for entry in getattr(batch, "entries", ())]
        self._drop_line(stage, self._stale_fence(owner), len(items) or 1, call_ids,
                        owner.scope_generation)

    def _drop_line(self, stage: str, reason: str, count: int, call_ids,
                   previous_scope: int) -> None:
        """One line, same shape, wherever tool work goes away before the learner sees it."""

        logger.warning(
            "realtime tool work dropped stage=%s reason=%s count=%d call_fingerprints=%s "
            "owner_scope=%s current_scope=%s",
            stage,
            reason,
            count,
            ",".join(
                hashlib.sha256(str(call_id).encode("utf-8")).hexdigest()[:12]
                for call_id in call_ids if call_id
            ) or "none",
            previous_scope,
            getattr(self, "_tool_scope_generation", 0),
        )

    def _track_tool_task('''

REPLACEMENTS = (
    ("    def _track_tool_task(", HELPERS),
    ('''        self._seal_tool_batch(batch)
        if not self._tool_task_owner_is_current(owner):
            return []''',
     '''        self._seal_tool_batch(batch)
        if not self._tool_task_owner_is_current(owner):
            self._log_stale_tool_drop("collector", owner, list(collected.values()), batch=batch)
            return []'''),
    ('''        async def _run() -> ToolResult | None:
            if not self._tool_task_owner_is_current(owner):
                return None''',
     '''        async def _run() -> ToolResult | None:
            if not self._tool_task_owner_is_current(owner):
                self._log_stale_tool_drop("not_started", owner, [call])
                return None'''),
    ('''        async def _execute(call: ToolCall) -> ToolResult | None:
            if not self._tool_task_owner_is_current(owner):
                return None''',
     '''        async def _execute(call: ToolCall) -> ToolResult | None:
            if not self._tool_task_owner_is_current(owner):
                self._log_stale_tool_drop("not_started", owner, [call])
                return None'''),
    ('''        if owner is not None and not self._tool_task_owner_is_current(owner):
            return

        api = canonical_realtime_dialect(self._api_type)''',
     '''        if owner is not None and not self._tool_task_owner_is_current(owner):
            self._log_stale_tool_drop("send", owner, results)
            return

        api = canonical_realtime_dialect(self._api_type)'''),
    ('''            if owner is not None and not self._tool_task_owner_is_current(owner):
                await arbiter.cancel_ticket(ticket, wait=False)
                return''',
     '''            if owner is not None and not self._tool_task_owner_is_current(owner):
                self._log_stale_tool_drop("queued", owner, results)
                await arbiter.cancel_ticket(ticket, wait=False)
                return'''),
    ('''            await asyncio.shield(ticket.sent)
            if owner is not None and not self._tool_task_owner_is_current(owner):
                await arbiter.cancel_ticket(ticket, wait=False)''',
     '''            await asyncio.shield(ticket.sent)
            if owner is not None and not self._tool_task_owner_is_current(owner):
                # The batch went out, then the turn was replaced while it was in flight: the
                # continuation is cancelled, so say that rather than let it look unsent.
                self._log_stale_tool_drop("sent_then_retired", owner, results)
                await arbiter.cancel_ticket(ticket, wait=False)'''),
    ('''        current_task = asyncio.current_task()
        tasks = tuple(getattr(self, "_tool_tasks", ()))
        retired = self._retired_tool_task_registry()
        for task in tasks:
            if not task.done():
                task.cancel()
                # Marked HERE. The cancelled-id set is cleared one line up, so
                # a handler that ignores cancellation would otherwise carry no
                # retirement marker at all and read as live forever.
                retired.add(task)
        return tuple(task for task in tasks if task is not current_task)''',
     '''        current_task = asyncio.current_task()
        tasks = tuple(getattr(self, "_tool_tasks", ()))
        retired = self._retired_tool_task_registry()
        cancelled = [task for task in tasks if not task.done()]
        for task in cancelled:
            task.cancel()
            # Marked HERE. The cancelled-id set is cleared one line up, so
            # a handler that ignores cancellation would otherwise carry no
            # retirement marker at all and read as live forever.
            retired.add(task)
        if cancelled:
            # This is where an in-flight tool actually dies - the result sites below only see
            # what survived long enough to be judged stale. Without this line a question that
            # was interrupted mid-tool looks identical to one whose tool failed.
            live = set(cancelled)
            call_ids = sorted(str(call_id) for call_id, task_set
                              in getattr(self, "_tool_tasks_by_call_id", {}).items()
                              if any(task in live for task in task_set))
            self._drop_line("scope_retired", "user_turn_replaced", len(cancelled), call_ids,
                            self._tool_scope_generation - 1)
        return tuple(task for task in tasks if task is not current_task)'''),
    # ----------------------------------------------------------------------
    # The turn that never came back (2026-10-11, free realtime route).
    # Four of the learner's utterances in a row produced
    # `reason=provider_turn_snapshot_mismatch owner_scope=12 current_scope=12`
    # and the recording holds eleven straight minutes of silence after it.
    # The pair this owner sampled at capture disagreed because the response
    # carrying the call was never announced to us - the proxy opens one per
    # transcript fragment and does not echo `response.created`. A pair that
    # belongs to a different response is not evidence that THIS call was
    # retired, and answering it with nothing is what wedged the session.
    # ----------------------------------------------------------------------
    ('''@dataclass(frozen=True)
class _ToolTaskOwner:
    connection_generation: int
    scope_generation: int
    host_turn_id: str | None
    provider_turn_host_id: str | None
    provider_session: Any''',
     '''@dataclass(frozen=True)
class _ToolTaskOwner:
    connection_generation: int
    scope_generation: int
    host_turn_id: str | None
    provider_turn_host_id: str | None
    provider_session: Any
    # Whether the (host_turn_id, provider_turn_host_id) pair below describes the
    # response that actually emitted this call. False when that response was never
    # announced to us: the snapshot then belongs to some other response, and an
    # unverifiable pair is not the same thing as a retired turn.
    turn_pair_fence_applies: bool = True'''),
    ('''        return (
            owner.provider_turn_host_id is None
            or owner.provider_turn_host_id == owner.host_turn_id
        )''',
     '''        if not owner.turn_pair_fence_applies:
            # The other three fences are enforced above and still apply in full:
            # same connection, same tool scope, same provider session.
            return True
        return (
            owner.provider_turn_host_id is None
            or owner.provider_turn_host_id == owner.host_turn_id
        )'''),
    ('''        async def _run() -> ToolResult | None:
            if not self._tool_task_owner_is_current(owner):
                self._log_stale_tool_drop("not_started", owner, [call])
                return None
            return await self._execute_tool_call(call)''',
     '''        if response_id is not None and response_id != self._current_response_id:
            owner = _ToolTaskOwner(
                owner.connection_generation,
                owner.scope_generation,
                owner.host_turn_id,
                owner.provider_turn_host_id,
                owner.provider_session,
                turn_pair_fence_applies=False,
            )
            logger.info(
                "realtime tool call arrived on an unannounced response; turn-pair fence off "
                "reason=%s call_fingerprints=%s response_id=%s last_observed_response=%s",
                self._stale_fence(owner),
                hashlib.sha256(str(call.call_id).encode("utf-8")).hexdigest()[:12],
                response_id,
                self._current_response_id,
            )

        async def _run() -> ToolResult | None:
            if not self._tool_task_owner_is_current(owner):
                self._log_stale_tool_drop("not_started", owner, [call])
                return None
            return await self._execute_tool_call(call)'''),
    ('''        results = await self._collect_tool_batch(batch, owner)
        if results:
            await self._send_tool_results_openai_realtime(results, owner=owner)''',
     '''        results = await self._collect_tool_batch(batch, owner)
        if results:
            await self._send_tool_results_openai_realtime(results, owner=owner)
            return
        await self._close_unanswered_tool_calls(batch, owner)

    async def _close_unanswered_tool_calls(
        self,
        batch: _ToolBatch,
        owner: _ToolTaskOwner,
    ) -> None:
        """Release the calls this client will not answer, without answering them.

        Withholding a retired turn's payload is right. Leaving its function call
        OPEN is not: the provider holds the response lane waiting for a
        ``function_call_output`` for every id it emitted, and on a proxy that
        auto-opens a response per fragment nothing ever releases it - that is how
        one discarded result became a character that would not answer for the rest
        of the session. This sends the protocol's own "do not wait for this"
        payload (the same one the retirement path already uses) and deliberately
        requests NO continuation, so it cannot speak into a turn that is not its
        own. Connection and session fences still gate it; a dead connection has
        nobody to release.
        """

        if not self._tool_task_connection_is_current(owner):
            return
        live_session = self._gemini_session if self._is_gemini else self.ws
        if owner.provider_session is not live_session:
            return
        api = canonical_realtime_dialect(self._api_type)
        closed = []
        for entry in batch.entries:
            call_id = str(entry.call.call_id or "")
            if not call_id or self._tool_call_was_cancelled(owner, call_id):
                continue
            item = {
                "type": "function_call_output",
                "output": ToolResult(
                    call_id=call_id,
                    name=entry.call.name,
                    output={"abandoned": True, "error": _ABANDONED_TOOL_CALL_REASON},
                    is_error=True,
                    error_message=_ABANDONED_TOOL_CALL_REASON,
                ).output_as_json_string(),
            }
            if api != "glm" and call_id:
                item["call_id"] = call_id
            await self.send_event(
                {"type": "conversation.item.create", "item": item},
                send_guard=lambda: self._tool_task_connection_is_current(owner),
            )
            closed.append(call_id)
        if closed:
            logger.warning(
                "realtime tool calls released without a result count=%d call_fingerprints=%s",
                len(closed),
                ",".join(hashlib.sha256(call_id.encode("utf-8")).hexdigest()[:12]
                         for call_id in closed),
            )'''),
)


TRANSPORT_RELATIVE = "main_logic/omni_realtime_client/_transport.py"

# What this hunk set does, and what it deliberately does not do.
#
# `handle_interruption` cannot be reached on the free route (see
# `docs/LIVETUTOR_NIGHTLY_DELIVERY.md`): it returns unless `_is_responding`, which only a
# `response.created` or an owned-content start can set, and the proxy sends neither. Three drafts
# that called it were inert and were withdrawn.
#
# Stopping the *playback* is a different question from cancelling the *response*, and it does not
# need the provider: the host already gates every outgoing delta behind
# `not self._skip_until_next_response and not self._interrupted`. These hunks add a second, local
# gate next to it - armed by the host's own sustained-speech transition, keyed to the response id
# currently being spoken, and self-releasing. Nothing is scheduled, no playback state machine is
# introduced, and no response-lifecycle semantics are redefined.
#
# The two properties that make it safe to leave on overnight:
# - it needs an anchor. If the route ever stops tagging deltas with a `response_id`, the mute is
#   never armed and the log says so, rather than silencing an answer we cannot identify;
# - it expires. `_LOCAL_MUTE_MAX_SECONDS` releases the mute even if no new response id arrives,
#   because a wedge is the failure this project already paid for once.
TRANSPORT_REPLACEMENTS = (
    ('''    async def stream_audio(''',
     '''    # How long the learner has to talk before it counts as an interruption. Same
    # 0.5 s the RNNoise branch already means by `_speech_sustain_threshold`; measured on the
    # audio timeline rather than by frame count because the uplink chunk period here is ~10 ms.
    _LOCAL_BARGE_IN_SECONDS = 0.5
    # A short run counts as talking even though it is not unbroken. Measured 2026-10-12 by
    # replaying a real recorded question through the host's own
    # `utils.audio_processor.AudioProcessor` (`scripts/neko_speech_signal_probe.py`): 27% of
    # the 48 kHz frames clear the int16 RMS gate, but the longest run with no dip at all is
    # 0.08 s raw / 0.07 s denoised (a second pass over the same file put the raw figure at
    # 0.45 s - either way, far short of half a second). Natural speech breathes, so an
    # unbroken window is a threshold no learner meets. 0.15 s is the smallest tolerance in
    # that table whose spans reach 0.5 s on both columns (0.65 s raw, 0.57 s denoised), and
    # the 0.5 s span requirement still has to be satisfied inside it.
    _LOCAL_BARGE_IN_GAP_SECONDS = 0.15
    # How long the answer stays suppressed when no new response id ever shows up. The mute must
    # expire, because a wedge is the failure this project already paid for once.
    _LOCAL_MUTE_MAX_SECONDS = 12.0
    # `_ai_recent_activity_time` is written at the delivery site, so it is the only
    # "something is being spoken right now" signal that survives a route that never announces a
    # response. Outside this window there is nothing to interrupt.
    _LOCAL_TALKING_WINDOW_SECONDS = 2.0

    def _note_output_delivery(self, event: dict) -> None:
        """Track which response the spoken output belongs to; release a mute that it overran."""

        response_id = event.get("response_id")
        if not isinstance(response_id, str) or not response_id:
            return
        muted = getattr(self, "_muted_response_id", None)
        if muted == response_id:
            return
        if muted is not None:
            logger.info(
                "local playback mute released on a new response: released=%s incoming=%s "
                "suppressed_events=%d",
                muted, response_id, getattr(self, "_local_mute_suppressed", 0),
            )
            self._muted_response_id = None
        self._last_delivered_response_id = response_id

    def _output_locally_muted(self, event: dict) -> bool:
        """True while the learner is talking over the response this event belongs to."""

        muted = getattr(self, "_muted_response_id", None)
        if muted is None:
            return False
        import time as _time

        if _time.monotonic() - self._muted_at > self._LOCAL_MUTE_MAX_SECONDS:
            logger.warning(
                "local playback mute expired without a new response: response=%s "
                "suppressed_events=%d - the route gave no id boundary, delivering again",
                muted, getattr(self, "_local_mute_suppressed", 0),
            )
            self._muted_response_id = None
            return False
        response_id = event.get("response_id")
        if isinstance(response_id, str) and response_id != muted:
            return False
        self._local_mute_suppressed = getattr(self, "_local_mute_suppressed", 0) + 1
        return True

    def _count_gemini_local_onset_suppression(self) -> None:
        """Count the output frames the local onset stopped on the Gemini-shaped route.

        Counting only - the shipped gate does the suppressing, so a frame attributed to us while
        the provider had interrupted itself inflates a log number and changes no behaviour.
        """
        import time
        armed = getattr(self, "_local_onset_armed_at", 0.0)
        if armed and time.time() - armed < 30.0:
            self._local_mute_suppressed = getattr(self, "_local_mute_suppressed", 0) + 1

    def _note_barge_in_meter(self, speaking: bool, loud: bool, raw_samples,
                             audio_timeline_at: float) -> None:
        """Two seconds of what the local onset gate was actually fed, then say it out loud.

        Seven sessions were needed to find the last cause and every one of them was blind:
        a missing `local speech onset` line cannot tell "nobody spoke" from "spoke, and the
        signal I read never rose". This reports both signals side by side - what the caller's
        verdict saw, and what the int16 gate saw - in the shape the host already uses for its
        own `[voice-rnnoise]` line, so the next session can be read instead of re-litigated.
        """
        bucket = getattr(self, "_barge_in_bucket", None)
        if bucket is None or audio_timeline_at - bucket["from"] >= 2.0:
            if bucket is not None and bucket["frames"]:
                values = sorted(bucket["rms"])
                # Same units as `_client_vad_threshold` (raw int16 amplitude): the first version
                # of this line scaled an already-raw RMS by 32767 again and printed numbers over
                # the int16 ceiling, which made the live session unreadable.
                logger.info(
                    "[barge-in-meter] from=%.1f frames=%d speaking=%d raw_loud=%d "
                    "rms_p50=%.0f rms_p90=%.0f rms_max=%.0f gate=%d",
                    bucket["from"], bucket["frames"], bucket["speaking"], bucket["loud"],
                    values[len(values) // 2],
                    values[min(len(values) - 1, int(len(values) * 0.9))],
                    values[-1], getattr(self, "_client_vad_threshold", 0),
                )
            bucket = {"from": audio_timeline_at, "frames": 0, "speaking": 0, "loud": 0, "rms": []}
            self._barge_in_bucket = bucket
        level = float(np.sqrt(np.mean(raw_samples.astype(np.float32) ** 2))) if len(raw_samples) else 0.0
        bucket["frames"] += 1
        bucket["speaking"] += int(bool(speaking))
        bucket["loud"] += int(bool(loud))
        bucket["rms"].append(level)

    def _note_local_onset_declined(self, reason: str) -> None:
        """Say why a completed speech streak did not mute, at most once every 20 s.

        Four live sessions produced zero onset lines and no way to tell "never armed" from
        "armed, but nothing was playing". The decline is the only case that is invisible
        otherwise, so it gets one rate-limited line instead of silence.
        """
        import time
        now = time.time()
        if now - getattr(self, "_local_onset_declined_logged_at", 0.0) < 20.0:
            return
        self._local_onset_declined_logged_at = now
        logger.info("local speech onset declined: %s", reason)

    async def _handle_local_speech_onset(self, evidence: str) -> None:
        """Stop the current answer from being spoken, without asking the provider to cancel it.

        Narrow on purpose: `_LOCAL_BARGE_IN_SECONDS` of talking, where a gap longer than
        `_LOCAL_BARGE_IN_GAP_SECONDS` restarts the clock (real speech breathes, measured: 0.45 s
        is the longest unbroken loud run a spoken sentence produces), never on a route whose
        server VAD already interrupts, never when nothing has
        been audible in the last `_LOCAL_TALKING_WINDOW_SECONDS`. NEKO_LOCAL_BARGE_IN=0 restores
        shipped behaviour without touching this file; whether the speaker's own echo can trip it
        is a listening test, not something an offline run can answer.

        Two shapes, because the route the learner is actually on is not the one the id-keyed mute
        was written for. Measured 2026-10-12 03:14 on a live session: `route=lanlan_app_gemini`,
        audio delivered through `_gemini_support.py`, zero onset lines - the Gemini client never
        reaches the `_transport.py` gate, and this handler used to return on `_is_gemini`. On that
        route the shipped code already honours `_interrupted` at the delivery site and clears it
        itself once the AI has been quiet for `_ai_recent_activity_window`, so the local onset
        raises the product's own flag and lets its own turn detection release it. The id-bearing
        route keeps the response-keyed mute, because there `_interrupted` is only cleared by a
        `response.created` this proxy never sends.
        """
        import os
        import time

        if os.environ.get("NEKO_LOCAL_BARGE_IN", "1").strip() == "0":
            return
        if self._has_server_vad and getattr(self, "_speech_started_total", 0):
            # A server that does announce its own boundaries owns the interruption; standing
            # aside is what keeps this from being a second, competing arbiter. Advertising
            # server VAD and never sending one event is the case that has to be armed here.
            self._note_local_onset_declined("server VAD owns the boundaries")
            return
        now = time.time()
        if now - getattr(self, "_ai_recent_activity_time", 0.0) > self._LOCAL_TALKING_WINDOW_SECONDS:
            self._note_local_onset_declined(
                "nothing audible for %.1fs" % (now - getattr(self, "_ai_recent_activity_time", 0.0)))
            return
        if self._is_gemini:
            if self._interrupted:
                return
            self._local_onset_armed_at = now
            self._local_mute_suppressed = 0
            self._interrupted = True
            logger.info(
                "local speech onset (%s): interrupting the answer in the speaker "
                "route=gemini ai_last_spoke=%.2fs ago - released by the product's own new-turn "
                "detection", evidence, now - getattr(self, "_ai_recent_activity_time", 0.0),
            )
            return
        anchor = getattr(self, "_last_delivered_response_id", None)
        if anchor is None:
            logger.info(
                "local speech onset (%s) with no response anchor: not muting - the route is "
                "not identifying which answer this output belongs to", evidence,
            )
            return
        if getattr(self, "_muted_response_id", None) == anchor:
            return
        self._muted_response_id = anchor
        self._muted_at = time.monotonic()
        self._local_mute_suppressed = 0
        logger.info(
            "local speech onset (%s): suppressing the rest of response=%s deltas_delivered=%d "
            "ai_last_spoke=%.2fs ago",
            evidence, anchor, getattr(self, "_audio_delta_count", 0),
            now - getattr(self, "_ai_recent_activity_time", 0.0),
        )

    async def stream_audio('''),
    # The 48 kHz branch, for a client that runs its own denoiser.
    ('''                        elif (
                            audio_timeline_at - self._speech_detect_start
                            >= self._speech_sustain_threshold
                        ):
                            self._client_vad_last_speech_time = audio_timeline_at
                            self._client_vad_active = True''',
     '''                        elif (
                            audio_timeline_at - self._speech_detect_start
                            >= self._speech_sustain_threshold
                        ):
                            sustained_onset = not self._client_vad_active
                            self._client_vad_last_speech_time = audio_timeline_at
                            self._client_vad_active = True
                            if sustained_onset:
                                await self._handle_local_speech_onset("rnnoise-sustain")'''),
    # The desktop route runs with `turn_detection: "server_vad"` - the host's own
    # `session.update` sends it, so `_has_server_vad` is True and the shipped "react to local
    # speech" block above is skipped entirely. Measured 2026-10-12 03:45, 300 s, 24 answered
    # turns, `speech_started` count 0: nothing on that route can interrupt today. So the local
    # onset goes where both shapes reach it - beside the silence handling - and only while the
    # server has not delivered one boundary event, so a route that does own its boundaries keeps
    # owning them. The frame count also became a duration, because these uplink chunks are ~10 ms
    # apart and 16 of them is 160 ms, which no-one would call a sentence.
    ('''                elif raw_loud:
                    self._client_vad_last_speech_time = audio_timeline_at
                    self._client_vad_active = True

            # 静音清 buffer：有 RNNoise 以 RNNoise 为准，否则 VAD + 连续本地静音。''',
     '''                elif raw_loud:
                    self._client_vad_last_speech_time = audio_timeline_at
                    self._client_vad_active = True

            if not getattr(self, "_speech_started_total", 0):
                # Whichever sustained-speech signal this frame actually carries. There are two
                # input routes and they are not interchangeable: the browser-shaped 48 kHz path
                # lets this client run its own denoiser, while the desktop path hands
                # `stream_audio` frames the host already scored and denoised to 16 kHz. Measured
                # on the real microphone (learner session 2026-10-12 11:35-11:48, 18 turns): the
                # int16 RMS>500 gate held for half a second **zero** times, while the host's own
                # RNNoise reported `probability_peak=0.9998, peak_ge_0_5_chunks=138/200` for the
                # same speech - and 8.45 MB of that microphone PCM demonstrably reached
                # `stream_audio` (`asr_runtime.py` counts it only after a successful send), so
                # the frames were here and the signal I was reading was the wrong one. The
                # caller's verdict is therefore the primary evidence; it is produced by the
                # host's own `_voice_session_activation_has_speech`, not by a threshold added
                # here. `None` means this route has no verdict, which is the 48 kHz case.
                _speaking_now = (
                    speech_active
                    if speech_active is not None else
                    ((audio_processor.speech_probability > 0.4)
                     if _rnnoise_vad_live else raw_loud)
                )
                self._note_barge_in_meter(_speaking_now, raw_loud, raw_samples,
                                          audio_timeline_at)
                if _speaking_now:
                    _loud_since = getattr(self, "_local_barge_in_loud_at", 0.0)
                    if (getattr(self, "_local_barge_in_from", None) is None
                            or audio_timeline_at - _loud_since > self._LOCAL_BARGE_IN_GAP_SECONDS):
                        self._local_barge_in_from = audio_timeline_at
                    self._local_barge_in_loud_at = audio_timeline_at
                    if (audio_timeline_at - self._local_barge_in_from
                            >= self._LOCAL_BARGE_IN_SECONDS):
                        self._local_barge_in_from = None
                        await self._handle_local_speech_onset("speech-sustained")
                elif (audio_timeline_at - getattr(self, "_local_barge_in_loud_at", 0.0)
                      > self._LOCAL_BARGE_IN_GAP_SECONDS):
                    self._local_barge_in_from = None

            # 静音清 buffer：有 RNNoise 以 RNNoise 为准，否则 VAD + 连续本地静音。'''),
    # The desktop path's verdict has to arrive somewhere, and a keyword-only argument with a
    # `None` default leaves every other caller (and the 48 kHz route) exactly as shipped.
    ('''    async def stream_audio(
        self,
        audio_chunk: bytes,
        *,
        captured_at: float | None = None,
        raise_on_error: bool = False,
        require_output_commit: bool = False,
    ) -> bool | None:''',
     '''    async def stream_audio(
        self,
        audio_chunk: bytes,
        *,
        captured_at: float | None = None,
        speech_active: bool | None = None,
        raise_on_error: bool = False,
        require_output_commit: bool = False,
    ) -> bool | None:'''),
    # The gate itself: the local mute sits beside the host's existing two flags, and the
    # bookkeeping call in front of it is what lets the mute release on the next response.
    ('''                if not self._skip_until_next_response and not self._interrupted:''',
     '''                self._note_output_delivery(event)
                if (not self._skip_until_next_response and not self._interrupted
                        and not self._output_locally_muted(event)):'''),
)

GEMINI_RELATIVE = "main_logic/omni_realtime_client/_gemini_support.py"

# The delivery site the free route actually uses (`route=lanlan_app_gemini`, measured live).
# Purely additive: the shipped condition still decides what plays, this only counts the frames
# the local onset suppressed so the report can say how much of the answer the learner did not
# hear. Suppressing itself comes from setting `_interrupted`, which this gate already honours.
GEMINI_REPLACEMENTS = (
    ('''                        if hasattr(part, 'inline_data') and part.inline_data:
                            if isinstance(part.inline_data.data, bytes):
                                if not self._skip_until_next_response and not self._interrupted and self.on_audio_delta:''',
     '''                        if hasattr(part, 'inline_data') and part.inline_data:
                            if isinstance(part.inline_data.data, bytes):
                                if self._interrupted and self.on_audio_delta:
                                    self._count_gemini_local_onset_suppression()
                                if not self._skip_until_next_response and not self._interrupted and self.on_audio_delta:'''),
)

ASR_RELATIVE = "main_logic/core/asr_runtime.py"

# The learner's own microphone is the desktop route: `voice_turn` has already run RNNoise and
# resampled to 16 kHz by the time a frame reaches the realtime client, so the client cannot
# judge the speech itself - but the host has already judged it, two lines above this send, for
# the purpose of opening a turn. Passing that verdict is what makes the local barge-in gate
# read the same signal the product reads, instead of a second threshold nobody tuned.
ASR_REPLACEMENTS = (
    ('''                    if require_output_commit:
                        written = await stream_audio(
                            pcm16,
                            captured_at=captured_at,
                            raise_on_error=True,
                            require_output_commit=True,
                        )
                    else:
                        await stream_audio(
                            pcm16,
                            captured_at=captured_at,
                        )
                        written = None''',
     '''                    speech_active = self._voice_session_activation_has_speech(
                        pcm16,
                        speech_probability=speech_probability,
                        rnnoise_available=rnnoise_available,
                        rnnoise_evidence=rnnoise_evidence,
                    )
                    if require_output_commit:
                        written = await stream_audio(
                            pcm16,
                            captured_at=captured_at,
                            speech_active=speech_active,
                            raise_on_error=True,
                            require_output_commit=True,
                        )
                    else:
                        await stream_audio(
                            pcm16,
                            captured_at=captured_at,
                            speech_active=speech_active,
                        )
                        written = None'''),
)

TARGETS = (
    (RELATIVE, REPLACEMENTS),
    (TRANSPORT_RELATIVE, TRANSPORT_REPLACEMENTS),
    (GEMINI_RELATIVE, GEMINI_REPLACEMENTS),
    (ASR_RELATIVE, ASR_REPLACEMENTS),
)

# Passive correlation only. A host speech ID can survive a new user transcript
# until response.done rotates it, so it is not yet a safe queued-audio stop key.
_OWNER_TRACE_UPGRADES = {
    TRANSPORT_RELATIVE: (
        ("    async def _handle_local_speech_onset(self, evidence: str) -> None:",
         '''    def _trace_local_playback_owner(self) -> None:
        import time
        now = time.monotonic()
        if now - getattr(self, "_local_owner_trace_at", 0.0) < 2.0:
            return
        self._local_owner_trace_at = now
        owner = getattr(self, "_local_audio_dispatch_owner", (None, None, None))
        logger.info(
            "[barge-in-owner] connection=%s dispatch_connection=%s "
            "dispatch_speech=%s current_speech=%s dispatch_response=%s mute_anchor=%s",
            self._connection_generation, owner[0], owner[1], self._read_host_turn_id(),
            owner[2], getattr(self, "_last_delivered_response_id", None),
        )

    async def _handle_local_speech_onset(self, evidence: str) -> None:'''),
        ('''            self._note_local_onset_declined("server VAD owns the boundaries")
            return
        now = time.time()''',
         '''            self._note_local_onset_declined("server VAD owns the boundaries")
            return
        self._trace_local_playback_owner()
        now = time.time()'''),
        ('''                            await self.on_audio_delta(audio_bytes)
                            if await retire_if_replaced():''',
         '''                            # Dispatch intent, not a frontend playback receipt.
                            self._local_audio_dispatch_owner = (
                                self._connection_generation, self._read_host_turn_id(),
                                event.get("response_id"),
                            )
                            await self.on_audio_delta(audio_bytes)
                            if await retire_if_replaced():'''),
    ),
    GEMINI_RELATIVE: (
        ('''                                    await self.on_audio_delta(part.inline_data.data)
                                    if not event_owner_is_current():''',
         '''                                    # Dispatch intent, not a frontend playback receipt.
                                    self._local_audio_dispatch_owner = (
                                        self._connection_generation, self._read_host_turn_id(),
                                        getattr(self, "_current_turn_epoch", None),
                                    )
                                    await self.on_audio_delta(part.inline_data.data)
                                    if not event_owner_is_current():'''),
    ),
}


def _owner_trace_targets(targets):
    updated, replay = [], []
    for relative, replacements in targets:
        upgrades = _OWNER_TRACE_UPGRADES.get(relative, ())
        covered, hunks = set(), []
        for old, prior in replacements:
            new = prior
            for index, (before, after) in enumerate(upgrades):
                if before in new:
                    new = new.replace(before, after)
                    covered.add(index)
            hunks.append((old, new))
            if prior != new:
                replay.append((relative, prior, new))
        extra = [pair for index, pair in enumerate(upgrades) if index not in covered]
        hunks.extend(extra)
        replay.extend((relative, old, new) for old, new in extra)
        updated.append((relative, tuple(hunks)))
    return tuple(updated), tuple(replay)


TARGETS, _OWNER_TRACE_REPLAY = _owner_trace_targets(TARGETS)

from neko_native_barge_in_patch import upgrade_targets as _native_barge_in_targets
from neko_native_barge_in_patch import normalize_playback_feedback

TARGETS, _NATIVE_BARGE_IN_REPLAY = _native_barge_in_targets(TARGETS)
_OWNER_TRACE_REPLAY += _NATIVE_BARGE_IN_REPLAY

from neko_late_asr_tool_patch import upgrade_targets as _late_asr_tool_targets
from neko_late_asr_tool_patch import normalize_ordering_helpers
TARGETS, _LATE_ASR_TOOL_REPLAY = _late_asr_tool_targets(TARGETS)
_OWNER_TRACE_REPLAY += _LATE_ASR_TOOL_REPLAY

from neko_study_singleflight_patch import upgrade_targets as _study_singleflight_targets
TARGETS, _STUDY_SINGLEFLIGHT_REPLAY = _study_singleflight_targets(TARGETS)
_OWNER_TRACE_REPLAY += _STUDY_SINGLEFLIGHT_REPLAY

from neko_material_audio_patch import upgrade_targets as _material_audio_targets
from neko_material_audio_patch import normalize_material_audio
TARGETS, _MATERIAL_AUDIO_REPLAY = _material_audio_targets(TARGETS)
_OWNER_TRACE_REPLAY += _MATERIAL_AUDIO_REPLAY

from neko_phrase_input_patch import upgrade_targets as _phrase_input_targets
from neko_phrase_input_patch import normalize_phrase_helpers, normalize_phrase_transport
TARGETS, _PHRASE_INPUT_REPLAY = _phrase_input_targets(TARGETS)
_OWNER_TRACE_REPLAY += _PHRASE_INPUT_REPLAY

from neko_native_grade_patch import upgrade_targets as _native_grade_targets
TARGETS, _NATIVE_GRADE_REPLAY = _native_grade_targets(TARGETS)
_OWNER_TRACE_REPLAY += _NATIVE_GRADE_REPLAY

# The route remains opt-in; single-slot native tools must share their input lane.
from neko_native_tool_join_patch import upgrade_targets as _native_tool_join_targets
from neko_native_tool_join_patch import normalize_ordering_helpers
TARGETS, _OWNER_TRACE_REPLAY = _native_tool_join_targets(TARGETS, _OWNER_TRACE_REPLAY)
_NATIVE_TOOL_JOIN_PATCHED = True


def hunks_for(path: Path):
    """The replacement list that belongs to this file."""

    for relative, replacements in TARGETS:
        if path.as_posix().endswith(relative):
            return replacements
    raise KeyError(f"no patch target for {path}")


def state(path: Path) -> str:
    """`patched` / `pristine` / `partial` - partial means a vendored update moved the code."""
    if not path.is_file():
        return "missing"
    text = path.read_text(encoding="utf-8")
    if path.as_posix().endswith("main_logic/core/session_lifecycle.py") and normalize_phrase_helpers(text) != text:
        return "partial(reviewed-phrase-authority-helper)"
    if path.as_posix().endswith("main_logic/omni_realtime_client/_transport.py") and normalize_phrase_transport(text) != text:
        return "partial(reviewed-phrase-transport-draft)"
    if path.as_posix().endswith("main_logic/omni_realtime_client/_tools.py") and normalize_ordering_helpers(text) != text:
        return "partial(reviewed-ordering-helper)"
    if path.as_posix().endswith("main_logic/core/tool_calling.py") and normalize_material_audio(text) != text:
        return "partial(reviewed-material-helper)"
    if path.as_posix().endswith("static/app/app-audio-playback.js") and normalize_playback_feedback(text) != text:
        return "partial(duplicate-playback-feedback)"
    replacements = hunks_for(path)
    hits = sum(1 for old, new in replacements if new in text)
    if hits == len(replacements):
        return "patched"
    if hits == 0 and any(old in text for old, _ in replacements if old.strip()):
        return "pristine"
    return f"partial({hits}/{len(replacements)})"


def apply_to(path: Path) -> str:
    current = state(path)
    if current == "patched":
        return "already patched"
    text = path.read_text(encoding="utf-8")
    if path.as_posix().endswith("main_logic/core/session_lifecycle.py"):
        text = normalize_phrase_helpers(text)
    if path.as_posix().endswith("main_logic/omni_realtime_client/_transport.py"):
        text = normalize_phrase_transport(text)
    if path.as_posix().endswith("static/app/app-audio-playback.js"):
        text = normalize_playback_feedback(text)
    if path.as_posix().endswith("main_logic/core/tool_calling.py"):
        text = normalize_material_audio(text)
    if path.as_posix().endswith("main_logic/omni_realtime_client/_tools.py"):
        text = normalize_ordering_helpers(text)
    # A reviewed normalizer can already produce the complete canonical source.
    # Replaying older overlapping hunks after that would insert helpers twice.
    if all(new in text for _, new in hunks_for(path)):
        path.write_text(text, encoding="utf-8", newline="\n")
        return "patched"
    for relative, old, new in _OWNER_TRACE_REPLAY:
        if path.as_posix().endswith(relative) and new not in text and text.count(old) == 1:
            text = text.replace(old, new)
    for old, new in hunks_for(path):
        if new in text:
            continue
        if text.count(old) != 1:
            raise RuntimeError(f"{path.name}: expected exactly one place for {old[:52]!r}, "
                               f"found {text.count(old)} - the vendored code has moved")
        text = text.replace(old, new)
    # A later migration can activate an older overlapping replay hunk.
    if path.as_posix().endswith("main_logic/omni_realtime_client/_transport.py"):
        text = normalize_phrase_transport(text)
    if path.as_posix().endswith("main_logic/core/tool_calling.py"):
        text = normalize_material_audio(text)
    path.write_text(text, encoding="utf-8", newline="\n")
    return "patched"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report without writing")
    args = parser.parse_args()
    report = {}
    failed = False
    for host in HOSTS:
        for relative, _ in TARGETS:
            path = host / relative
            if args.check:
                report[path.relative_to(ROOT).as_posix()] = state(path)
                failed = failed or state(path) != "patched"
            else:
                report[path.relative_to(ROOT).as_posix()] = apply_to(path)
    print(json.dumps(report, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
