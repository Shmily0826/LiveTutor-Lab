"""Own one sealed native audio submission through the existing response lane."""
from neko_native_barge_in_patch import _upgrade_targets

ITEM_DRIVEN = '''        item_driven = bool(
            self._protocol_capabilities.responds_to_conversation_items
            and queued.events_before_response
            and all(
                event.get("type") == "conversation.item.create"
                and isinstance(event.get("item"), dict)
                and (
                    event["item"].get("type") == "function_call_output"
                    or (
                        event["item"].get("type") == "message"
                        and event["item"].get("role") == "user"
                    )
                )
                for event in queued.events_before_response
            )
        )'''

UPGRADES = {'main_logic/omni_realtime_client/_response_arbiter.py': (
    ('    item_driven: bool = field(default=False, compare=False)\n',
     '    item_driven: bool = field(default=False, compare=False)\n'
     '    automatic_audio: bool = field(default=False, compare=False)\n'
     '    native_input_sequence: int | None = field(default=None, compare=False)\n'),
    ('        pre_commit: Callable[[dict[str, Any]], None] | None = None,\n    ) -> ResponseTicket:',
     '        pre_commit: Callable[[dict[str, Any]], None] | None = None,\n'
     '        automatic_audio: bool = False,\n'
     '        native_input_sequence: int | None = None,\n    ) -> ResponseTicket:'),
    ('        loop = asyncio.get_running_loop()\n        ticket = ResponseTicket(',
     '        if (type(automatic_audio) is not bool or (not automatic_audio and native_input_sequence is not None)\n'
     '                or (automatic_audio and (type(native_input_sequence) is not int or native_input_sequence <= 0\n'
     '                or source != "native_phrase" or response_event is not None or ack_expected or pre_commit is not None\n'
     '                or self._protocol_capabilities.route_key != "lanlan_app_gemini"\n'
     '                or not self._protocol_capabilities.accepts_id_bearing_content_start\n'
     '                or not events_before_response or any(not isinstance(event, dict)\n'
     '                    or event.get("type") != "input_audio_buffer.append"\n'
     '                    or not isinstance(event.get("audio"), str) or not event["audio"]\n'
     '                    for event in events_before_response)))):\n'
     '            raise ValueError("automatic audio requires the explicit native phrase route and PCM events")\n'
     '        loop = asyncio.get_running_loop()\n        ticket = ResponseTicket('),
    ('            pre_commit=pre_commit,\n            event_ids=frozenset(ids),',
     '            pre_commit=pre_commit,\n            automatic_audio=automatic_audio,\n'
     '            native_input_sequence=native_input_sequence,\n            event_ids=frozenset(ids),'),
    ('        item_acked = not queued.ack_expected\n',
     '        item_acked = not queued.ack_expected and not queued.automatic_audio\n'),
    ('        owner_was_unannounced = bool(\n',
     '        if (owner is not None and owner.automatic_audio\n'
     '                and (owner.response_id is None or self._event_response_id(event) != owner.response_id)):\n'
     '            return False  # Neither terminal-only nor id-less events prove this native response.\n'
     '        owner_was_unannounced = bool(\n'),
    ('                owner.terminal_error = terminal_error\n',
     '                if owner.automatic_audio and response_status not in {"completed", "success", "succeeded"}:\n'
     '                    terminal_error = RuntimeError("native audio response did not complete successfully")\n'
     '                owner.terminal_error = terminal_error\n'),
    (ITEM_DRIVEN, ITEM_DRIVEN.replace('        item_driven = bool(\n',
        '        # Both modes generate from their real pre-events; neither sends response.create.\n'
        '        item_driven = bool(queued.automatic_audio or (\n').removesuffix('        )')+'        ))'),
    ('    @property\n    def has_live_response(self) -> bool:',
     '    def native_input_sequence_for(self, response_id):\n'
     '        owner = self._response_owner\n'
     '        if (owner is not None and owner is self._current and owner.automatic_audio and not owner.interrupted\n'
     '                and owner.response_id is not None and owner.response_id == _response_id_text(response_id)\n'
     '                and owner.ticket.started.done() and not owner.ticket.started.cancelled()\n'
     '                and owner.ticket.started.exception() is None):\n'
     '            return owner.native_input_sequence\n'
     '        return None\n\n'
     '    @property\n    def has_live_response(self) -> bool:'),
),
 'main_logic/omni_realtime_client/_transport.py': (
    ('        if not self._has_server_vad and step_timeout is None:\n',
     '        # Native phrase input is retired only by its fully-written successful ticket.\n'
     '        if (not self._has_server_vad and step_timeout is None\n'
     '                and getattr(self, "_current_response_source", None) != "native_phrase"):\n'),
    ('        self._voice_handoff_response_input_sequence = getattr(\n'
     '            self,\n            "_voice_handoff_input_sequence",\n            0,\n        )',
     '        if self._current_response_source == "native_phrase":\n'
     '            bound_sequence = arbiter.native_input_sequence_for(response_id)\n'
     '            self._voice_handoff_response_input_sequence = (bound_sequence\n'
     '                if type(bound_sequence) is int and bound_sequence > 0 else 0)\n'
     '        else:\n'
     '            self._voice_handoff_response_input_sequence = getattr(\n'
     '                self, "_voice_handoff_input_sequence", 0)\n'),
 )}


def upgrade_targets(targets, replay):
    targets, added = _upgrade_targets(targets, UPGRADES, [])
    final=[]
    for relative,old,new in replay:
        for before,after in UPGRADES.get(relative,()):new=new.replace(before,after)
        final.append((relative,old,new))
    return targets, added+tuple(final)
