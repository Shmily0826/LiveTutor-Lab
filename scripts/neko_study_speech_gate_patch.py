"""Opt-in bounded Study tool admission on the observed free voice route.

This gates execution, not speech onset/cancellation or provider endpointing.
The original connection/scope owns each queued call; a later ASR cannot adopt it.
"""

START = '''    _STUDY_SPEECH_QUIET_SECONDS = 1.2
    _STUDY_SPEECH_GATE_SECONDS = 20.0
    _STUDY_ASR_NEIGHBOR_SECONDS = 0.2
    _STUDY_LATE_ORDERING_QUIET_SECONDS = 8.0
    _STUDY_LATE_ORDERING_ASR_SECONDS = 0.4

    def _start_raw_tool_call(self, call, owner, *, response_id=None):
        route = getattr(getattr(self, "_realtime_protocol_capabilities", None), "route_key", None)
        now = time.time()
        loud_at = getattr(self, "_last_local_loud_time", 0.0)
        transcript_at = getattr(self, "_late_raw_transcript_at", 0.0)
        if (route == "lanlan_app_gemini" and getattr(self, "_is_free_proxy", False)
                and not getattr(self, "_has_server_vad", False)
                and str(call.name).startswith("study_")
                and (getattr(self, "_native_barge_in_pending", False) or getattr(self, "_fatal_error_occurred", False))):
            async def release_retiring_call():
                logger.info("study voice admission abandoned name=%s reason=arrived_during_handoff scope=%s", call.name, owner.scope_generation)
                batch = _ToolBatch(closed=True)
                batch.entries.append(_ToolBatchEntry(call, owner, asyncio.current_task(), abandoned=True))
                await self._close_unanswered_tool_calls(batch, owner)
            return asyncio.create_task(release_retiring_call())
        voice_route = (route == "lanlan_app_gemini" and getattr(self, "_is_free_proxy", False)
                       and not getattr(self, "_has_server_vad", False)
                       and not getattr(self, "_native_barge_in_pending", False))
        ordered = voice_route and loud_at > transcript_at and 0 <= now - loud_at <= 2.0
        # Observed first quiz: call 2.117s after speech, ASR 225ms later.
        # There is no stable proxy utterance ID, so this compatibility wait is
        # only for the first transcript of this connection, not later prefixes.
        # Fence both sides of the legacy two-second ordering boundary.
        # A known foreign input since connection attachment excludes this wait.
        # Delay NOT-YET-EXECUTED Study calls in that quiet interval;
        # never resurrect an executing task that scope retirement cancelled.
        late_ordering = (voice_route and str(call.name).startswith("study_")
                         and getattr(self, "_late_raw_transcript_connection", None) != owner.connection_generation
                         and getattr(self, "_late_raw_connection_foreign_scope", None) is not None
                         and self._late_raw_connection_foreign_scope == getattr(self, "_late_raw_foreign_scope", 0)
                         and loud_at > transcript_at and 0 <= now-loud_at <= self._STUDY_LATE_ORDERING_QUIET_SECONDS
                         and not getattr(self, "_fatal_error_occurred", False))
        # Read-only lookups and preference/session changes can also trigger an
        # early provider reply or consume a prefix's incomplete instructions.
        gated = (voice_route and str(call.name).startswith("study_")
                 and loud_at > 0 and (loud_at > transcript_at or 0 <= now - loud_at <= 2.0)
                 and __import__("os").environ.get("NEKO_STUDY_SPEECH_GATE") == "1")
        pending = getattr(self, "_late_raw_tool_pending", None)
        if response_id and pending:
            # A fast read-only sibling must not bypass the barrier of an
            # already-known gated call and seal that response's batch early.
            gated = gated or any(r["gated"] and not r["admitted"]
                                 and r["response_id"] == response_id
                                 and r["owner"].connection_generation == owner.connection_generation
                                 and r["owner"].provider_session is owner.provider_session
                                 and r["foreign_scope"] == getattr(self, "_late_raw_foreign_scope", 0)
                                 and (r.get("current", r["owner"]).scope_generation == owner.scope_generation
                                      or (r["released"] and r["owner"].scope_generation + 1 == owner.scope_generation))
                                 for r in pending)
        if not ordered and not gated and not late_ordering:
            return self._start_raw_tool_call_now(call, owner, response_id=response_id)
        if pending is None:
            pending = self._late_raw_tool_pending = []
        ready_here = (getattr(self, "_late_raw_transcript_scope", None) == owner.scope_generation
                      and getattr(self, "_late_raw_transcript_ready_scope", None) == owner.scope_generation)
        # Observed: this same fragment's call follows its ASR by ~55 ms,
        # while continuing PCM has already advanced last_loud. Keep that
        # call in the ready fragment's scope; do not await/promote its suffix.
        adjacent_ready = ready_here and 0 <= now - transcript_at <= 0.2
        needs_asr = (ordered or late_ordering) if not gated else (not ready_here or (loud_at > transcript_at and not adjacent_ready))
        record = {"event": asyncio.Event(), "owner": owner, "needs_asr": needs_asr,
                  "call": call, "response_id": response_id, "gated": gated, "admitted": False,
                  "queued_mono": time.monotonic(),
                  "late_ordering": late_ordering, "loud_snapshot": loud_at,
                  "input_sequence": getattr(self, "_voice_handoff_input_sequence", 0),
                  "foreign_scope": getattr(self, "_late_raw_foreign_scope", 0),
                  "released": False, "asr_observed": False}

        def same_connection():
            live = self._gemini_session if self._is_gemini else self.ws
            return (owner.connection_generation == self._connection_generation
                    and owner.provider_session is live
                    and record["foreign_scope"] == getattr(self, "_late_raw_foreign_scope", 0)
                    and (not record["late_ordering"] or (
                        record["input_sequence"] == getattr(self, "_voice_handoff_input_sequence", 0)
                        and record["loud_snapshot"] == getattr(self, "_last_local_loud_time", 0.0)
                        and not getattr(self, "_fatal_error_occurred", False)))
                    and not getattr(self, "_native_barge_in_pending", False)
                    and not (gated and getattr(self, "_fatal_error_occurred", False)))

        async def abandoned(reason):
            logger.info("study voice admission abandoned name=%s reason=%s scope=%s", call.name, reason, owner.scope_generation)
            batch = _ToolBatch(closed=True)
            batch.entries.append(_ToolBatchEntry(call, owner, asyncio.current_task(), abandoned=True))
            await self._close_unanswered_tool_calls(batch, owner)

        async def dispatch():
            try:
                deadline = time.monotonic() + self._STUDY_SPEECH_GATE_SECONDS
                if record["needs_asr"]:
                    try:
                        await asyncio.wait_for(record["event"].wait(), self._STUDY_SPEECH_GATE_SECONDS if gated else self._LATE_ASR_TOOL_WAIT_SECONDS)
                    except asyncio.TimeoutError:
                        if record["asr_observed"] and same_connection():
                            try:
                                callback_wait = min(self._LATE_ASR_CALLBACK_WAIT_SECONDS, max(0.0, deadline-time.monotonic())) if gated else self._LATE_ASR_CALLBACK_WAIT_SECONDS
                                await asyncio.wait_for(record["event"].wait(), callback_wait)
                            except asyncio.TimeoutError:
                                logger.warning("late ASR host callback readiness timed out")
                scope = getattr(self, "_tool_scope_generation", 0)
                if not same_connection():
                    await abandoned("connection_or_input_replaced"); return
                if record["released"]:
                    if scope != owner.scope_generation + 1:
                        await abandoned("scope_replaced"); return
                    current = self._capture_tool_task_owner(owner.provider_session,
                                                           connection_generation=owner.connection_generation)
                else:
                    if scope != owner.scope_generation or ((gated or late_ordering) and record["needs_asr"]):
                        await abandoned("transcript_not_ready"); return
                    current = owner
                # Fixed once. Never adopt a second fragment's scope while waiting.
                record["current"] = current
                if gated:
                    while True:
                        if record["admitted"]:
                            return
                        if not same_connection() or getattr(self, "_tool_scope_generation", 0) != current.scope_generation:
                            await abandoned("scope_or_connection_replaced"); return
                        latest_loud = getattr(self, "_last_local_loud_time", 0.0)
                        received = getattr(self, "_late_raw_transcript_at", 0.0)
                        ready = (getattr(self, "_late_raw_transcript_scope", None) == current.scope_generation
                                 and getattr(self, "_late_raw_transcript_ready_scope", None) == current.scope_generation)
                        if ready and received >= latest_loud and time.time() - latest_loud >= self._STUDY_SPEECH_QUIET_SECONDS:
                            break
                        if time.monotonic() >= deadline:
                            await abandoned("speech_or_transcript_deadline"); return
                        await asyncio.sleep(0.05)
                    logger.info("study voice admission ready name=%s scope=%s quiet=%.3f asr_after_loud=%.3f", call.name, current.scope_generation, time.time()-latest_loud, received-latest_loud)
                    if __import__("os").environ.get("NEKO_STUDY_SPEECH_GATE_TRACE") == "1":
                        arguments = call.arguments if isinstance(call.arguments, dict) else {}
                        fields = {key: str(arguments[key])[:600] for key in ("kind", "source_line", "source_file", "symbol", "question", "topic", "answer", "text") if key in arguments}
                        logger.info("study voice admission arguments name=%s scope=%s fields=%s", call.name, current.scope_generation, __import__("json").dumps(fields, ensure_ascii=False))
                    # Already queued siblings with this exact response/scope are
                    # admitted synchronously before a fast tool can seal the
                    # original unannounced batch. No future response is aliased.
                    cohort = [record]
                    if response_id:
                        cohort += [r for r in tuple(pending) if r is not record
                                   and r["gated"] and not r["admitted"] and r["response_id"] == response_id
                                   and r.get("current") is not None
                                   and r["current"].scope_generation == current.scope_generation
                                   and r["owner"].connection_generation == owner.connection_generation
                                   and r["owner"].provider_session is owner.provider_session
                                   and r["foreign_scope"] == record["foreign_scope"]]
                    for admitted in cohort:
                        admitted["admitted"] = True
                        self._start_raw_tool_call_now(admitted["call"], admitted["current"], response_id=admitted["response_id"])
                    return
                self._start_raw_tool_call_now(call, current, response_id=response_id)
            finally:
                if record in pending:
                    pending.remove(record)

        if len(pending) >= 16:
            if not gated and not late_ordering:
                return self._start_raw_tool_call_now(call, owner, response_id=response_id)
            return asyncio.create_task(abandoned("queue_full"))
        pending.append(record)
        task = asyncio.create_task(dispatch())
        # Independent pending, bounded on teardown. Old executing tasks retire normally.
        def done(completed):
            if not completed.cancelled() and completed.exception() is not None:
                logger.warning("late ASR tool dispatch failed: %s", type(completed.exception()).__name__)
        task.add_done_callback(done)
        return task

'''

TRANSCRIPT = '''    def _begin_raw_input_transcript(self):
        # Called synchronously after scoped completion, before the host callback awaits.
        # Callback completion time cannot stand in for ASR receipt time.
        self._late_raw_transcript_at = time.time()
        self._late_raw_transcript_connection = self._connection_generation
        received_mono = time.monotonic()
        self._late_raw_transcript_scope = getattr(self, "_tool_scope_generation", 0)
        self._late_raw_transcript_ready_scope = None
        for record in tuple(getattr(self, "_late_raw_tool_pending", ())):
            owner = record["owner"]
            if (record["needs_asr"] and record["foreign_scope"] == getattr(self, "_late_raw_foreign_scope", 0)
                    and self._late_raw_transcript_scope == owner.scope_generation + 1):
                # The observed final call can precede its ASR by milliseconds.
                # A prefix from seconds earlier must never acquire that final
                # scope with its old question/preferences still in arguments.
                if record.get("late_ordering"):
                    if (received_mono - record["queued_mono"] > self._STUDY_LATE_ORDERING_ASR_SECONDS
                            or record["input_sequence"] != getattr(self, "_voice_handoff_input_sequence", 0)
                            or record["loud_snapshot"] != getattr(self, "_last_local_loud_time", 0.0)):
                        record["event"].set()
                        continue
                elif record["gated"] and received_mono - record["queued_mono"] > self._STUDY_ASR_NEIGHBOR_SECONDS:
                    record["event"].set()
                    continue
                record["asr_observed"] = True

    def _finish_raw_input_transcript(self):
        scope = getattr(self, "_tool_scope_generation", 0)
        if getattr(self, "_late_raw_transcript_scope", None) != scope:
            return
        self._late_raw_transcript_ready_scope = scope
        for record in tuple(getattr(self, "_late_raw_tool_pending", ())):
            if record["asr_observed"] and scope == record["owner"].scope_generation + 1:
                record["released"] = True
                record["event"].set()

'''


def upgrade_ordering_helpers(helpers):
    """Build the canonical patch once; preserve exact prior helpers for migration."""
    start = helpers.index('    def _start_raw_tool_call(')
    end = helpers.index('    def _begin_raw_input_transcript(')
    return helpers[:start] + START + TRANSCRIPT
