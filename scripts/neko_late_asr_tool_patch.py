"""Bounded free-proxy tool/ASR ordering repair; leaves onset and PCM unchanged.

No stable proxy item ID is available for the observed late transcript. Queue only
recent voice calls on this exact route, pin their connection/session/scope, then
admit at most one expected transcript scope advance. A foreign scope retirement
never grants new ownership. This is ordering compatibility, not speech endpointing.
"""
from neko_native_barge_in_patch import _upgrade_targets

HELPERS = '''    # late-asr-tool-ordering-v1
    _LATE_ASR_TOOL_WAIT_SECONDS = 0.4
    _LATE_ASR_CALLBACK_WAIT_SECONDS = 2.0

    def _start_raw_tool_call(self, call, owner, *, response_id=None):
        route = getattr(getattr(self, "_realtime_protocol_capabilities", None), "route_key", None)
        now = time.time()
        loud_at = getattr(self, "_last_local_loud_time", 0.0)
        transcript_at = getattr(self, "_late_raw_transcript_at", 0.0)
        eligible = (route == "lanlan_app_gemini" and getattr(self, "_is_free_proxy", False)
                    and not getattr(self, "_has_server_vad", False)
                    and loud_at > transcript_at and 0 <= now - loud_at <= 2.0
                    and not getattr(self, "_native_barge_in_pending", False))
        if not eligible:
            return self._start_raw_tool_call_now(call, owner, response_id=response_id)
        pending = getattr(self, "_late_raw_tool_pending", None)
        if pending is None:
            pending = self._late_raw_tool_pending = []
        if len(pending) >= 16:
            return self._start_raw_tool_call_now(call, owner, response_id=response_id)
        record = {"event": asyncio.Event(), "owner": owner,
                  "foreign_scope": getattr(self, "_late_raw_foreign_scope", 0),
                  "released": False, "asr_observed": False}
        pending.append(record)

        def same_connection():
            live = self._gemini_session if self._is_gemini else self.ws
            return (owner.connection_generation == self._connection_generation
                    and owner.provider_session is live
                    and record["foreign_scope"] == getattr(self, "_late_raw_foreign_scope", 0)
                    and not getattr(self, "_native_barge_in_pending", False))

        async def abandoned():
            # Reuse the original no-continuation release instead of wedging a
            # provider lane. The original method retains its connection fences.
            batch = _ToolBatch(closed=True)
            batch.entries.append(_ToolBatchEntry(call, owner, asyncio.current_task(), abandoned=True))
            await self._close_unanswered_tool_calls(batch, owner)

        async def dispatch():
            try:
                try:
                    await asyncio.wait_for(record["event"].wait(), self._LATE_ASR_TOOL_WAIT_SECONDS)
                except asyncio.TimeoutError:
                    if record["asr_observed"] and same_connection():
                        # Input completion already established the scope. Allow
                        # its host callback to finish without losing the call
                        # merely because that callback took longer than .4 s.
                        try:
                            await asyncio.wait_for(record["event"].wait(), self._LATE_ASR_CALLBACK_WAIT_SECONDS)
                        except asyncio.TimeoutError:
                            logger.warning("late ASR host callback readiness timed out")
                scope = getattr(self, "_tool_scope_generation", 0)
                if not same_connection():
                    await abandoned()
                    return
                if record["released"]:
                    if scope != owner.scope_generation + 1:
                        await abandoned()
                        return
                    current = self._capture_tool_task_owner(owner.provider_session,
                                                           connection_generation=owner.connection_generation)
                else:
                    # No completion arrived: retain the original owner, never
                    # promote a timed-out call to whichever turn is now live.
                    if scope != owner.scope_generation:
                        await abandoned()
                        return
                    current = owner
                self._start_raw_tool_call_now(call, current, response_id=response_id)
            finally:
                if record in pending:
                    pending.remove(record)

        task = asyncio.create_task(dispatch())
        # Kept outside _tool_tasks: the one expected ASR must retire OLD work,
        # not this not-yet-dispatched call. The wait remains bounded on teardown.
        def done(completed):
            if not completed.cancelled() and completed.exception() is not None:
                logger.warning("late ASR tool dispatch failed: %s", type(completed.exception()).__name__)
        task.add_done_callback(done)
        return task

    def _begin_raw_input_transcript(self):
        for record in tuple(getattr(self, "_late_raw_tool_pending", ())):
            owner = record["owner"]
            if (record["foreign_scope"] == getattr(self, "_late_raw_foreign_scope", 0)
                    and getattr(self, "_tool_scope_generation", 0) == owner.scope_generation + 1):
                record["asr_observed"] = True

    def _finish_raw_input_transcript(self):
        self._late_raw_transcript_at = time.time()
        for record in tuple(getattr(self, "_late_raw_tool_pending", ())):
            if record["asr_observed"]:
                record["released"] = True
                record["event"].set()

'''

_V2_WAIT = '''                except asyncio.TimeoutError:
                    if record["asr_observed"] and same_connection():
                        # Input completion already established the scope. Allow
                        # its host callback to finish without losing the call
                        # merely because that callback took longer than .4 s.
                        try:
                            await asyncio.wait_for(record["event"].wait(), self._LATE_ASR_CALLBACK_WAIT_SECONDS)
                        except asyncio.TimeoutError:
                            logger.warning("late ASR host callback readiness timed out")
'''
_V2_FINISH = '''    def _begin_raw_input_transcript(self):
        for record in tuple(getattr(self, "_late_raw_tool_pending", ())):
            owner = record["owner"]
            if (record["foreign_scope"] == getattr(self, "_late_raw_foreign_scope", 0)
                    and getattr(self, "_tool_scope_generation", 0) == owner.scope_generation + 1):
                record["asr_observed"] = True

    def _finish_raw_input_transcript(self):
        self._late_raw_transcript_at = time.time()
        for record in tuple(getattr(self, "_late_raw_tool_pending", ())):
            if record["asr_observed"]:
                record["released"] = True
                record["event"].set()

'''
_V1_FINISH = '''    def _finish_raw_input_transcript(self):
        self._late_raw_transcript_at = time.time()
        for record in tuple(getattr(self, "_late_raw_tool_pending", ())):
            owner = record["owner"]
            if (record["foreign_scope"] == getattr(self, "_late_raw_foreign_scope", 0)
                    and getattr(self, "_tool_scope_generation", 0) == owner.scope_generation + 1):
                record["released"] = True
                record["event"].set()

'''
# Precisely migrate the first offline draft; unknown helper bytes still refuse.
LEGACY_HELPERS = (HELPERS.replace('    _LATE_ASR_CALLBACK_WAIT_SECONDS = 2.0\n', '')
                 .replace('"released": False, "asr_observed": False}', '"released": False}')
                 .replace(_V2_WAIT, '                except asyncio.TimeoutError:\n                    pass\n')
                 .replace(_V2_FINISH, _V1_FINISH))

UPGRADES = {
    "main_logic/omni_realtime_client/_tools.py": (
        ('    def _start_raw_tool_call(\n', HELPERS + '    def _start_raw_tool_call_now(\n'),
        ('        self._tool_scope_generation = getattr(self, "_tool_scope_generation", 0) + 1\n',
         '        if not getattr(self, "_late_raw_expected_asr_advance", False):\n'
         '            self._late_raw_foreign_scope = getattr(self, "_late_raw_foreign_scope", 0) + 1\n'
         '        self._tool_scope_generation = getattr(self, "_tool_scope_generation", 0) + 1\n'),
    ),
    "main_logic/omni_realtime_client/_transport.py": (
        ('                        self.note_user_turn_started()\n                    self._print_input_transcript = True\n',
         '                        self._late_raw_expected_asr_advance = True\n'
         '                        try:\n                            self.note_user_turn_started()\n'
         '                        finally:\n                            self._late_raw_expected_asr_advance = False\n'
         '                    self._begin_raw_input_transcript()\n'
         '                    self._print_input_transcript = True\n'),
        ('                            return\n                elif event_type in ["response.audio_transcript.done", "response.output_audio_transcript.done"]:\n',
         '                            return\n                    self._finish_raw_input_transcript()\n'
         '                elif event_type in ["response.audio_transcript.done", "response.output_audio_transcript.done"]:\n'),
    ),
}

MIGRATIONS = (
    ('main_logic/omni_realtime_client/_tools.py', LEGACY_HELPERS + '    def _start_raw_tool_call_now(\n', HELPERS + '    def _start_raw_tool_call_now(\n'),
    ('main_logic/omni_realtime_client/_transport.py',
     '                            self._late_raw_expected_asr_advance = False\n                    self._print_input_transcript = True\n',
     '                            self._late_raw_expected_asr_advance = False\n                    self._begin_raw_input_transcript()\n                    self._print_input_transcript = True\n'),
)


def upgrade_targets(targets):
    if any('# late-asr-tool-ordering-v1' in new for _, pairs in targets for _, new in pairs):
        return targets, ()
    final,replay = _upgrade_targets(targets, UPGRADES, [])
    # Draft migrations belong only to replay, not to canonical inverse hunks.
    return final, MIGRATIONS + replay
