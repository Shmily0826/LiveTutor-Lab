"""Replayable native-microphone handoff using N.E.K.O's bounded PCM and lifecycle.

The replacement connection is the output ownership boundary. No provider response
identity, new VAD, or replacement playback scheduler is assumed.
"""

TRANSPORT_HELPERS = '''    def _capture_native_barge_in_pcm(self, pcm, speech_active, captured_at):
        if not self._is_free_proxy or speech_active is None or not pcm:
            return False
        getter = getattr(self, "get_native_barge_in_generation", None)
        generation = getter() if callable(getter) else None
        if generation is None:
            return False
        from main_logic.voice_input.activation.buffer import BoundedAudioFrameBuffer
        from main_logic.voice_input.activation.contracts import AudioFrame
        from main_logic.voice_input.activation.controller import VoiceActivationConfig
        pending = getattr(self, "_native_barge_in_pending", False)
        if generation != getattr(self, "_native_barge_in_generation", None):
            if pending:
                self._native_barge_in_overflow = True
                return True
            config = VoiceActivationConfig()
            self._native_barge_in_buffer = BoundedAudioFrameBuffer(
                max_seconds=config.buffer_seconds, max_bytes=config.buffer_bytes,
            )
            self._native_barge_in_config = config
            self._native_barge_in_generation = generation
            self._native_barge_in_sequence = self._native_barge_in_samples = 0
            self._native_barge_in_candidate = None
            self._native_barge_in_last_voice = 0.0
            self._native_barge_in_replayed_candidate = None
        when = captured_at if isinstance(captured_at, (int, float)) and captured_at > 0 else time.time()
        sequence = self._native_barge_in_sequence
        start = self._native_barge_in_samples
        frame = AudioFrame(sequence, start, start + len(pcm) // 2, when,
                           16_000, pcm, generation, bool(speech_active))
        result = self._native_barge_in_buffer.append(frame)
        self._native_barge_in_sequence += 1
        self._native_barge_in_samples = frame.sample_end
        if pending and any(seq >= self._native_barge_in_cursor for seq in result.evicted_sequences):
            self._native_barge_in_overflow = True
        if speech_active:
            if (self._native_barge_in_candidate is None
                    or when - self._native_barge_in_last_voice > self._local_quiet_seconds):
                self._native_barge_in_candidate = sequence
            self._native_barge_in_last_voice = when
        return pending

    def _prepare_native_barge_in_replay(self):
        candidate = getattr(self, "_native_barge_in_candidate", None)
        if candidate is None or candidate == getattr(self, "_native_barge_in_replayed_candidate", None):
            return False
        self._native_barge_in_cursor = self._native_barge_in_buffer.replay_start_sequence(
            candidate, pre_roll_seconds=self._native_barge_in_config.pre_roll_seconds,
        )
        self._native_barge_in_overflow = False
        return True

'''

CORE_HELPERS = '''    def note_native_speech_playback_state(self, message, websocket):
        source = getattr(self, "session", None)
        token = getattr(source, "_native_output_connection_token", None)
        active = message.get("active")
        if (websocket is self.websocket and token
                and message.get("sdk_speech_correlation_id") == token
                and isinstance(active, bool)):
            source._native_playback_active = active
            source._native_playback_state_at = time.monotonic()

    async def _begin_native_barge_in_handoff(self, source):
        if (source is not self.session or not self.is_active
                or self._asr_route_mode != "native" or self._voice_lease_owner != "core"
                or self._takeover_active or not self._voice_input_accepts_pcm()):
            return False
        if self._game_speech_correlation_for(self.read_current_speech_id()):
            return False  # Game speech retains its existing request-owned cancellation contract.
        if getattr(source, "_native_barge_in_pending", False):
            return True
        generation = self._capture_voice_session_activation_generation()
        if generation != getattr(source, "_native_barge_in_generation", None):
            return False
        try:
            if not source._prepare_native_barge_in_replay():
                return False
        except Exception:
            # Incomplete pre-roll is reported as a failed handoff, never silently replayed.
            source._native_barge_in_overflow = True
        source._native_barge_in_pending = True
        source._native_barge_in_origin_connection = source._connection_generation
        source._interrupted = True
        source._fatal_error_occurred = True
        source._native_barge_in_task = asyncio.create_task(
            self._recover_native_barge_in(source, generation,
                source._connection_generation, source._native_output_connection_token,
                self.websocket),
        )
        return True

    async def _recover_native_barge_in(self, source, generation, old_connection, old_token, output_socket):
        lock = self._core_voice_session_swap_lock
        locked = False
        owned_connection = old_connection
        success = False

        def current():
            return bool(source is self.session and self.is_active
                and self.websocket is output_socket
                and self._asr_route_mode == "native" and self._voice_lease_owner == "core"
                and self._voice_input_accepts_pcm()
                and self._capture_voice_session_activation_generation() == generation)

        try:
            barrier = self._core_voice_session_swap_barrier_timeout_s
            close_timeout = self._core_voice_listener_cancel_timeout_s
            async with asyncio.timeout(self._native_activation_reconnect_timeout_s + barrier + close_timeout):
                await asyncio.wait_for(lock.acquire(), timeout=barrier)
                locked = True
                if not current() or source._connection_generation != old_connection:
                    return
                # The existing frame lock orders the stop after any old header/payload pair.
                async with self._ensure_audio_frame_send_lock():
                    if not current():
                        return
                    await output_socket.send_json({"type": "game_route_speech_cancel",
                        "sdk_speech_correlation_id": old_token})
                await asyncio.wait_for(source.close(), timeout=close_timeout)
                if not current():
                    return
                # Reuse Core's bounded listener cancellation/retirement without starting B yet.
                if not await self._restart_message_handler_after_session_reconnect(source, start_listener=False):
                    raise RuntimeError("native_barge_in_listener_not_drained")
                if source._native_barge_in_overflow:
                    raise RuntimeError("native_barge_in_pcm_incomplete")
                if not current():
                    return
                source._native_barge_in_reconnecting = True
                try:
                    await source.connect(str(getattr(source, "instructions", "") or ""), native_audio=True)
                finally:
                    source._native_barge_in_reconnecting = False
                    owned_connection = source._connection_generation
                if not current() or owned_connection <= old_connection:
                    raise RuntimeError("native_barge_in_connection_not_replaced")
                while True:
                    if not current() or source._connection_generation != owned_connection:
                        raise RuntimeError("native_barge_in_owner_replaced")
                    if source._native_barge_in_overflow:
                        raise RuntimeError("native_barge_in_pcm_incomplete")
                    buffer = source._native_barge_in_buffer
                    end = buffer.latest_sequence
                    cursor = source._native_barge_in_cursor
                    if end is None or cursor > end:
                        break
                    frames = buffer.get_range(cursor, end)
                    for frame in frames:
                        if not current() or source._connection_generation != owned_connection:
                            raise RuntimeError("native_barge_in_owner_replaced")
                        accepted = await source.stream_audio(frame.pcm, captured_at=frame.captured_at,
                            speech_active=frame.context, raise_on_error=True, require_output_commit=True,
                            _native_barge_in_replay=True)
                        if accepted is False:
                            raise RuntimeError("native_barge_in_replay_failed")
                        source._native_barge_in_cursor = frame.sequence + 1
                source._native_barge_in_replayed_candidate = source._native_barge_in_candidate
                source._native_barge_in_pending = False
                if not await self._restart_message_handler_after_session_reconnect(source):
                    raise RuntimeError("native_barge_in_listener_restart_failed")
                self.session_closed_by_server = False
                success = True
                logger.info("[native-barge-in] handoff complete connection=%d->%d",
                            old_connection, owned_connection)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("[native-barge-in] handoff failed kind=%s", type(exc).__name__)
        finally:
            if not success and source._connection_generation == owned_connection:
                source._interrupted = source._fatal_error_occurred = True
                try:
                    await asyncio.wait_for(source.close(), timeout=self._core_voice_listener_cancel_timeout_s)
                except (Exception, asyncio.CancelledError):
                    pass
            owns_task = getattr(source, "_native_barge_in_task", None) is asyncio.current_task()
            if owns_task:
                source._native_barge_in_pending = False
                source._native_barge_in_task = None
                if not success and source._connection_generation == owned_connection:
                    source._native_barge_in_buffer.clear()
            if locked:
                lock.release()
            if (not success and source is self.session and self.is_active
                    and source._connection_generation == owned_connection and owns_task):
                # Existing fail-closed UI path; no automatic reconnect loop or replay of partial PCM.
                await self.send_status(json.dumps({"code": "ASR_INPUT_DELIVERY_FAILED"}))
                await self.disconnected_by_server(expected_session=source, announce_disconnect=False)

'''

PLAYBACK_HELPERS = '''    // The physical provider connection is the ownership boundary for native handoff.
    var retiredNativeConnections = new Set();

    function cancelNativeConnectionPlayback(token) {
        if (typeof token !== 'string' || token.indexOf('native_connection_') !== 0) return;
        retiredNativeConnections.add(token);
        S.scheduledSources = S.scheduledSources.filter(function (source) {
            if (source._nekoSpeechCorrelationId !== token) return true;
            try { source.stop(); } catch (_) { /* already ended */ }
            releaseAssistantPlaybackGraph(source);
            return false;
        });
        S.audioBufferQueue = S.audioBufferQueue.filter(function (item) {
            return item.correlationId !== token;
        });
        S.incomingAudioBlobQueue = S.incomingAudioBlobQueue.filter(function (item) {
            return item.correlationId !== token;
        });
        // Keep header/blob pairing and all next-connection decoder/lifecycle state intact.
        if (!S.scheduledSources.length && S.audioPlayerContext) {
            S.nextChunkTime = S.audioPlayerContext.currentTime;
        }
        if (S.currentPlayingSpeechCorrelationId === token && !S.scheduledSources.length &&
            !S.audioBufferQueue.length && !S.incomingAudioBlobQueue.length) {
            S.isPlaying = false;
            stopActiveLipSync();
            publishSpeechPlaybackState('native_connection_cancel', {active: false});
        }
    }

'''

UPGRADES = {
    "main_logic/omni_realtime_client/_transport.py": (
        ("    def _trace_local_playback_owner(self) -> None:", TRANSPORT_HELPERS + "    def _trace_local_playback_owner(self) -> None:"),
        ('''        now = time.time()
        if now - getattr(self, "_ai_recent_activity_time", 0.0) > self._LOCAL_TALKING_WINDOW_SECONDS:''',
         '''        now = time.time()
        playback_at = getattr(self, "_native_playback_state_at", 0.0)
        if playback_at and time.monotonic() - playback_at <= self._LOCAL_TALKING_WINDOW_SECONDS:
            audible = getattr(self, "_native_playback_active", False)
        else:
            audible = now - getattr(self, "_ai_recent_activity_time", 0.0) <= self._LOCAL_TALKING_WINDOW_SECONDS
        if not audible:'''),
        ('''        if self._is_gemini:
            if self._interrupted:
                return
            self._local_onset_armed_at = now''',
         '''        native_handoff = getattr(self, "on_native_barge_in", None)
        if self._is_free_proxy and callable(native_handoff):
            if await native_handoff():
                logger.info("local speech onset (%s): isolating old native connection", evidence)
            return
        if self._is_gemini:
            if self._interrupted:
                return
            self._local_onset_armed_at = now'''),
        ('''        require_output_commit: bool = False,
    ) -> bool | None:''',
         '''        require_output_commit: bool = False,
        _native_barge_in_replay: bool = False,
    ) -> bool | None:'''),
        ('''        if self._fatal_error_occurred:
            return False if require_output_commit else None

        audio_timeline_at =''',
         '''        if not _native_barge_in_replay and self._capture_native_barge_in_pcm(
                audio_chunk, speech_active, captured_at):
            return False if self._native_barge_in_overflow else None
        if self._fatal_error_occurred:
            return False if require_output_commit else None

        audio_timeline_at ='''),
        ("        is_48khz = (num_samples == 480)  # RNNoise frame size",
         "        is_48khz = (num_samples == 480 and speech_active is None)  # Host-scored PCM is already 16 kHz."),
        ('''        if raw_loud:
            # Publish user engagement before waiting''',
         '''        input_has_speech = speech_active if speech_active is not None else raw_loud
        if input_has_speech:
            # Publish user engagement before waiting'''),
        ('''            elif raw_loud:
                # RMS is the only local onset signal''',
         '''            elif input_has_speech:
                # Host-scored PCM retains its speech verdict; other input uses RMS.
                # RMS is the only local onset signal'''),
        ('''                elif raw_loud:
                    self._client_vad_last_speech_time''',
         '''                elif input_has_speech:
                    self._client_vad_last_speech_time'''),
        ("            if not getattr(self, \"_speech_started_total\", 0):",
         "            if not _native_barge_in_replay and not getattr(self, \"_speech_started_total\", 0):"),
        ("            # 音频 buffer：有 RNNoise 用 RNNoise 统计，无则按 VAD + 连续静音判定",
         "            # 音频 buffer：有 RNNoise 用 RNNoise 统计，无则按 VAD + 连续静音判定"),
        ('''            # Gemini uses different API (16kHz, no uplink resample needed)''',
         '''            if getattr(self, "_native_barge_in_pending", False) and not _native_barge_in_replay:
                return None  # This frame is retained for the replacement, not written to A.

            # Gemini uses different API (16kHz, no uplink resample needed)'''),
        ('''        self._connection_generation += 1
        self._clear_input_route_identities()''',
         '''        self._connection_generation += 1
        self._native_output_connection_token = "native_connection_" + uuid.uuid4().hex
        self._native_playback_state_at = 0.0
        if (getattr(self, "_native_barge_in_pending", False) and
                (not getattr(self, "_native_barge_in_reconnecting", False) or
                 self._connection_generation != self._native_barge_in_origin_connection + 1)):
            self._native_barge_in_pending = False
            self._native_barge_in_overflow = True
            self._native_barge_in_buffer.clear()
            self._native_barge_in_candidate = None
        self._clear_input_route_identities()'''),
        ('''                if event_type == "session.updated":''',
         '''                if (getattr(self, "_native_barge_in_pending", False)
                        and message_generation == self._native_barge_in_origin_connection):
                    continue  # A's late transcript/output cannot enter the replacement turn.

                if event_type == "session.updated":'''),
        ('''                    already_scoped = self._raw_transcript_was_already_scoped(''',
         '''                    self._native_barge_in_candidate = None
                    already_scoped = self._raw_transcript_was_already_scoped('''),
    ),
    "main_logic/core/asr_runtime.py": (
        ("    async def _reconnect_native_voice_session_for_activation(", CORE_HELPERS + "    async def _reconnect_native_voice_session_for_activation("),
        ('''            if getattr(session_ref, "_fatal_error_occurred", False):
                # After an Omni fatal error''',
         '''            if (getattr(session_ref, "_fatal_error_occurred", False)
                    and not getattr(session_ref, "_native_barge_in_pending", False)):
                # After an Omni fatal error'''),
        ('''                if require_output_commit and written is False:
                    return OutputCommit.NOT_SENT
                if not native_send_is_current():''',
         '''                if require_output_commit and written is False:
                    return OutputCommit.NOT_SENT
                if getattr(session_ref, "_native_barge_in_pending", False):
                    return OutputCommit.LOCAL_ACCEPTED
                if not native_send_is_current():'''),
    ),
    "main_logic/core/session_lifecycle.py": (
        ("from functools import wraps", "from functools import partial, wraps"),
        ('''        for name in (
            "on_text_delta", "on_audio_delta", "on_audio_done", "on_new_message",''',
         '''        if hasattr(session, "_capture_native_barge_in_pcm"):
            session.on_native_barge_in = partial(self._begin_native_barge_in_handoff, session)
            session.get_native_barge_in_generation = self._capture_voice_session_activation_generation
        for name in (
            "on_native_barge_in",
            "on_text_delta", "on_audio_delta", "on_audio_done", "on_new_message",'''),
        ("        for name in ('get_host_turn_id', 'on_response_displaced', 'on_idle'):",
         "        for name in ('get_native_barge_in_generation', 'get_host_turn_id', 'on_response_displaced', 'on_idle'):"),
    ),
    "main_logic/core/lifecycle.py": (
        ('''        session_ref,
    ) -> bool:
        """Replace the receive task after an in-place Provider reconnect.''',
         '''        session_ref,
        *, start_listener: bool = True,
    ) -> bool:
        """Replace the receive task after an in-place Provider reconnect.'''),
        ('''            if not previous_task.cancelled():
                previous_task.exception()

        async with self.lock:''',
         '''            if not previous_task.cancelled():
                previous_task.exception()

        if not start_listener:
            return session_ref is self.session and self.is_active

        async with self.lock:'''),
    ),
    "main_logic/core/tts_runtime.py": (
        ('''        correlation_id = self._game_speech_correlation_for(effective_speech_id)
        if correlation_id:''',
         '''        correlation_id = self._game_speech_correlation_for(effective_speech_id)
        source = getattr(self, "session", None)
        if not correlation_id and getattr(source, "_is_free_proxy", False) and not self.use_tts:
            correlation_id = getattr(source, "_native_output_connection_token", "")
        if correlation_id:'''),
    ),
    "main_routers/websocket_router.py": (
        ('''                # Music playback ownership is also window-local:''',
         '''                if message.get("action") == "native_speech_playback_state":
                    session_manager[lanlan_name].note_native_speech_playback_state(message, websocket)
                    continue
                # Music playback ownership is also window-local:'''),
        ('''            action = message.get("action")

            if action == "voice_identity_control":''',
         '''            action = message.get("action")
            if action == "native_speech_playback_state":
                session_manager[lanlan_name].note_native_speech_playback_state(message, websocket)
                continue

            if action == "voice_identity_control":'''),
    ),
    "static/app/app-websocket.js": (
        ('''                    var speechCorrelationId = String(response.sdk_speech_correlation_id || '');''',
         '''                    var speechCorrelationId = String(response.sdk_speech_correlation_id || '');'''),
        ('''                        playbackGain: playbackGain,
                        epoch: S.incomingAudioEpoch,''',
         '''                        playbackGain: playbackGain,
                        correlationId: speechCorrelationId,
                        epoch: S.incomingAudioEpoch,'''),
        ('''                    if (
                        cancelledCorrelationId
                        && cancelledCorrelationId === S.currentPlayingSpeechCorrelationId
                    ) {''',
         '''                    if (cancelledCorrelationId.indexOf('native_connection_') === 0) {
                        if (window.appAudioPlayback && typeof window.appAudioPlayback.cancelNativeConnectionPlayback === 'function') {
                            window.appAudioPlayback.cancelNativeConnectionPlayback(cancelledCorrelationId);
                        }
                    } else if (
                        cancelledCorrelationId
                        && cancelledCorrelationId === S.currentPlayingSpeechCorrelationId
                    ) {'''),
    ),
    "static/app/app-audio-playback.js": (
        ("    // ======================== Audio blob handling ========================", PLAYBACK_HELPERS + "    // ======================== Audio blob handling ========================"),
        ("                    source._nekoSpeechId = normalizeAssistantTurnId(item.speechId);",
         "                    source._nekoSpeechId = normalizeAssistantTurnId(item.speechId);\n                    source._nekoSpeechCorrelationId = item.correlationId;"),
        ("    async function handleAudioBlob(blob, expectedEpoch, speechId, turnId, playbackGain) {",
         "    async function handleAudioBlob(blob, expectedEpoch, speechId, turnId, playbackGain, correlationId) {"),
        ('''        var arrayBuffer = await blob.arrayBuffer();
        if (expectedEpoch !== S.incomingAudioEpoch) {''',
         '''        var arrayBuffer = await blob.arrayBuffer();
        if (expectedEpoch !== S.incomingAudioEpoch || retiredNativeConnections.has(correlationId)) {'''),
        ("        var audioBuffer = S.audioPlayerContext.createBuffer(1, float32Data.length, sampleRate);",
         "        if (retiredNativeConnections.has(correlationId)) return;\n        var audioBuffer = S.audioPlayerContext.createBuffer(1, float32Data.length, sampleRate);"),
        ("            speechId: normalizeAssistantTurnId(speechId),\n            playbackGain:",
         "            speechId: normalizeAssistantTurnId(speechId),\n            correlationId: correlationId,\n            playbackGain:"),
        ("        if (!meta.speechId) {", "        if (retiredNativeConnections.has(meta.correlationId)) return;\n        if (!meta.speechId) {"),
        ("            speechId: meta.speechId,\n            turnId:", "            speechId: meta.speechId,\n            correlationId: meta.correlationId,\n            turnId:"),
        ('''                    item.turnId,
                    item.playbackGain
                );''',
         '''                    item.turnId,
                    item.playbackGain,
                    item.correlationId
                );'''),
        ("    mod.clearAudioQueue = clearAudioQueue;", "    mod.cancelNativeConnectionPlayback = cancelNativeConnectionPlayback;\n    mod.clearAudioQueue = clearAudioQueue;"),
        ('''        window.NekoSpeechPlaybackState = state;
        try {''',
         '''        window.NekoSpeechPlaybackState = state;
        try {
            if (String(state.correlationId).indexOf('native_connection_') === 0 &&
                S.socket && typeof S.socket.send === 'function' &&
                (S.socket.readyState === 1 || typeof S.socket.readyState === 'undefined')) {
                S.socket.send(JSON.stringify({action: 'native_speech_playback_state',
                    sdk_speech_correlation_id: state.correlationId, active: !!state.active}));
            }
        } catch (_) { /* disconnected local frontend */ }
        try {'''),
    ),
}


ELIGIBILITY_UPGRADES = {
    "main_routers/websocket_router.py": (
        ('''                if _is_voice_path_message(message) and _owns_voice_connection():''',
         '''                if message.get("action") == "ping" and _owns_voice_connection():
                    # A newer chat window does not revoke this voice lease.
                    # Reply on the sender socket without granting text authority.
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
                if _is_voice_path_message(message) and _owns_voice_connection():'''),
    ),
    "main_logic/omni_realtime_client/_transport.py": (
        ("    def _capture_native_barge_in_pcm(self, pcm, speech_active, captured_at):",
         '''    def _remember_native_barge_in_overlap(self, audio_timeline_at):
        self._local_barge_in_overlap = None
        getter = getattr(self, "get_native_barge_in_generation", None)
        generation = getter() if callable(getter) else None
        owner = getattr(self, "_native_playback_owner", None)
        now = time.monotonic()
        playback_at = getattr(self, "_native_playback_state_at", 0.0)
        if (self._is_free_proxy and generation is not None and owner
                and owner[:3] == (self._native_output_connection_token,
                                  self._connection_generation, generation)
                and getattr(self, "_native_playback_active", False)
                and getattr(self, "_native_playback_audible", False)
                and playback_at and 0 <= now - playback_at <= self._LOCAL_TALKING_WINDOW_SECONDS):
            # Only a real playback receipt can carry this utterance across the end.
            self._local_barge_in_overlap = (owner, now, audio_timeline_at)

    def _capture_native_barge_in_pcm(self, pcm, speech_active, captured_at):'''),
        ('''        if not audible:
            self._note_local_onset_declined(
                "nothing audible for %.1fs" % (now - getattr(self, "_ai_recent_activity_time", 0.0)))''',
         '''        overlap = getattr(self, "_local_barge_in_overlap", None)
        getter = getattr(self, "get_native_barge_in_generation", None)
        generation = getter() if callable(getter) else None
        playback_owner = getattr(self, "_native_playback_owner", None)
        playback_owner_matches = bool(playback_owner and playback_owner[:3] == (
            getattr(self, "_native_output_connection_token", None), self._connection_generation, generation))
        if self._is_free_proxy and playback_owner and not playback_owner_matches:
            audible = False
        overlap_matches = bool(overlap and overlap[0][:3] == (
            getattr(self, "_native_output_connection_token", None),
            self._connection_generation, generation))
        if (evidence == "speech-sustained" and overlap_matches
                and 0 <= time.monotonic() - overlap[1] <= self._LOCAL_BARGE_IN_SECONDS + self._LOCAL_BARGE_IN_GAP_SECONDS
                and self._LOCAL_BARGE_IN_SECONDS <= self._local_barge_in_loud_at - overlap[2]
                    <= self._LOCAL_BARGE_IN_SECONDS + self._LOCAL_BARGE_IN_GAP_SECONDS):
            audible = True
        if not audible:
            age = time.monotonic() - playback_at if playback_at else -1.0
            feedback = ("missing" if not playback_at else "stale" if age > self._LOCAL_TALKING_WINDOW_SECONDS
                        else "active" if getattr(self, "_native_playback_active", False) else "inactive")
            self._note_local_onset_declined(
                "nothing audible for %.1fs feedback=%s playback_active=%s playback_audible=%s heartbeat_age=%.3fs "
                "feedback_rejected=%s playback_owner_match=%s overlap_owner_match=%s speech_sustained=%s" % (
                    now - getattr(self, "_ai_recent_activity_time", 0.0), feedback,
                    getattr(self, "_native_playback_active", None), getattr(self, "_native_playback_audible", None), age,
                    getattr(self, "_native_playback_rejected", None), playback_owner_matches, overlap_matches,
                    evidence == "speech-sustained"))'''),
        ('''                        self._local_barge_in_from = audio_timeline_at
                    self._local_barge_in_loud_at = audio_timeline_at''',
         '''                        self._local_barge_in_from = audio_timeline_at
                        self._local_barge_in_overlap = None
                        if speech_active is True:
                            self._remember_native_barge_in_overlap(audio_timeline_at)
                    self._local_barge_in_loud_at = audio_timeline_at'''),
        ('''                        self._local_barge_in_from = None
                        await self._handle_local_speech_onset("speech-sustained")''',
         '''                        self._local_barge_in_from = None
                        try:
                            await self._handle_local_speech_onset("speech-sustained")
                        finally:
                            self._local_barge_in_overlap = None'''),
        ('''                      > self._LOCAL_BARGE_IN_GAP_SECONDS):
                    self._local_barge_in_from = None''',
         '''                      > self._LOCAL_BARGE_IN_GAP_SECONDS):
                    self._local_barge_in_from = None
                    self._local_barge_in_overlap = None'''),
        ('''        self._native_playback_state_at = 0.0
        if (getattr(self, "_native_barge_in_pending", False) and''',
         '''        self._native_playback_state_at = 0.0
        self._native_playback_owner = None
        self._local_barge_in_overlap = None
        if (getattr(self, "_native_barge_in_pending", False) and'''),
    ),
    "main_logic/core/asr_runtime.py": (
        ('''            source._native_playback_active = active
            source._native_playback_state_at = time.monotonic()''',
         '''            source._native_playback_active = active
            source._native_playback_state_at = time.monotonic()
            getter = getattr(source, "get_native_barge_in_generation", None)
            generation = getter() if callable(getter) else None
            source._native_playback_owner = (token, source._connection_generation, generation, websocket)
            source._native_playback_rejected = None
            source._native_playback_audible = message.get("audible") is True
        elif source is not None:
            source._native_playback_rejected = ("websocket" if websocket is not self.websocket
                else "token" if message.get("sdk_speech_correlation_id") != token else "invalid_active")'''),
        ('''        if self._game_speech_correlation_for(self.read_current_speech_id()):''',
         '''        overlap = getattr(source, "_local_barge_in_overlap", None)
        if overlap and overlap[0][3] is not self.websocket:
            source._note_local_onset_declined("native playback owner mismatch: websocket")
            return False
        if self._game_speech_correlation_for(self.read_current_speech_id()):'''),
    ),
    "static/app/app-audio-playback.js": (
        ("                    source._nekoScheduledEndAudioTime = scheduledEndTime;",
         "                    source._nekoScheduledStartAudioTime = scheduledStartTime;\n                    source._nekoScheduledEndAudioTime = scheduledEndTime;"),
        ('''                    sdk_speech_correlation_id: state.correlationId, active: !!state.active}));''',
         '''                    sdk_speech_correlation_id: state.correlationId, active: !!state.active,
                    audible: state.audioContextState === 'running' && S.scheduledSources.some(function (source) {
                        return source._nekoSpeechCorrelationId === state.correlationId &&
                            source._nekoScheduledStartAudioTime <= state.audioContextTime &&
                            source._nekoScheduledEndAudioTime > state.audioContextTime;
                    })}));'''),
    ),
}


def _upgrade_targets(targets, upgrades, replay):
    """Keep complete existing patch hunks verifiable, including earlier deployments."""
    result = []
    remaining = dict(upgrades)
    for relative, replacements in targets:
        additions = remaining.pop(relative, ())
        covered, hunks = set(), []
        for old, prior in replacements:
            new = prior
            for index, (before, after) in enumerate(additions):
                if before in new:
                    new = new.replace(before, after)
                    covered.add(index)
            hunks.append((old, new))
            if prior != new:
                replay.append((relative, prior, new))
        extra = [pair for index, pair in enumerate(additions) if index not in covered and pair[0] != pair[1]]
        hunks.extend(extra)
        replay.extend((relative, old, new) for old, new in extra)
        result.append((relative, tuple(hunks)))
    for relative, hunks in remaining.items():
        hunks = tuple(pair for pair in hunks if pair[0] != pair[1])
        result.append((relative, hunks))
        replay.extend((relative, old, new) for old, new in hunks)
    return tuple(result), tuple(replay)


def upgrade_targets(targets):
    targets, replay = _upgrade_targets(targets, UPGRADES, [(
        "main_logic/core/asr_runtime.py",
        "        if self._game_speech_correlation_for(self.speech_id):",
        "        if self._game_speech_correlation_for(self.read_current_speech_id()):",
    )])
    targets, eligibility_replay = _upgrade_targets(targets, ELIGIBILITY_UPGRADES, [])
    # Upgrade an existing full hunk before considering its shorter original anchor.
    # Replay must look for the final hunk, or it inserts another feedback sender.
    final_replay = []
    for relative, old, new in replay:
        for before, after in ELIGIBILITY_UPGRADES.get(relative, ()):
            new = new.replace(before, after)
        final_replay.append((relative, old, new))
    return targets, eligibility_replay + tuple(final_replay)


def normalize_playback_feedback(text):
    """Remove the legacy sender left beside the complete audible receipt by old replay."""
    _, inserted = UPGRADES["static/app/app-audio-playback.js"][-1]
    legacy_sender = inserted.removeprefix("        window.NekoSpeechPlaybackState = state;\n").removesuffix("        try {")
    if "audible: state.audioContextState === 'running'" in text:
        return text.replace(legacy_sender, "")
    return text
