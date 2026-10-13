"""Bind trusted Study output to material identity and retire its native connection.

No speech onset emulation, PCM replay, or response-id aliasing. Material updates
use the existing physical connection playback cancellation and one bounded swap.
"""
from neko_native_barge_in_patch import _upgrade_targets

HELPERS = '''    @staticmethod
    def _valid_study_material_record(value, *, binding=False):
        if not isinstance(value, dict) or type(value.get("v")) is not int or value.get("v") != 1:
            return False
        boot = value.get("boot_id")
        seq = value.get("change_seq")
        if (not isinstance(boot, str) or len(boot) != 32
                or any(char not in "0123456789abcdef" for char in boot)
                or type(seq) is not int or seq < 0):
            return False
        fields = ("context",) if binding else ("before", "after")
        for field in fields:
            context = value.get(field)
            if (not isinstance(context, dict) or not context
                    or set(context) - {"course_id", "session_id", "material_identity"}
                    or not {"course_id", "session_id"} <= set(context)
                    or any(not isinstance(item, str) or len(item) > 256 for item in context.values())):
                return False
            identity = context.get("material_identity")
            if identity is not None and (len(identity) != 64 or any(char not in "0123456789abcdef" for char in identity)):
                return False
        return True

    def _study_material_native_output_held(self):
        source = getattr(self, "session", None)
        hold = getattr(source, "_study_material_output_hold", None)
        return bool(hold and not getattr(self, "use_tts", False)
                    and getattr(source, "_is_free_proxy", False)
                    and source._connection_generation == hold["connection"]
                    and getattr(source, "_study_material_user_epoch", 0) == hold["user_epoch"])

    def _capture_study_material_tool_owner(self, call, invoking_session):
        definition = self.tool_registry.get(call.name)
        source = invoking_session
        if call.name == "study_explain":
            logger.info("[study-material-audio] binding admission trusted=%s current=%s class=%s free=%s tts=%s route=%s lease=%s native_class=%s takeover=%s token_present=%s",
                getattr(definition, "metadata", {}).get("source") == "plugin:study_companion", source is self.session,
                type(source).__name__, getattr(source, "_is_free_proxy", False),
                getattr(self, "use_tts", False), self._asr_route_mode, self._voice_lease_owner,
                isinstance(source, OmniRealtimeClient), self._takeover_active,
                str(getattr(source, "_native_output_connection_token", "")).startswith("native_connection_"))
        if (call.name != "study_explain" or definition is None
                or definition.metadata.get("source") != "plugin:study_companion"
                or source is not self.session or not isinstance(source, OmniRealtimeClient)
                or not getattr(source, "_is_free_proxy", False)
                or getattr(self, "use_tts", False) or self._takeover_active
                or not str(getattr(source, "_native_output_connection_token", "")).startswith("native_connection_")):
            return None
        provider = source._gemini_session if source._is_gemini else source.ws
        entry = getattr(source, "_tool_batch_entry_by_task", {}).get(asyncio.current_task())
        if entry is not None:
            if entry.abandoned or entry.call.call_id != call.call_id:
                logger.info("[study-material-audio] binding rejected abandoned=%s call_matches=%s",
                    entry.abandoned, entry.call.call_id == call.call_id)
                return None
            owner = entry.owner # preserve the actual unannounced-response fence
        else:
            owner = source._capture_tool_task_owner(provider)
        return {"source": source, "tool_owner": owner,
                "socket": self.websocket, "activation": self._capture_voice_session_activation_generation(),
                "input_route": self._asr_route_mode, "input_lease": self._voice_lease_owner}

    async def _bind_study_material_tool_result(self, captured, result):
        logger.info("[study-material-audio] result admission captured=%s error=%s output_kind=%s",
            captured is not None, result.is_error, type(result.output).__name__)
        if captured is None or result.is_error:
            return
        payload = result.output
        if isinstance(payload, str):
            try:
                payload = __import__("json").loads(payload)
            except (ValueError, TypeError):
                return
        if not isinstance(payload, dict):
            return
        record = payload.get("_study_material_binding")
        logger.info("[study-material-audio] result binding present=%s valid=%s reply=%s",
            record is not None, self._valid_study_material_record(record, binding=True),
            isinstance(payload.get("reply"), str) and bool(payload.get("reply")))
        if not self._valid_study_material_record(record, binding=True):
            return
        # Host-only provenance does not need to enter the provider's prompt.
        result.output = {key: value for key, value in payload.items() if key != "_study_material_binding"}
        source = captured["source"]
        owner = captured["tool_owner"]
        if (payload.get("degraded") or payload.get("ok") is False or not payload.get("reply")
                or not isinstance(payload.get("reply"), str)
                or source is not self.session or self.websocket is not captured["socket"]
                or not source._tool_task_owner_is_current(owner)
                or self._capture_voice_session_activation_generation() != captured["activation"]):
            return
        binding = {**captured, "record": __import__("copy").deepcopy(record),
                   "connection": source._connection_generation,
                   "token": getattr(source, "_native_output_connection_token", None)}
        self._study_material_output_owner = binding
        logger.info("[study-material-audio] output bound connection=%s", binding["connection"])
        # A UI change may arrive while the tool response is in transit. Do not
        # lose that control just because no output was bound at its arrival.
        latest = getattr(self, "_study_material_controls", {}).get(record["boot_id"])
        if latest and latest["change_seq"] > record["change_seq"]:
            await self._apply_study_material_control(latest)

    async def _apply_study_material_control(self, control):
        if not self._valid_study_material_record(control):
            return False
        controls = getattr(self, "_study_material_controls", None)
        if controls is None:
            controls = self._study_material_controls = {}
        boot = control["boot_id"]
        previous = controls.get(boot)
        if previous and previous["change_seq"] > control["change_seq"]:
            return False
        if previous is None and len(controls) >= 4:
            controls.pop(next(iter(controls)))
        controls[boot] = __import__("copy").deepcopy(control)
        binding = getattr(self, "_study_material_output_owner", None)
        if not binding:
            return False
        record = binding["record"]
        if record["boot_id"] != boot or control["change_seq"] <= record["change_seq"]:
            return False
        expected = record["context"]
        # Also handles a missed intermediate A->B notification followed by B->C:
        # sequence establishes that C is newer than the bound A. A late event
        # cannot cancel C's newer binding. Immutable explicit text is unaffected
        # by a picture-only change of the same course/session.
        if all(control["after"].get(key) == value for key, value in expected.items()):
            return False
        source = binding["source"]
        owner = binding["tool_owner"]
        if (source is not self.session or self.websocket is not binding["socket"]
                or self._takeover_active or not self.is_active or getattr(self, "use_tts", False)
                or self._asr_route_mode != binding["input_route"] or self._voice_lease_owner != binding["input_lease"]
                or not source._tool_task_owner_is_current(owner)
                or source._connection_generation != binding["connection"]
                or self._capture_voice_session_activation_generation() != binding["activation"]
                or getattr(source, "_native_barge_in_pending", False)
                or getattr(source, "_study_material_replacing", False)
                or not binding["token"]):
            return False
        source._study_material_replacing = True
        # Scope retirement can cancel the tool that is currently binding a late
        # result. The independently owned swap must survive that cancellation.
        task = asyncio.create_task(self._replace_study_material_native_connection(binding))
        source._study_material_replace_task = task
        def completed(done):
            if getattr(source, "_study_material_replace_task", None) is done:
                source._study_material_replace_task = None
            if not done.cancelled() and done.exception() is not None:
                logger.warning("[study-material-audio] task failed kind=%s", type(done.exception()).__name__)
        task.add_done_callback(completed)
        source.note_user_turn_started() # retire tools; no speech onset or input replay
        binding["replacement_user_epoch"] = getattr(source, "_study_material_user_epoch", 0)
        hold = {"connection": binding["connection"], "user_epoch": binding["replacement_user_epoch"]}
        binding["output_hold"] = source._study_material_output_hold = hold
        self._study_material_output_owner = None
        return await asyncio.shield(task)

    async def _replace_study_material_native_connection(self, binding):
        source = binding["source"]
        socket = binding["socket"]
        connection = binding["connection"]
        owned_connection = connection
        lock = self._core_voice_session_swap_lock
        locked = False
        attempted = False
        cancel_attempted = False
        success = False
        def physical_current():
            return bool(source is self.session and self.is_active
                and self.websocket is socket and self._asr_route_mode == binding["input_route"]
                and self._voice_lease_owner == binding["input_lease"] and not self._takeover_active
                and not getattr(self, "use_tts", False)
                and self._capture_voice_session_activation_generation() == binding["activation"])
        def current():
            return physical_current() and getattr(source, "_study_material_user_epoch", 0) == binding["replacement_user_epoch"]
        def failed_owner_current():
            # A cancel already sent retires this physical token irreversibly.
            # A new input on that SAME old connection needs explicit restart,
            # not a silent fatal connection or a fake successful takeover.
            return current() or (cancel_attempted and physical_current()
                                 and source._connection_generation == connection)
        try:
            barrier = self._core_voice_session_swap_barrier_timeout_s
            close_timeout = self._core_voice_listener_cancel_timeout_s
            async with asyncio.timeout(self._native_activation_reconnect_timeout_s + barrier + close_timeout):
                await asyncio.wait_for(lock.acquire(), timeout=barrier)
                locked = True
                if not current() or source._connection_generation != connection:
                    return False
                attempted = True
                async with self._ensure_audio_frame_send_lock():
                    if not current() or source._connection_generation != connection:
                        return False
                    source._interrupted = source._fatal_error_occurred = True
                    cancel_attempted = True
                    await socket.send_json({"type": "game_route_speech_cancel",
                        "sdk_speech_correlation_id": binding["token"]})
                if not current() or source._connection_generation != connection:
                    return False
                await asyncio.wait_for(source.close(), timeout=close_timeout)
                if not current() or source._connection_generation != connection:
                    return False
                if not await self._restart_message_handler_after_session_reconnect(source, start_listener=False):
                    raise RuntimeError("study_material_listener_not_drained")
                if not current() or source._connection_generation != connection:
                    return False
                # One normal connect resets input buffers and gets a fresh physical
                # output token. Never call the barge-in replay path for a UI change.
                try:
                    await source.connect(str(getattr(source, "instructions", "") or ""), native_audio=True)
                finally:
                    owned_connection = min(source._connection_generation, connection + 1)
                if not current() or source._connection_generation != connection + 1:
                    raise RuntimeError("study_material_connection_not_replaced")
                if not await self._restart_message_handler_after_session_reconnect(source):
                    raise RuntimeError("study_material_listener_restart_failed")
                if not current() or source._connection_generation != owned_connection:
                    return False
                self.session_closed_by_server = False
                success = True
                logger.info("[study-material-audio] connection retired and restored %d->%d", connection, owned_connection)
                return True
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # No automatic retry loop and no old-material PCM or reply replay.
            logger.warning("[study-material-audio] restore failed kind=%s", type(error).__name__)
            return False
        finally:
            failed_ours = not success and failed_owner_current() and source._connection_generation == owned_connection
            if failed_ours:
                try:
                    if not cancel_attempted:
                        # Even a swap-lock timeout must suppress the exact old
                        # renderer queue. At most one cancel delivery attempt.
                        async with asyncio.timeout(self._core_voice_listener_cancel_timeout_s):
                            async with self._ensure_audio_frame_send_lock():
                                if current() and source._connection_generation == connection:
                                    cancel_attempted = True
                                    await socket.send_json({"type": "game_route_speech_cancel",
                                        "sdk_speech_correlation_id": binding["token"]})
                    if failed_owner_current() and source._connection_generation == owned_connection:
                        source._interrupted = source._fatal_error_occurred = True
                        await asyncio.wait_for(source.close(), timeout=self._core_voice_listener_cancel_timeout_s)
                except (Exception, asyncio.CancelledError):
                    pass
            source._study_material_replacing = False
            if getattr(source, "_study_material_output_hold", None) is binding.get("output_hold"):
                source._study_material_output_hold = None
            if locked:
                lock.release()
            if failed_ours and failed_owner_current() and source._connection_generation == owned_connection:
                await self.send_status("材料已更新，语音未能恢复，请重新开始语音。")
                if failed_owner_current() and source._connection_generation == owned_connection:
                    await self.disconnected_by_server(expected_session=source, announce_disconnect=False)

'''

_EXECUTE_PRIOR = '''        material_owner = self._capture_study_material_tool_owner(call, invoking_session)
        result = await self.tool_registry.execute(call)
        await self._bind_study_material_tool_result(material_owner, result)
        if result.images:'''

_EXECUTE_ROUTED_PRIOR = '''        material_owner = self._capture_study_material_tool_owner(call, invoking_session)
        dispatched_call = call
        if material_owner is not None:
            # The process-global remote dispatcher has no manager identity.
            # Supply only this trusted role; ignore model-supplied _ctx and do
            # not mutate original arguments used by exact-inflight sharing.
            role = str(getattr(self, "lanlan_name", "") or "").strip()
            arguments = {**(getattr(call, "arguments", None) or {}), "_ctx": {"lanlan_name": role}}
            dataclasses = __import__("dataclasses")
            if dataclasses.is_dataclass(call):
                dispatched_call = dataclasses.replace(call, arguments=arguments)
            else:
                dispatched_call = __import__("copy").copy(call)
                dispatched_call.arguments = arguments
        result = await self.tool_registry.execute(dispatched_call)
        await self._bind_study_material_tool_result(material_owner, result)
        if result.images:'''

_EXECUTE = _EXECUTE_ROUTED_PRIOR.replace(
    '        if material_owner is not None:',
    '''        definition = self.tool_registry.get(call.name)
        if (call.name == "study_explain" and definition is not None
                and definition.metadata.get("source") == "plugin:study_companion"
                and invoking_session is not None and invoking_session is self.session):'''
).replace(
    '            arguments = {**',
    '''            logger.info("[study-material-audio] dispatch role_length=%d captured=%s", len(role), material_owner is not None)
            arguments = {**'''
)

_EXECUTE_CURRENT_PRIOR = _EXECUTE
_EXECUTE = _EXECUTE.replace('        if result.images:', '''        if (call.name == "study_explain" and definition is not None
                and definition.metadata.get("source") == "plugin:study_companion"):
            # Provenance stays host-only even when Native capture was refused
            # (TTS, stale owner, unavailable token, or failed tool result).
            payload = result.output
            if isinstance(payload, str):
                try:
                    payload = __import__("json").loads(payload)
                except (ValueError, TypeError):
                    payload = None
            if isinstance(payload, dict) and "_study_material_binding" in payload:
                result.output = {key: value for key, value in payload.items() if key != "_study_material_binding"}
        if result.images:''')

EVENT = '''        if (event_type == "proactive_message" and isinstance(event.get("metadata"), dict)
                and "study_material_control" in event["metadata"]):
            # Routing provenance is derived by the plugin bridge, never by model text.
            if (event.get("source_kind") == "plugin" and event.get("source_name") == "study_companion"
                    and event.get("channel") == "plugin:study_companion"
                    and event.get("ai_behavior") == "blind" and event.get("visibility") == []
                    and isinstance(lanlan, str) and lanlan.strip()):
                manager = _get_session_manager(lanlan)
                if manager is not None:
                    await manager._apply_study_material_control(event["metadata"]["study_material_control"])
            return # A rejected control is never injected as conversation or broadcast.

'''

UPGRADES = {
    'main_logic/core/tts_lifecycle.py': (
        ('    def _tts_output_is_current(self):\n        return self._tts_runtime_is_current(tts_output_runtime.get())',
         '    def _tts_output_is_current(self):\n'
         '        if self._study_material_native_output_held():\n            return False\n'
         '        return self._tts_runtime_is_current(tts_output_runtime.get())'),
    ),
    'main_logic/omni_realtime_client/_tools.py': (
        ('        """Invalidate tool work from the turn that the new user turn replaces."""\n\n        self._advance_tool_scope()',
         '        """Invalidate tool work from the turn that the new user turn replaces."""\n\n'
         '        self._study_material_user_epoch = getattr(self, "_study_material_user_epoch", 0) + 1\n'
         '        self._advance_tool_scope()'),
    ),
    'main_logic/core/tool_calling.py': (
        ('    def _make_tool_call_handler(self, session):', HELPERS + '    def _make_tool_call_handler(self, session):'),
        ('        result = await self.tool_registry.execute(call)\n        if result.images:',
         _EXECUTE),
    ),
    'app/main_server/character_runtime.py': (
        ('        if event_type == "plugin_card":', EVENT + '        if event_type == "plugin_card":'),
    ),
}

def upgrade_targets(targets):
    return _upgrade_targets(targets, UPGRADES,
        [('main_logic/core/tool_calling.py', _EXECUTE_PRIOR, _EXECUTE),
         ('main_logic/core/tool_calling.py', _EXECUTE_ROUTED_PRIOR, _EXECUTE),
         ('main_logic/core/tool_calling.py', _EXECUTE_CURRENT_PRIOR, _EXECUTE)])

def normalize_material_audio(text):
    """Upgrade only the exact locally deployed first draft; reject unknown edits."""
    if HELPERS in text or '    def _valid_study_material_record' not in text:
        return text
    start = text.index('    @staticmethod\n    def _valid_study_material_record')
    end = text.index('    def _make_tool_call_handler', start)
    old = text[start:end]
    digest = __import__('hashlib').sha256(old.encode()).hexdigest()
    if digest not in {'eb6d593cece24b9bef57e2429d3bfb30807e6be56c4a8d7eaf01c32e9781e979',
                      '50bf4784d64b2a634f25ad7bc6ead997457d838faa0c095a1ea97be73a44b309',
                      'f0bce743af91f02f33cb70797e17e324770cd41026bb08adb53da6b4be0a7a9c',
                      '0abcfcddf6079a9f0d8966d46defad53170313676faa4d1d03a4e775696c54ed'}:
        raise RuntimeError('unknown material audio helper draft; preserve source')
    return text[:start] + HELPERS + text[end:]
