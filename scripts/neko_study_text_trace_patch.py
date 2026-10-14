"""Opt-in, content-free diagnostics of the existing Study voice relay.

Lengths and UTF8 digests are observations, never delivery ACKs or permissions.
"""
from neko_native_barge_in_patch import _upgrade_targets

WIRE_HELPER = '''    def record_study_text(self, stage, text, *, generation=None, response_id=None,
                          cumulative=False, scope=None, token=None):
        # This recorder exists only on the existing opt-in wire-trace client.
        try:
            if stage not in ("grade_reply", "relay_write", "provider_delta", "provider_done",
                             "omni_callback", "core_entry", "core_queue", "core_ws") or not isinstance(text, str):
                return
            raw = text.encode("utf-8")
            digest = __import__("hashlib").sha256
            record = {"stage": stage, "t": trace_now(), "mono": round(time.monotonic(), 6),
                      "cid": self._client_tag, "chars": len(text), "utf8_bytes": len(raw),
                      "sha256": digest(raw).hexdigest(), "gen": _scalar(generation),
                      "response_id": _scalar(response_id), "scope": _scalar(scope), "token": _scalar(token)}
            if cumulative:
                streams = getattr(self, "_study_text_streams", None)
                if streams is None:
                    streams = self._study_text_streams = {}
                key = (stage, generation, response_id, scope, token)
                # Missing identity or exhausted capacity cannot start a false prefix.
                identity = (type(generation) is int and generation > 0
                            and isinstance(response_id, str) and 0 < len(response_id) <= 160)
                if identity and (key in streams or len(streams) < 64):
                    state = streams.setdefault(key, [digest(), 0, 0])
                    state[0].update(raw); state[1] += len(text); state[2] += 1
                    record.update(stream_chars=state[1], stream_chunks=state[2],
                                  stream_sha256=state[0].hexdigest(), cumulative_available=True)
                else:
                    record["cumulative_available"] = False
            self._logger.info("[study-text] %s", trace_json(record))
        except Exception:
            return # Diagnostics cannot change output, ownership or exception handling.

    def record_study_relay_write(self, payload, *, generation=None):
        try:
            event = json.loads(payload)
            item = event.get("item") or {}
            content = item.get("content") or []
            if (event.get("type") != "conversation.item.create" or item.get("role") != "user"
                    or len(content) != 1 or content[0].get("type") != "input_text"):
                return
            text = content[0].get("text", "")
            prefix = "[Authoritative Study result; do not regrade or ask a question.]\\n"
            if not isinstance(text, str) or not text.startswith(prefix):
                return
            result = json.loads(text[len(prefix):])
            self.record_study_text("relay_write", result.get("reply"), generation=generation)
            raw = payload.encode("utf-8") if isinstance(payload, str) else payload
            self._logger.info("[study-text] %s", trace_json({"stage": "relay_envelope_write",
                "cid": self._client_tag, "gen": _scalar(generation), "t": trace_now(),
                "bytes": len(raw), "sha256": __import__("hashlib").sha256(raw).hexdigest(),
                "delivery": "local_socket_write_only"}))
        except Exception:
            return

'''


def _core_context(indent=8):
    space=' '*indent
    return (space+'study_text_source = getattr(self, "session", None)\n'
        +space+'study_text_trace = getattr(getattr(study_text_source, "_wire_trace", None), "record_study_text", None)\n'
        +space+'study_text_identity = dict(generation=getattr(study_text_source, "_connection_generation", None),\n'
        +space+'    response_id=getattr(study_text_source, "_current_response_id", None), cumulative=True,\n'
        +space+'    scope=getattr(study_text_source, "_tool_scope_generation", None),\n'
        +space+'    token=getattr(study_text_source, "_native_output_connection_token", None))\n')


def _core_trace(stage, text, indent=8):
    space=' '*indent
    return (space+'if callable(study_text_trace):\n'
        +space+f'    study_text_trace("{stage}", {text}, **study_text_identity)\n')


def _omni_trace(text, indent):
    space=' '*indent
    return (space+'trace = getattr(getattr(self, "_wire_trace", None), "record_study_text", None)\n'
        +space+'if callable(trace):\n'
        +space+f'    trace("omni_callback", {text}, generation=getattr(self, "_connection_generation", None),\n'
        +space+'          response_id=getattr(self, "_current_response_id", None), cumulative=True,\n'
        +space+'          scope=getattr(self, "_tool_scope_generation", None),\n'
        +space+'          token=getattr(self, "_native_output_connection_token", None))\n')


UPGRADES = {
 'main_logic/omni_realtime_client/_wire_trace.py': (
    ('    def record_send(\n', WIRE_HELPER+'    def record_send(\n'),
    ('            event_type = event.get("type")\n',
     '            event_type = event.get("type")\n'
     '            if event_type in ("response.audio_transcript.delta", "response.output_audio_transcript.delta"):\n'
     '                self.record_study_text("provider_delta", event.get("delta"), generation=generation,\n'
     '                    response_id=event.get("response_id"), cumulative=True)\n'
     '            elif event_type in ("response.audio_transcript.done", "response.output_audio_transcript.done"):\n'
     '                self.record_study_text("provider_done", event.get("transcript"), generation=generation,\n'
     '                    response_id=event.get("response_id"))\n'),
    ('instructions, tool arguments and outputs, audio and image payloads, and\ncredentials are never read.',
     'instructions, tool arguments and outputs, audio and image payloads, and\ncredentials are never logged. Study text is transiently hashed by the explicit\nrecord_study_text diagnostic; only length and UTF8 digest are logged.'),
 ),
 'main_logic/omni_realtime_client/_transport.py': (
    ('                await transport.send(payload)\n',
     '                await transport.send(payload)\n'
     '                trace_relay = getattr(wire_trace, "record_study_relay_write", None)\n'
     '                if callable(trace_relay) and event.get("type") == "conversation.item.create":\n'
     '                    trace_relay(payload, generation=trace_generation)\n'),
    *tuple(('\n'+(' '*indent)+f'await self.on_output_transcript({args})\n',
            '\n'+_omni_trace(text,indent)+(' '*indent)+f'await self.on_output_transcript({args})\n')
        for indent,args,text in (
            (8,'text, is_first','text'),
            (24,'self._output_transcript_buffer, self._is_first_transcript_chunk','self._output_transcript_buffer'),
            (32,'transcript, True','transcript'),
            (36,'self._output_transcript_buffer, self._is_first_transcript_chunk','self._output_transcript_buffer'),
            (32,'delta, self._is_first_transcript_chunk','delta'))),
 ),
 'main_logic/core/turn.py': (
    ('        if self._takeover_active:\n            logger.info("[%s] session takeover active: dropping ordinary realtime output transcript',
     _core_context()+_core_trace('core_entry','text')+'        if self._takeover_active:\n            logger.info("[%s] session takeover active: dropping ordinary realtime output transcript'),
    ("        text_clean = self.emotion_pattern.sub('', text)\n",
     _core_context()+"        text_clean = self.emotion_pattern.sub('', text)\n"),
    ('        self.sync_message_queue.put({"type": "json", "data": message})\n',
     '        self.sync_message_queue.put({"type": "json", "data": message})\n'+_core_trace('core_queue','text_clean')),
    ('                    await self.websocket.send_json(message)\n                    return True\n',
     '                    await self.websocket.send_json(message)\n'+_core_trace('core_ws','text_clean',20)+'                    return True\n'),
 ),
 'main_logic/core/tool_calling.py': (
    ('        logger.info("[study-grade-event] %s", __import__("json").dumps(value, ensure_ascii=True))\n',
     '        logger.info("[study-grade-event] %s", __import__("json").dumps(value, ensure_ascii=True))\n'
     '        trace = getattr(getattr(source, "_wire_trace", None), "record_study_text", None)\n'
     '        if stage == "grade_complete" and callable(trace):\n'
     '            trace("grade_reply", result.get("reply"), generation=source._connection_generation,\n'
     '                  scope=getattr(source, "_tool_scope_generation", None),\n'
     '                  token=getattr(source, "_native_output_connection_token", None))\n'),
 ),
}


def upgrade_targets(targets, replay):
    targets, added = _upgrade_targets(targets, UPGRADES, [])
    final=[]
    for relative,old,new in replay:
        for before,after in UPGRADES.get(relative,()):new=new.replace(before,after)
        final.append((relative,old,new))
    return targets, added+tuple(final)
