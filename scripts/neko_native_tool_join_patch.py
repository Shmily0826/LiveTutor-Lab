"""Single-input Native tool continuation, used only by the opt-in phrase route."""
from neko_native_audio_dispatch_patch import upgrade_targets as audio_targets
from neko_native_barge_in_patch import _upgrade_targets

ARBITER_METHODS = '''    _NATIVE_TOOL_RESPONSE_WAIT_SECONDS = 30.0

    def _native_tool_owner(self, origin):
        owner = self._response_owner
        if (origin is None or owner is None or owner is not self._current
                or not owner.automatic_audio or owner.native_tool_origin is not origin
                or owner.interrupted or not self._connection_available
                or owner.terminal is None or owner.terminal.done()
                or (owner.admission_check is not None and not owner.admission_check())):
            raise ResponseAdmissionRejected("native tool input origin retired")
        return owner

    def capture_native_tool_origin(self, call_id, *, wire_call_id=None, connection_check=None):
        owner = self._response_owner
        if owner is None or not owner.automatic_audio:
            return None
        owner = self._native_tool_owner(owner.native_tool_origin)
        if not owner.response_send_started or owner.ticket.started.done():
            raise ResponseAdmissionRejected("native tool arrived outside the supported pre-content slot")
        if (not isinstance(wire_call_id, str) or not wire_call_id
                or len(wire_call_id) > 1000 or call_id != wire_call_id):
            raise ValueError("native continuation needs an actual bounded call id")
        if (call_id in owner.native_tools_written or call_id in owner.native_tools_pending
                or len(owner.native_tools_pending | owner.native_tools_written) >= 32):
            raise RuntimeError("duplicate or excessive native tool continuation")
        owner.native_tools_pending.add(call_id)
        if owner.native_tool_connection_check is None:
            owner.native_tool_connection_check = connection_check
        owner.native_tools_changed.set()
        return owner.native_tool_origin

    def native_tool_origin_is_current(self, origin):
        try:
            self._native_tool_owner(origin)
            return True
        except ResponseAdmissionRejected:
            return False

    async def wait_native_tool_input(self, origin):
        owner = self._native_tool_owner(origin)
        async with asyncio.timeout(8):
            await asyncio.shield(owner.ticket.sent)
        self._native_tool_owner(origin)

    def reject_native_tool_origin(self, origin):
        try:
            owner = self._native_tool_owner(origin)
        except ResponseAdmissionRejected:
            return
        error = RuntimeError("native tool continuation was abandoned")
        self._fail_ticket(owner.ticket, error)
        if owner.terminal is not None and not owner.terminal.done():
            owner.terminal.set_exception(error)
        owner.native_tools_changed.set()

    async def join_native_tool_results(self, origin, events, *, event_sender, admission_check):
        owner = self._native_tool_owner(origin)
        call_ids = [event.get("item", {}).get("call_id") for event in events]
        if (not events or len(events) > 32 or len(set(call_ids)) != len(call_ids)
                or any(event.get("type") != "conversation.item.create"
                    or event.get("item", {}).get("type") != "function_call_output"
                    or not isinstance(event.get("item", {}).get("output"), str)
                    for event in events)
                or any(call_id not in owner.native_tools_pending for call_id in call_ids)):
            raise ValueError("native continuation contains an unregistered tool output")
        def current():
            return (self.native_tool_origin_is_current(origin) and admission_check())
        try:
            async with asyncio.timeout(8):
                await asyncio.shield(owner.ticket.sent)
                async with owner.native_join_lock:
                    if not current() or any(call_id not in owner.native_tools_pending for call_id in call_ids):
                        raise ResponseAdmissionRejected("native tool continuation retired before write")
                    for event in events:
                        event.setdefault("event_id", "event_arbiter_" + uuid.uuid4().hex)
                    owner.event_ids |= frozenset(event["event_id"] for event in events)
                    for event in events:
                        if not current():
                            raise ResponseAdmissionRejected("native tool continuation retired during write")
                        owner.submitted_item_event_ids.append(event["event_id"])
                        self._worker_send_in_flight = True
                        try:
                            await event_sender(event)
                        finally:
                            self._worker_send_in_flight = False
                        if not current():
                            raise ResponseAdmissionRejected("native tool continuation retired after write")
                    owner.native_tools_pending.difference_update(call_ids)
                    owner.native_tools_written.update(call_ids)
                    owner.native_tools_changed.set()
        except BaseException:
            # A partially sent batch must never fall back to a second submission.
            self.reject_native_tool_origin(origin)
            raise

    async def _wait_native_audio_started(self, owner):
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        overall_deadline = started_at + self._NATIVE_TOOL_RESPONSE_WAIT_SECONDS
        idle_deadline = started_at + owner.response_started_timeout
        while not owner.ticket.started.done():
            if owner.interrupt_event.is_set():
                if (owner.native_tool_connection_check is not None
                        and not owner.native_tool_connection_check()):
                    raise ResponseAdmissionRejected("native tool connection retired during cancellation")
                raise asyncio.TimeoutError("native automatic response interrupted before content")
            pending = bool(owner.native_tools_pending)
            deadline = overall_deadline if pending else min(overall_deadline, idle_deadline)
            owner.native_start_wait_budget = deadline - started_at
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError("native automatic response start timed out")
            owner.native_tools_changed.clear()
            changed = asyncio.create_task(owner.native_tools_changed.wait())
            interrupted = asyncio.create_task(owner.interrupt_event.wait())
            try:
                with self._report_wait_margin("native response/tool wait", remaining):
                    await asyncio.wait((owner.ticket.started, changed, interrupted), timeout=remaining,
                                       return_when=asyncio.FIRST_COMPLETED)
            finally:
                changed.cancel()
                interrupted.cancel()
                await asyncio.gather(changed, interrupted, return_exceptions=True)
            if not owner.native_tools_pending and changed.done() and not changed.cancelled():
                idle_deadline = loop.time() + owner.response_started_timeout
        await asyncio.shield(owner.ticket.started)

'''

UPGRADES = {
    'main_logic/omni_realtime_client/_response_arbiter.py': (
        ('    automatic_audio: bool = field(default=False, compare=False)\n',
         '    automatic_audio: bool = field(default=False, compare=False)\n'
         '    native_tool_origin: object = field(default_factory=object, compare=False)\n'
         '    native_tool_connection_check: object = field(default=None, compare=False)\n'
         '    native_tools_pending: set = field(default_factory=set, compare=False)\n'
         '    native_tools_written: set = field(default_factory=set, compare=False)\n'
         '    native_tools_changed: asyncio.Event = field(default_factory=asyncio.Event, compare=False)\n'
         '    native_join_lock: asyncio.Lock = field(default_factory=asyncio.Lock, compare=False)\n'
         '    native_start_wait_budget: float = field(default=5.0, compare=False)\n'),
        ('    def native_input_sequence_for(self, response_id):',
         ARBITER_METHODS + '    def native_input_sequence_for(self, response_id):'),
        ('                if owner.automatic_audio and response_status not in {"completed", "success", "succeeded"}:\n',
         '                if owner.automatic_audio and owner.native_tools_pending:\n'
         '                    terminal_error = RuntimeError("native tool outputs were not fully submitted")\n'
         '                if owner.automatic_audio and response_status not in {"completed", "success", "succeeded"}:\n'),
        ('                with self._report_wait_margin(\n'
         '                    "response announcement", queued.response_started_timeout\n'
         '                ):\n'
         '                    await asyncio.wait_for(\n'
         '                        asyncio.shield(queued.ticket.started),\n'
         '                        queued.response_started_timeout,\n'
         '                    )',
         '                if queued.automatic_audio:\n'
         '                    await self._wait_native_audio_started(queued)\n'
         '                else:\n'
         '                    with self._report_wait_margin("response announcement", queued.response_started_timeout):\n'
         '                        await asyncio.wait_for(asyncio.shield(queued.ticket.started), queued.response_started_timeout)'),
        ('                            "timeout_s": queued.response_started_timeout,\n',
         '                            "timeout_s": (queued.native_start_wait_budget if queued.automatic_audio else queued.response_started_timeout),\n'),
        ('                adopted_id = self._adoptable_id_for(queued)\n',
         '                if queued.automatic_audio and queued.interrupted:\n'
         '                    await self._cancel_after_timeout(queued, started_timeout)\n'
         '                adopted_id = self._adoptable_id_for(queued)\n'),
        ('            await self._escalate(\n'
         '                "response lifecycle could not reach a terminal state",\n',
         '            if (queued.automatic_audio and queued.native_tool_connection_check is not None\n'
         '                    and not queued.native_tool_connection_check()):\n'
         '                raise ResponseAdmissionRejected("native tool connection retired during cancel grace")\n'
         '            await self._escalate(\n'
         '                "response lifecycle could not reach a terminal state",\n'),
    ),
    'main_logic/omni_realtime_client/_tools.py': (
        ('from dataclasses import dataclass, field\n', 'from dataclasses import dataclass, field, replace\n'),
        ('    turn_pair_fence_applies: bool = True\n',
         '    turn_pair_fence_applies: bool = True\n'
         '    native_audio_origin: object = field(default=None, compare=False)\n'),
        ('    def _start_raw_tool_call(self, call, owner, *, response_id=None):\n',
         '    def _start_raw_tool_call(self, call, owner, *, response_id=None):\n'
         '        arbiter = getattr(self, "_response_arbiter", None)\n'
         '        if (arbiter is not None and self._tool_task_connection_is_current(owner)\n'
         '                and not getattr(self, "_native_barge_in_pending", False)\n'
         '                and not getattr(self, "_fatal_error_occurred", False)\n'
         '                and owner.scope_generation == getattr(self, "_tool_scope_generation", 0)):\n'
         '            origin = arbiter.capture_native_tool_origin(call.call_id,\n'
         '                wire_call_id=call.provider_meta.get("native_wire_call_id"),\n'
         '                connection_check=lambda: self._tool_task_connection_is_current(owner))\n'
         '            if origin is None and getattr(self, "_native_phrase_uplink", None) is not None:\n'
         '                raise RuntimeError("native tool has no qualified outstanding input slot")\n'
         '            owner = replace(owner, native_audio_origin=origin)\n'),
        ('                    current = self._capture_tool_task_owner(owner.provider_session,\n'
         '                                                           connection_generation=owner.connection_generation)\n',
         '                    current = self._capture_tool_task_owner(owner.provider_session,\n'
         '                                                           connection_generation=owner.connection_generation)\n'
         '                    current = replace(current, native_audio_origin=owner.native_audio_origin)\n'),
        ('                turn_pair_fence_applies=False,\n',
         '                turn_pair_fence_applies=False,\n'
         '                native_audio_origin=owner.native_audio_origin,\n'),
        ('        async def _run() -> ToolResult | None:\n'
         '            if not self._tool_task_owner_is_current(owner):\n',
         '        async def _run() -> ToolResult | None:\n'
         '            if owner.native_audio_origin is not None:\n'
         '                await self._ensure_response_arbiter().wait_native_tool_input(owner.native_audio_origin)\n'
         '            if (not self._tool_task_owner_is_current(owner)\n'
         '                    or (owner.native_audio_origin is not None and not self._ensure_response_arbiter().native_tool_origin_is_current(owner.native_audio_origin))):\n'),
        ('        results = await self._collect_tool_batch(batch, owner)\n'
         '        if results:\n'
         '            await self._send_tool_results_openai_realtime(results, owner=owner)\n',
         '        results = await self._collect_tool_batch(batch, owner)\n'
         '        origin = getattr(owner, "native_audio_origin", None)\n'
         '        origins = [getattr(entry.owner, "native_audio_origin", None) for entry in batch.entries]\n'
         '        if any(value is not None for value in origins):\n'
         '            if (origin is None or any(value is not origin for value in origins)\n'
         '                    or any(not self._tool_task_owner_is_current(entry.owner) for entry in batch.entries)\n'
         '                    or {result.call_id for result in results} != {entry.call.call_id for entry in batch.entries}):\n'
         '                for value in origins:\n'
         '                    if value is not None:\n'
         '                        self._ensure_response_arbiter().reject_native_tool_origin(value)\n'
         '                await self._close_unanswered_tool_calls(batch, owner)\n'
         '                return\n'
         '        if results:\n'
         '            await self._send_tool_results_openai_realtime(results, owner=owner)\n'),
        ('        if not self._tool_task_connection_is_current(owner):\n            return\n        live_session = self._gemini_session if self._is_gemini else self.ws\n',
         '        origin = getattr(owner, "native_audio_origin", None)\n'
         '        if origin is not None:\n'
         '            self._ensure_response_arbiter().reject_native_tool_origin(origin)\n'
         '        if not self._tool_task_connection_is_current(owner):\n            return\n        live_session = self._gemini_session if self._is_gemini else self.ws\n'),
        ('        async def _send_owned_event(event: Dict[str, Any]) -> None:\n',
         '        native_origin = getattr(owner, "native_audio_origin", None)\n'
         '        async def _send_owned_event(event: Dict[str, Any]) -> None:\n'),
        ('            await self.send_event(\n                event,\n                send_guard=(\n',
         '            sent = await self.send_event(\n                event,\n                send_guard=(\n'),
        ('                    else (lambda: self._tool_task_owner_is_current(owner))\n',
         '                    else (lambda: self._tool_task_owner_is_current(owner)\n'
         '                        and (native_origin is None or arbiter.native_tool_origin_is_current(native_origin)))\n'),
        ('        ticket = await arbiter.enqueue(\n            source="tool_result",\n',
         '            if native_origin is not None and sent is not True:\n'
         '                raise ConnectionError("native tool result write refused")\n\n'
         '        if native_origin is not None:\n'
         '            await arbiter.join_native_tool_results(native_origin, tuple(item_events),\n'
         '                event_sender=_send_owned_event,\n'
         '                admission_check=lambda: self._tool_task_owner_is_current(owner))\n'
         '            return\n'
         '        ticket = await arbiter.enqueue(\n            source="tool_result",\n'),
    ),
    'main_logic/omni_realtime_client/_transport.py': (
        ('                                call_id=call_id,\n'
         '                                raw_arguments=raw_args,\n',
         '                                call_id=call_id,\n'
         '                                raw_arguments=raw_args,\n'
         '                                provider_meta={"native_wire_call_id": event.get("call_id")},\n'),
    ),
}


def upgrade_targets(targets, replay):
    targets, replay = audio_targets(targets, replay)
    targets, added = _upgrade_targets(targets, UPGRADES, [])
    transformed = []
    for relative, old, new in replay:
        for before, after in UPGRADES.get(relative, ()):
            new = new.replace(before, after)
        transformed.append((relative, old, new))
    # Apply narrow edits before older overlapping whole-function migrations.
    direct = tuple((relative, before, after) for relative, pairs in UPGRADES.items()
                   for before, after in pairs)
    return targets, direct + added + tuple(transformed)


def normalize_ordering_helpers(source):
    from neko_late_asr_tool_patch import HELPERS, normalize_ordering_helpers as original
    expected = HELPERS
    for before, after in UPGRADES['main_logic/omni_realtime_client/_tools.py']:
        expected = expected.replace(before, after)
    start = '    # late-asr-tool-ordering-v1\n'
    end = '    def _start_raw_tool_call_now(\n'
    if source.count(start) == 1 and source.count(end) == 1:
        if source[source.index(start):source.index(end)] == expected:
            return source
    return original(source)
