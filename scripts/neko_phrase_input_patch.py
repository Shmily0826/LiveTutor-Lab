"""Default-OFF native phrase input; exact replay onto both actual host trees."""
from neko_native_barge_in_patch import _upgrade_targets

CORE_HELPERS = '''    def _native_phrase_input_authority(self, session):
        # This callback is bound to the exact installed Core session, not a game route.
        record = self._connection_record(session)
        if (session is not self.session or record is None or record.retired
                or not self.is_active or self._asr_route_mode != "native"
                or self._voice_lease_owner != "core" or self._takeover_active
                or self.session_closed_by_server or self.websocket is None or not self._voice_input_accepts_pcm()
                or getattr(session, "_fatal_error_occurred", False)
                or getattr(session, "ws", None) is None):
            return None
        generation = getattr(session, "_connection_generation", None)
        if type(generation) is not int or generation <= 0:
            return None
        activation = self._capture_voice_session_activation_generation()
        ingress = self._capture_native_ingress_token()
        return (activation.session_id, (ingress, activation, self.websocket), generation)

    def _native_phrase_transport_written(self, session, count, authority):
        if (type(count) is not int or count <= 0
                or self._native_phrase_input_authority(session) != authority):
            return False
        self._record_omni_microphone_audio(count)
        return True

'''

TRANSPORT_HELPERS = '''    def _native_phrase_mode_allowed(self):
        route = getattr(getattr(self, "_realtime_protocol_capabilities", None), "route_key", None)
        return bool(getattr(self, "_native_phrase_input_enabled", False)
                    and route == "lanlan_app_gemini" and self._is_free_proxy
                    and not self._has_server_vad and not self._is_gemini)

    def _native_phrase_driver(self):
        driver = getattr(self, "_native_phrase_uplink", None)
        if driver is None:
            from neko_phrase_input_transport import NativePhraseUplink
            driver = self._native_phrase_uplink = NativePhraseUplink(self)
        return driver

    def _native_phrase_protects_input(self):
        driver = getattr(self, "_native_phrase_uplink", None)
        return bool(driver is not None and driver.protect_clear())

    def _retire_native_phrase_input(self):
        driver = getattr(self, "_native_phrase_uplink", None)
        if driver is not None:
            driver.retire()

'''

UPGRADES = {
    'main_logic/core/session_lifecycle.py': (
        ('    def _bind_owned_output_callbacks(self, session):', CORE_HELPERS + '    def _bind_owned_output_callbacks(self, session):'),
        ('            session.get_native_barge_in_generation = self._capture_voice_session_activation_generation',
         '''            session.get_native_barge_in_generation = self._capture_voice_session_activation_generation
            import os
            session._native_phrase_input_enabled = os.environ.get("NEKO_EXPERIMENTAL_PHRASE_INPUT") == "1"
            session.get_native_phrase_input_authority = partial(self._native_phrase_input_authority, session)
            session.on_native_phrase_transport_written = partial(self._native_phrase_transport_written, session)'''),
    ),
    'main_logic/core/asr_runtime.py': (
        ('                    if require_output_commit:\n                        written = await stream_audio(',
         '''                    phrase_frame = (session_ref._native_phrase_mode_allowed()
                                    and not getattr(self, "is_flushing_hot_swap_cache", False))
                    effective_output_commit = (require_output_commit or phrase_frame
                                               or getattr(session_ref, "_native_phrase_uplink", None) is not None)
                    if effective_output_commit:
                        written = await stream_audio('''),
        ('                            require_output_commit=True,\n                        )\n                    else:\n                        await stream_audio(',
         '''                            require_output_commit=True,
                            _native_phrase_single_frame=phrase_frame,
                        )
                    else:
                        await stream_audio('''),
        ('                else:\n                    await stream_audio(pcm16)\n                    written = None',
         '''                else:
                    await stream_audio(pcm16)
                    written = None
                    effective_output_commit = require_output_commit'''),
        ('                if require_output_commit and written is False:',
         '                if effective_output_commit and written is False:'),
        ('                if require_output_commit and written is None:\n                    return OutputCommit.LOCAL_ACCEPTED',
         '                if effective_output_commit and written is None:\n                    return OutputCommit.LOCAL_ACCEPTED'),
    ),
    'main_logic/omni_realtime_client/_transport.py': (
        ('    def _trace_local_playback_owner(self) -> None:',
         TRANSPORT_HELPERS + '    def _trace_local_playback_owner(self) -> None:'),
        ('        _native_barge_in_replay: bool = False,\n    ) -> bool | None:',
         '        _native_barge_in_replay: bool = False,\n        _native_phrase_single_frame: bool = False,\n    ) -> bool | None:'),
        ('        # 检查是否已发生致命错误，如果是则直接返回\n        if not _native_barge_in_replay and self._capture_native_barge_in_pcm(',
         '''        phrase_driver = self._native_phrase_driver() if self._native_phrase_mode_allowed() else None
        if phrase_driver is None:
            previous_driver = getattr(self, "_native_phrase_uplink", None)
            if previous_driver is not None:
                if previous_driver.buffer is not None or previous_driver.writer is not None or previous_driver.preroll:
                    previous_driver.fail("phrase_route_changed_with_unsent_input")
                    return False if require_output_commit else None
                previous_driver.retire()
        phrase_bypass = True
        if phrase_driver is not None:
            phrase_bypass = phrase_driver.bypass_frame(
                replay=_native_barge_in_replay, single_frame=_native_phrase_single_frame,
                speech=speech_active, arrival=captured_at if captured_at is not None else time.time())
        # 检查是否已发生致命错误，如果是则直接返回
        if not _native_barge_in_replay and self._capture_native_barge_in_pcm('''),
        ('            if self._should_clear_audio_buffer_on_silence(\n                audio_timeline_at,',
         '            if not self._native_phrase_protects_input() and self._should_clear_audio_buffer_on_silence(\n                audio_timeline_at,'),
        ('            if getattr(self, "_native_barge_in_pending", False) and not _native_barge_in_replay:\n                return None',
         '''            if getattr(self, "_native_barge_in_pending", False) and not _native_barge_in_replay:
                if phrase_driver is not None:
                    phrase_driver.retire()
                    phrase_driver.bypass = True
                    phrase_driver.bypass_loud_at = audio_timeline_at
                return None'''),
        ('            # Gemini uses different API (16kHz, no uplink resample needed)',
         '''            # Actual DSP, local onset and pending-handoff decision have already run.
            if phrase_driver is not None and not phrase_bypass:
                accepted = phrase_driver.accept(audio_chunk, speech_active, audio_timeline_at)
                return None if accepted else False

            # Gemini uses different API (16kHz, no uplink resample needed)'''),
        ('        self._connection_generation += 1\n        self._native_output_connection_token =',
         '''        self._retire_native_phrase_input()
        driver = getattr(self, "_native_phrase_uplink", None)
        if driver is not None:
            driver.bypass = bool(getattr(self, "_native_barge_in_pending", False))
        self._connection_generation += 1
        self._native_output_connection_token ='''),
        ('            self._voice_handoff_input_open = False\n\n    def can_handoff_voice_input',
         '''            self._voice_handoff_input_open = False
            driver = getattr(self, "_native_phrase_uplink", None)
            if driver is not None:
                driver.note_boundary(expected_sequence)

    def can_handoff_voice_input'''),
        ('        self._fatal_error_occurred = True\n        await self._own_teardown(',
         '        self._fatal_error_occurred = True\n        self._retire_native_phrase_input()\n        await self._own_teardown('),
        ('        """Close the WebSocket connection."""\n        # Before the teardown,',
         '        """Close the WebSocket connection."""\n        self._retire_native_phrase_input()\n        # Before the teardown,'),
    ),
    'main_logic/omni_realtime_client/_audio.py': (
        ('        """Send an input_audio_buffer.clear event to clear the server-side buffer."""\n        self._input_route_identity = None',
         '''        """Send an input_audio_buffer.clear event to clear the server-side buffer."""
        if self._native_phrase_protects_input():
            return False  # A local silence reset cannot consume pending owned phrase PCM.
        self._input_route_identity = None'''),
    ),
}


MIGRATIONS = [
    ('main_logic/core/asr_runtime.py',
     '''                    phrase_frame = session_ref._native_phrase_mode_allowed()
                    effective_output_commit = require_output_commit or phrase_frame''',
     '''                    phrase_frame = (session_ref._native_phrase_mode_allowed()
                                    and not getattr(self, "is_flushing_hot_swap_cache", False))
                    effective_output_commit = (require_output_commit or phrase_frame
                                               or getattr(session_ref, "_native_phrase_uplink", None) is not None)'''),
    ('main_logic/omni_realtime_client/_transport.py',
     '''        phrase_driver = self._native_phrase_driver() if self._native_phrase_mode_allowed() else None
        phrase_bypass = True''',
     '''        phrase_driver = self._native_phrase_driver() if self._native_phrase_mode_allowed() else None
        if phrase_driver is None:
            previous_driver = getattr(self, "_native_phrase_uplink", None)
            if previous_driver is not None:
                if previous_driver.buffer is not None or previous_driver.writer is not None or previous_driver.preroll:
                    previous_driver.fail("phrase_route_changed_with_unsent_input")
                    return False if require_output_commit else None
                previous_driver.retire()
        phrase_bypass = True'''),
    ('main_logic/omni_realtime_client/_transport.py',
     '''            if previous_driver is not None and (previous_driver.buffer is not None or previous_driver.writer is not None):
                previous_driver.fail("phrase_route_changed_with_unsent_input")
                return False if require_output_commit else None''',
     '''            if previous_driver is not None:
                if previous_driver.buffer is not None or previous_driver.writer is not None or previous_driver.preroll:
                    previous_driver.fail("phrase_route_changed_with_unsent_input")
                    return False if require_output_commit else None
                previous_driver.retire()'''),
]


def upgrade_targets(targets):
    return _upgrade_targets(targets, UPGRADES, list(MIGRATIONS))


def normalize_phrase_helpers(text):
    marker = '    def _native_phrase_input_authority'
    if marker not in text:
        return text
    if text.count(marker) != 1 or text.count('    def _bind_owned_output_callbacks') != 1:
        raise RuntimeError('duplicate phrase input authority; preserve source')
    start = text.index(marker)
    end = text.index('    def _bind_owned_output_callbacks', start)
    prior = text[start:end]
    if prior == CORE_HELPERS:
        return text
    digest = __import__('hashlib').sha256(prior.encode()).hexdigest()
    if digest != 'd6677dfb14df23cb6be7cdafb216831ac316ab47e990f096ee697333633412c2':
        raise RuntimeError('unknown phrase input authority draft; preserve source')
    return text[:start] + CORE_HELPERS + text[end:]


_DELIVERY_BLOCK = '''            if getattr(self, "_native_barge_in_pending", False) and not _native_barge_in_replay:
                if phrase_driver is not None:
                    phrase_driver.retire()
                    phrase_driver.bypass = True
                    phrase_driver.bypass_loud_at = audio_timeline_at
                return None  # This frame is retained for the replacement, not written to A.

            # Actual DSP, local onset and pending-handoff decision have already run.
            if phrase_driver is not None and not phrase_bypass:
                accepted = phrase_driver.accept(audio_chunk, speech_active, audio_timeline_at)
                return None if accepted else False

'''


def normalize_phrase_transport(text):
    marker = '    def _native_phrase_mode_allowed'
    if marker not in text:
        return text
    if text.count(marker) != 1 or text.count(TRANSPORT_HELPERS) != 1:
        raise RuntimeError('unknown or duplicate phrase transport helper; preserve source')
    canonical_anchor = '    def _trace_local_playback_owner(self) -> None:'
    if TRANSPORT_HELPERS + '    async def stream_audio(' in text:
        if text.count(canonical_anchor) != 1:
            raise RuntimeError('unknown phrase transport placement; preserve source')
        text = text.replace(TRANSPORT_HELPERS, '', 1).replace(canonical_anchor,
                TRANSPORT_HELPERS + canonical_anchor, 1)
    elif TRANSPORT_HELPERS + canonical_anchor not in text:
        raise RuntimeError('unknown phrase transport placement; preserve source')
    # Exact repeated local draft only, never a general duplicate remover.
    if text.count(_DELIVERY_BLOCK + _DELIVERY_BLOCK) == 1:
        text = text.replace(_DELIVERY_BLOCK + _DELIVERY_BLOCK, _DELIVERY_BLOCK, 1)
    if text.count('            # Actual DSP, local onset and pending-handoff decision have already run.') != 1 or text.count(_DELIVERY_BLOCK) != 1:
        raise RuntimeError('unknown or duplicate phrase admission draft; preserve source')
    return text
