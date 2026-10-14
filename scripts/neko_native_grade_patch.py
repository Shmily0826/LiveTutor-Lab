"""Explicit voice answers use Study grading and one controlled, PCM-free relay.

Opt-in until the actual provider/device acceptance is complete. No speech onset,
provider function-call ID, input replay, or current-question adoption is invented.
"""
from neko_native_barge_in_patch import _upgrade_targets

TRANSPORT_HELPERS = '''    def _capture_study_grade_pin(self, speech, arrival, *, replay=False):
        if __import__("os").environ.get("NEKO_STUDY_AUTO_GRADE") != "1":
            return
        reader = getattr(self, "get_study_question_pin", None)
        if not callable(reader):
            return
        if replay:
            # Replayed old input cannot acquire the question on a new connection.
            self._study_grade_pin = {"connection": self._connection_generation, "invalid": True}
            return
        if speech is not True:
            return
        saved = getattr(self, "_study_grade_pin", None)
        if saved is not None:
            if (saved["connection"] != self._connection_generation
                    or arrival - saved.get("last_speech", arrival) > 1.2):
                saved["invalid"] = True # Ambiguous overlapping inputs: no rebinding.
            saved["last_speech"] = arrival
            return
        authority_reader = getattr(self, "get_study_input_authority", None)
        authority = authority_reader() if callable(authority_reader) else None
        pin = reader()
        self._study_grade_pin = {"connection": self._connection_generation,
            "question": pin, "last_speech": arrival, "invalid": pin is None or authority is None,
            "authority": authority, "provider": self.ws,
            "token": getattr(self, "_native_output_connection_token", None),
            "scope": getattr(self, "_tool_scope_generation", 0), "scoped": False}

    def _advance_study_grade_ingress_scope(self):
        saved = getattr(self, "_study_grade_pin", None)
        if not saved or saved.get("invalid"): return
        if saved.get("scoped") or saved["scope"] != getattr(self, "_tool_scope_generation", 0):
            saved["invalid"] = True
            return
        # Only the protocol's actual user-turn boundary may advance this pin.
        saved["scope"] += 1
        saved["scoped"] = True

    def _take_study_grade_asr(self, provider, generation):
        if __import__("os").environ.get("NEKO_STUDY_AUTO_GRADE") != "1":
            return None
        saved = getattr(self, "_study_grade_pin", None)
        if saved is not None and not saved.get("invalid"):
            self._study_grade_pin = None
        # A poisoned slot stays poisoned until an actual connection replacement.
        reader = getattr(self, "get_study_input_authority", None)
        authority = reader() if callable(reader) else None
        binding_current = bool(saved and saved["connection"] == generation
                and provider is self.ws and generation == self._connection_generation
                and saved.get("provider") is provider
                and saved.get("scope") == getattr(self, "_tool_scope_generation", 0)
                and saved.get("token") == getattr(self, "_native_output_connection_token", None)
                and authority is not None and saved.get("authority") == authority)
        if (not saved or saved.get("invalid") or saved["connection"] != generation
                or provider is not self.ws or generation != self._connection_generation
                or saved.get("provider") is not provider
                or saved.get("scope") != getattr(self, "_tool_scope_generation", 0)
                or saved.get("token") != getattr(self, "_native_output_connection_token", None)
                or authority is None or saved.get("authority") != authority):
            pin = None
        else:
            pin = saved.get("question")
        owner = self._capture_tool_task_owner(provider, connection_generation=generation)
        owner = __import__("dataclasses").replace(owner, turn_pair_fence_applies=False)
        return {"client": self, "owner": owner, "pin": pin,
                "token": getattr(self, "_native_output_connection_token", None),
                "frames": getattr(self, "_voice_handoff_input_sequence", 0),
                "input_authority": authority if binding_current else None}

'''

CORE_HELPERS = '''    def _read_study_question_pin(self, source):
        if (os.environ.get("NEKO_STUDY_AUTO_GRADE") != "1" or source is not self.session
                or not self.is_active or self._takeover_active or getattr(self, "use_tts", False)
                or not getattr(source, "_is_free_proxy", False)):
            return None
        from neko_study_answer_intent import read_question_pin
        runtime = os.environ.get("NEKO_STORAGE_SELECTED_ROOT", "")
        return read_question_pin(runtime) if runtime else None

    def _study_input_authority(self, source):
        if source is not self.session or not self.is_active or self._takeover_active:
            return None
        return (self._capture_voice_session_activation_generation(), self.websocket)

    def _make_study_input_handler(self, source):
        async def accepted(transcript, *, source_game_route_identity=None, study_input_owner=None):
            if source is not self.session:
                return False
            activation = self._capture_voice_session_activation_generation()
            return await self.handle_input_transcript(transcript,
                source_game_route_identity=source_game_route_identity,
                source_study_client=source, source_study_input=study_input_owner,
                source_study_activation=activation)
        return accepted

    def _study_grade_claim_current(self, claim, *, controlled=False):
        source = claim["client"]
        basic = (source is self.session and self.is_active and not self._takeover_active
            and not getattr(self, "use_tts", False) and self.websocket is claim["socket"]
            and self._capture_voice_session_activation_generation() == claim["activation"]
            and getattr(source, "_voice_handoff_input_sequence", 0) == claim["frames"]
            and getattr(self, "_study_grade_claim", None) is claim)
        if not basic:
            return False
        if controlled:
            return source._connection_generation == claim["controlled_connection"]
        return (source._tool_task_owner_is_current(claim["owner"])
            and getattr(source, "_native_output_connection_token", None) == claim["token"])

    def _study_grade_output_held(self):
        claim = getattr(self, "_study_grade_claim", None)
        source = getattr(self, "session", None)
        if not claim or claim.get("released") or source is not claim["client"]:
            return False
        # Keep free output muted on its physical connection until it is retired.
        return (source._connection_generation == claim.get("controlled_connection", claim["owner"].connection_generation)
            and getattr(source, "_tool_scope_generation", 0) == claim.get("controlled_scope", claim["owner"].scope_generation))

    def _start_study_grade_claim(self, transcript, source, receipt, activation):
        if (os.environ.get("NEKO_STUDY_AUTO_GRADE") != "1" or source is not self.session
                or not isinstance(receipt, dict) or receipt.get("client") is not source
                or self._capture_voice_session_activation_generation() != activation
                or self._takeover_active or not self.is_active or getattr(self, "use_tts", False)
                or not getattr(source, "_is_free_proxy", False)
                or receipt.get("frames") != getattr(source, "_voice_handoff_input_sequence", 0)
                or not str(receipt.get("token") or "").startswith("native_connection_")
                or receipt.get("token") != getattr(source, "_native_output_connection_token", None)):
            return False
        if receipt.get("input_authority") != self._study_input_authority(source):
            return False
        from neko_study_answer_intent import answer_intent
        intent = answer_intent(transcript)
        owner = receipt.get("owner")
        if not intent or owner is None or not source._tool_task_owner_is_current(owner):
            return False
        previous = getattr(self, "_study_grade_claim", None)
        if previous and previous["owner"] == owner:
            return True
        for name in ("study_session", "study_answer"):
            definition = self.tool_registry.get(name)
            if definition is None or definition.metadata.get("source") != "plugin:study_companion":
                return False
        claim = {**receipt, "activation": activation, "socket": self.websocket,
                 "intent": intent, "text": transcript, "released": False}
        self._study_grade_claim = claim
        # Return immediately; the provider receive loop must keep draining.
        task = source._create_tool_task(self._run_study_grade_claim(claim))
        claim["task"] = task
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        return True

    @staticmethod
    def _study_grade_payload(result):
        payload = result.output
        if isinstance(payload, str):
            try: payload = __import__("json").loads(payload)
            except (ValueError, TypeError): return None
        return payload if isinstance(payload, dict) and not result.is_error else None

    async def _run_study_grade_claim(self, claim):
        source = claim["client"]
        try:
            pin = claim.get("pin")
            if not pin or not self._study_grade_claim_current(claim):
                return await self._study_grade_notice(claim, "原题的输入身份无法确认，这次没有评分。")
            expected = {key: pin[key] for key in ("course_id", "session_id", "question_id", "attempt_id")}
            status = self._study_grade_payload(await self._on_tool_call(
                ToolCall(name="study_session", arguments={"action": "status"}), invoking_session=source))
            if not self._study_grade_claim_current(claim): return
            question = (status or {}).get("current_question") or {}
            actual = {**{key: question.get(key) for key in ("question_id", "attempt_id")},
                      **{key: (status or {}).get(key) for key in ("course_id", "session_id")}}
            state = "evaluated" if claim["intent"] == "correction" else "pending"
            if (actual != expected or (status or {}).get("question_state") != state
                    or pin["attempt_evaluated"] != (state == "evaluated")):
                return await self._study_grade_notice(claim, "题目或课程已变化，这次没有评分。")
            arguments = {"answer": claim["text"], "_expected_question": expected}
            if claim["intent"] == "correction":
                arguments["correction_of"] = {key: pin[key] for key in ("question_id", "attempt_id")}
            local_id = "local_study_grade_" + __import__("uuid").uuid4().hex
            claim["local_id"] = local_id
            result = await self._on_tool_call(ToolCall(name="study_answer", arguments=arguments,
                call_id=local_id), invoking_session=source, study_input_owner=claim["owner"])
            if not self._study_grade_claim_current(claim): return
            payload = self._study_grade_payload(result)
            if (not payload or payload.get("ok") is False or payload.get("degraded")
                    or payload.get("verdict") not in ("wrong", "partial", "correct")
                    or not payload.get("reply")):
                return await self._study_grade_notice(claim, "评分工具没有完成，这次没有确认成绩。")
            attempt = payload.get("attempt_id")
            if (payload.get("question_id") != pin["question_id"] or not attempt
                    or (claim["intent"] == "answer" and attempt != pin["attempt_id"])
                    or (claim["intent"] == "correction" and attempt == pin["attempt_id"])):
                return await self._study_grade_notice(claim, "成绩已返回，但题目身份无法确认，语音未发送。")
            claim["result"] = payload
            # A new controlled transition, not resurrection of the retired tool
            # owner. It uses no PCM replay and may perform only one connect.
            task = self._fire_task(self._relay_study_grade_once(claim))
            claim["relay_task"] = task
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning("[study-grade] failed kind=%s", type(error).__name__)
            await self._study_grade_notice(claim, "正式评分没有完成，请查看当前题目状态。")

    async def _study_grade_notice(self, claim, text, *, controlled=False):
        if self._study_grade_claim_current(claim, controlled=controlled):
            async with self._ensure_audio_frame_send_lock():
                if self._study_grade_claim_current(claim, controlled=controlled):
                    await claim["socket"].send_json({"type": "status", "message": text})

    async def _relay_study_grade_once(self, claim):
        source = claim["client"]
        old = claim["owner"].connection_generation
        locked = False
        cancelled = False
        written = False
        ticket = None
        try:
            async with asyncio.timeout(self._native_activation_reconnect_timeout_s + 10):
                await self._core_voice_session_swap_lock.acquire(); locked = True
                if not self._study_grade_claim_current(claim): return
                async with self._ensure_audio_frame_send_lock():
                    if not self._study_grade_claim_current(claim): return
                    source._interrupted = source._fatal_error_occurred = True
                    cancelled = True
                    claim["controlled_connection"] = old
                    claim["controlled_scope"] = claim["owner"].scope_generation
                    await claim["socket"].send_json({"type": "game_route_speech_cancel",
                        "sdk_speech_correlation_id": claim["token"]})
                if not self._study_grade_claim_current(claim): return
                claim["controlled_connection"] = old
                await source.close()
                if not self._study_grade_claim_current(claim, controlled=True): return
                claim["controlled_scope"] = getattr(source, "_tool_scope_generation", 0)
                if not await self._restart_message_handler_after_session_reconnect(source, start_listener=False):
                    raise RuntimeError("grade_listener_not_drained")
                if not self._study_grade_claim_current(claim, controlled=True): return
                try:
                    await source.connect(str(getattr(source, "instructions", "") or ""), native_audio=True)
                finally:
                    claim["controlled_connection"] = min(source._connection_generation, old + 1)
                if not self._study_grade_claim_current(claim, controlled=True): return
                claim["controlled_scope"] = getattr(source, "_tool_scope_generation", 0)
                if not await self._restart_message_handler_after_session_reconnect(source):
                    raise RuntimeError("grade_listener_not_restarted")
                if not self._study_grade_claim_current(claim, controlled=True): return
                deadline = asyncio.get_running_loop().time() + 1
                while getattr(source, "_native_output_connection_token", None) == claim["token"]:
                    if (not self._study_grade_claim_current(claim, controlled=True)
                            or asyncio.get_running_loop().time() >= deadline):
                        raise RuntimeError("grade_output_token_not_replaced")
                    await asyncio.sleep(.01)
                claim["relay_provider"] = source.ws
                claim["relay_token"] = source._native_output_connection_token
                claim["relay_scope"] = getattr(source, "_tool_scope_generation", 0)
                def current():
                    return (self._study_grade_claim_current(claim, controlled=True)
                        and source.ws is claim["relay_provider"]
                        and source._native_output_connection_token == claim["relay_token"]
                        and getattr(source, "_tool_scope_generation", 0) == claim["relay_scope"])
                status = self._study_grade_payload(await self._on_tool_call(
                    ToolCall(name="study_session", arguments={"action": "status"}), invoking_session=source))
                question = (status or {}).get("current_question") or {}
                if (not current() or question.get("question_id") != claim["result"]["question_id"]
                        or question.get("attempt_id") != claim["result"]["attempt_id"]
                        or (status or {}).get("course_id") != claim["pin"]["course_id"]
                        or (status or {}).get("session_id") != claim["pin"]["session_id"]
                        or (status or {}).get("question_state") != "evaluated"):
                    return
                async def send_owned(event):
                    if await source.send_event(event, send_guard=current) is not True:
                        raise ConnectionError("grade relay not written")
                def release(event):
                    if not current(): raise RuntimeError("grade relay owner replaced")
                    claim["released"] = True
                text = ("[Authoritative Study result; do not regrade or ask a question.]\\n"
                    + __import__("json").dumps({key: claim["result"].get(key) for key in
                        ("verdict", "score", "reply", "relay")}, ensure_ascii=False))
                arbiter = source._ensure_response_arbiter()
                ticket = await arbiter.enqueue(source="study_grade",
                    events_before_response=({"type": "conversation.item.create", "item": {
                        "type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}},),
                    response_event={"type": "response.create"}, event_sender=send_owned,
                    admission_check=current, pre_commit=release, priority=5)
                claim["ticket"] = ticket
                await asyncio.shield(ticket.sent)
                written = True
                claim["relay_written"] = True
                if not current(): await arbiter.cancel_ticket(ticket, wait=False)
        except asyncio.CancelledError:
            if ticket is not None:
                await asyncio.shield(source._ensure_response_arbiter().cancel_ticket(ticket, wait=False))
            raise
        except Exception as error:
            logger.warning("[study-grade] relay failed kind=%s", type(error).__name__)
            claim["released"] = False
            if ticket is not None:
                await source._ensure_response_arbiter().cancel_ticket(ticket, wait=False)
            await self._study_grade_notice(claim,
                "正式成绩已保存，但语音未完成：" + claim["result"]["reply"], controlled=cancelled)
        finally:
            if cancelled and not written and source is self.session:
                generation = source._connection_generation
                # The old physical queue was irrevocably retired. Close only
                # that dead connection, or our failed new one with no new input.
                if (generation == old or (generation == old + 1
                        and self._study_grade_claim_current(claim, controlled=True))):
                    try:
                        await asyncio.wait_for(source.close(), timeout=self._core_voice_listener_cancel_timeout_s)
                    except (Exception, asyncio.CancelledError):
                        pass
            if locked: self._core_voice_session_swap_lock.release()

'''

UPGRADES = {
 'main_logic/omni_realtime_client/_transport.py': (
    ('    async def _deliver_input_transcript(self, transcript: str, *, item_id: object = None) -> None:',
     TRANSPORT_HELPERS+'    async def _deliver_input_transcript(self, transcript: str, *, item_id: object = None, study_input_owner=None) -> None:'),
    ('                source_game_route_identity=identity,\n            )',
     '                source_game_route_identity=identity,\n                **({"study_input_owner": study_input_owner} if study_input_owner is not None else {}),\n            )'),
    ('        phrase_driver = self._native_phrase_driver() if self._native_phrase_mode_allowed() else None',
     '        self._capture_study_grade_pin(speech_active, captured_at if captured_at is not None else time.time(), replay=_native_barge_in_replay)\n'
     '        phrase_driver = self._native_phrase_driver() if self._native_phrase_mode_allowed() else None'),
    ('        # Serialize at the actual user-audio admission boundary, not inside the',
     '        if speech_active is None and (input_has_speech or (_rnnoise_vad_live and audio_processor.speech_probability > 0.4)):\n'
     '            # Legacy unscored DSP has no trustworthy pre-await pin yet.\n'
     '            # Refuse automatic grading instead of reading a newer question.\n'
     '            self._capture_study_grade_pin(True, audio_timeline_at, replay=True)\n\n'
     '        # Serialize at the actual user-audio admission boundary, not inside the'),
    ('                            item_id=event.get("item_id"),\n                        )\n                        if await retire_if_replaced():',
     '                            item_id=event.get("item_id"),\n'
     '                            study_input_owner=self._take_study_grade_asr(message_ws, message_generation),\n'
     '                        )\n                        if await retire_if_replaced():'),
    ('        self._native_audio = native_audio\n',
     '        self._native_audio = native_audio\n        self._study_grade_pin = None # Physical connection replacement retires ambiguous ingress.\n'),
    ('                elif event_type == "input_audio_buffer.speech_started":\n                    self.note_user_turn_started()',
     '                elif event_type == "input_audio_buffer.speech_started":\n                    self._advance_study_grade_ingress_scope()\n                    self.note_user_turn_started()'),
    ('                        self._late_raw_expected_asr_advance = True\n                        try:\n                            self.note_user_turn_started()',
     '                        self._late_raw_expected_asr_advance = True\n                        try:\n                            self._advance_study_grade_ingress_scope()\n                            self.note_user_turn_started()'),
 ),
 'main_logic/omni_realtime_client/_audio.py': (
    ('        await self.send_event({"type": "input_audio_buffer.clear"})',
     '        pin = getattr(self, "_study_grade_pin", None)\n        if pin is not None: pin["invalid"] = True\n'
     '        await self.send_event({"type": "input_audio_buffer.clear"})'),
 ),
 'main_logic/core/tool_calling.py': (
    ('        material_owner = self._capture_study_material_tool_owner(call, invoking_session)',
     '''        claim = getattr(self, "_study_grade_claim", None)
        relay_current = bool(claim and claim.get("relay_provider") is not None
            and self._study_grade_claim_current(claim, controlled=True)
            and invoking_session is claim["client"]
            and invoking_session.ws is claim["relay_provider"]
            and getattr(invoking_session, "_native_output_connection_token", None) == claim.get("relay_token")
            and getattr(invoking_session, "_tool_scope_generation", 0) == claim.get("relay_scope"))
        if (study_input_owner is None and claim and invoking_session is claim["client"]
                and call.name in ("study_answer", "study_explain", "study_quiz", "study_summary")
                and (self._study_grade_claim_current(claim) or relay_current)):
            if call.name != "study_answer":
                return ToolResult(call_id=call.call_id, name=call.name,
                    output={"ok":False,"error":"explicit_answer_is_being_graded"}, is_error=True)
            await asyncio.shield(claim["task"])
            if (not claim.get("result") or not (
                    self._study_grade_claim_current(claim) or (relay_current
                        and self._study_grade_claim_current(claim, controlled=True)
                        and invoking_session.ws is claim["relay_provider"]
                        and getattr(invoking_session, "_tool_scope_generation", 0) == claim.get("relay_scope")
                        and getattr(invoking_session, "_native_output_connection_token", None) == claim.get("relay_token")))):
                return ToolResult(call_id=call.call_id, name=call.name,
                    output={"ok":False,"error":"study_grade_unavailable"}, is_error=True)
            return ToolResult(call_id=call.call_id, name=call.name, output=claim["result"])
        material_owner = self._capture_study_material_tool_owner(call, invoking_session)'''),
    ('    def _register_builtin_tools(self) -> None:', CORE_HELPERS+'    def _register_builtin_tools(self) -> None:'),
    ('        invoking_session=None,\n    ) -> ToolResult:',
     '        invoking_session=None,\n        study_input_owner=None,\n    ) -> ToolResult:'),
    ('        dispatched_call = call\n',
     '        if material_owner is not None and study_input_owner is not None:\n'
     '            if not invoking_session._tool_task_owner_is_current(study_input_owner):\n'
     '                return ToolResult(call_id=call.call_id, name=call.name, output={"ok":False,"error":"stale_study_input"}, is_error=True)\n'
     '            material_owner["tool_owner"] = study_input_owner\n'
     '        dispatched_call = call\n'),
    ('    def _study_material_native_output_held(self):\n',
     '    def _study_material_native_output_held(self):\n        if self._study_grade_output_held(): return True\n'),
 ),
 'main_logic/core/session_lifecycle.py': (
    ('            session._native_phrase_input_enabled = os.environ.get("NEKO_EXPERIMENTAL_PHRASE_INPUT") == "1"',
     '            session._native_phrase_input_enabled = (os.environ.get("NEKO_EXPERIMENTAL_PHRASE_INPUT") == "1" or os.environ.get("NEKO_STUDY_AUTO_GRADE") == "1")'),
    ('        for name in (\n            "on_native_barge_in",',
     '        if hasattr(session, "_capture_tool_task_owner") and __import__("os").environ.get("NEKO_STUDY_AUTO_GRADE") == "1":\n'
     '            session.get_study_question_pin = partial(self._read_study_question_pin, session)\n'
     '            session.get_study_input_authority = partial(self._study_input_authority, session)\n'
     '            session.on_input_transcript_with_route = self._make_study_input_handler(session)\n'
     '        for name in (\n            "on_native_barge_in",'),
 ),
 'main_logic/core/turn.py': (
    ('        source_game_route_identity: Any = Ellipsis,\n    ):',
     '        source_game_route_identity: Any = Ellipsis,\n        source_study_client=None, source_study_input=None, source_study_activation=None,\n    ):'),
    ('        if is_voice_source and not voice_rms_recorded:\n',
     '        if is_voice_source and record_transcript_text:\n'
     '            self._start_study_grade_claim(transcript, source_study_client, source_study_input, source_study_activation)\n\n'
     '        if is_voice_source and not voice_rms_recorded:\n'),
    ('        """Qwen audio callback: push audio to the WebSocket frontend"""\n',
     '        """Qwen audio callback: push audio to the WebSocket frontend"""\n'
     '        if self._study_grade_output_held(): return\n'),
    ('        # 同 handle_text_data：proactive 路径设置的 sid',
     '        if self._study_grade_output_held(): return\n\n'
     '        # 同 handle_text_data：proactive 路径设置的 sid'),
 ),
}


def upgrade_targets(targets):
    return _upgrade_targets(targets, UPGRADES, [])
