# Native double-ASR: bounded source and sanitized observations

No product change, live test, audio playback, microphone, or model call was made to prepare this packet. Current local source excerpts are identified by SHA, and may postdate historical run51. Source comments claiming proxy support are hypotheses unless supported by an observed configuration acknowledgment. Do not interpret them as proof.

## Task

Explain the smallest diagnostic that distinguishes provider endpointing from local phrase timing/pacing, while preserving ordinary interruption. Do not implement or assume MANUAL support. Do not infer an actual provider ACK or audio offset from missing telemetry. Work with what is here and state residual uncertainty in ONE answer; do not ask for the complete raw report or repository.

Existing reports: ../daily-companion-continuous51-review-2026-10-15.md and ../daily-companion-native-auto-design-review-2026-10-15.md.
Public source files on codex/daily-learning-companion: scripts/neko_phrase_input_transport.py (accept/watch/flush), scripts/neko_phrase_input_buffer.py (feed/tick/take, cropping), scripts/neko_daily_voice_probe.py (fixed-input loop around lines527-560). These exist in GitHub; read directly, do not request manual pasting. Exact relative raw paths below are provenance only; use the supplied excerpts for those ignored files.

F3 previously requested lines1592-1711 are not the speech_started handler in the CURRENT source. Actual boundaries are included below. Follow symbols rather than assuming historical line numbers.

## What remains unproven

The recorded run is one multi-turn scene, not repeated trials establishing a deterministic silence threshold. At most four proposed probes would be exploratory samples, not proof of a stable T*. A neutral prompt also cannot guarantee zero autonomous tool calls; any future live test must have explicit call bounds. Fixed-file pacing is not equivalent to changing live microphone streaming. Internal-silence removal changes the signal and needs its own recognition/interrupt checks. No test is being authorized by this packet.

### benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_transport.py:913-951

Snapshot SHA256 `3f15318310c75880a27f4fc1ef2ec961b5472204f36056068df30ea8043bdae8`; current local source, not a claim of the historical run source.

```python
0913             # recall_memory calls in voice mode).
0914             #
0915             # MANUAL mode: both proxies receive ``turn_detection: null``
0916             # via the StepFun-shape websocket session config. lanlan.tech
0917             # (StepFun proxy) honours it natively; lanlan.app (Vertex
0918             # Gemini proxy) translates the disabled-VAD intent on the
0919             # server side, since the proxy already maps StepFun-shape
0920             # client events to Vertex Live (see _has_server_vad gate
0921             # at __init__ — lanlan.app+free is already treated as
0922             # client-side VAD only).
0923             default_voice = get_stepfun_tts_default_voice('free')
0924             free_session = {
0925                 "instructions": instructions,
0926                 "modalities": ['text', 'audio'],
0927                 "voice": self.voice if self.voice else default_voice,
0928                 "input_audio_format": "pcm16",
0929                 "output_audio_format": "pcm16",
0930                 "turn_detection": None if is_manual else {
0931                     "type": "server_vad"
0932                 },
0933             }
0934             # 海外免费（lanlan.app，Gemini 代理）建 session 时一次性指定
0935             # language_code，与 TTS server 路对偶；lanlan.tech（StepFun）不发，
0936             # 沿用其自动识别 / voice_label 语义。
0937             if 'lanlan.app' in (self.base_url or ''):
0938                 from utils.language_utils import get_tts_language_code
0939                 free_session["language_code"] = get_tts_language_code()
0940             free_tools: List[Dict[str, Any]] = []
0941             if self.has_tools():
0942                 free_tools.extend(self._tools_for_step())
0943             free_session["tools"] = free_tools
0944             await self.update_session(free_session)
0945         elif "grok" in self._model_lower:
0946             # xAI Grok Voice：OpenAI Realtime 1.0 风格的扁平 schema。
0947             # 内置 voice 见 GET /v1/tts/voices（eve/ara/leo/rex/sal），默认 eve。
0948             # tools 走 OpenAI 兼容的 function 协议（response.function_call_arguments.done）。
0949             grok_session = {
0950                 "instructions": instructions,
0951                 "modalities": self._modalities,
```

### benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_transport.py:1321-1360

Snapshot SHA256 `3f15318310c75880a27f4fc1ef2ec961b5472204f36056068df30ea8043bdae8`; current local source, not a claim of the historical run source.

```python
1321     def expect_session_update_ack(self, instructions: str) -> asyncio.Future:
1322         """Arm an exact waiter for a future ``session.updated`` snapshot."""
1323
1324         loop = asyncio.get_running_loop()
1325         waiter = loop.create_future()
1326         self._session_update_ack_waiters.append((str(instructions), waiter))
1327         return waiter
1328
1329     def discard_session_update_ack(self, waiter: asyncio.Future) -> None:
1330         """Remove a delivery-barrier waiter without affecting other updates."""
1331
1332         self._session_update_ack_waiters = [
1333             (expected, pending)
1334             for expected, pending in self._session_update_ack_waiters
1335             if pending is not waiter
1336         ]
1337         if not waiter.done():
1338             waiter.cancel()
1339
1340     def _notify_session_updated(self, event: Dict[str, Any]) -> None:
1341         """Settle waiters whose exact instructions snapshot was accepted."""
1342
1343         session = event.get("session")
1344         if not isinstance(session, dict):
1345             return
1346         accepted_instructions = session.get("instructions")
1347         if accepted_instructions is None:
1348             return
1349         accepted_text = str(accepted_instructions)
1350         remaining = []
1351         for expected, waiter in self._session_update_ack_waiters:
1352             if waiter.done():
1353                 continue
1354             if expected == accepted_text:
1355                 waiter.set_result(None)
1356             else:
1357                 remaining.append((expected, waiter))
1358         self._session_update_ack_waiters = remaining
1359
1360     def _cancel_session_update_ack_waiters(self) -> None:
```

### benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_transport.py:3513-3582

Snapshot SHA256 `3f15318310c75880a27f4fc1ef2ec961b5472204f36056068df30ea8043bdae8`; current local source, not a claim of the historical run source.

```python
3513     async def handle_interruption(
3514         self,
3515         *,
3516         connection_still_ours: Callable[[], bool] | None = None,
3517     ) -> None:
3518         """Handle user interruption of the current response."""
3519         if connection_still_ours is not None and not connection_still_ours():
3520             return
3521         if not self._is_responding:
3522             return
3523
3524         logger.info("Handling interruption")
3525
3526         # Mark as interrupted to suppress any remaining output until next response
3527         self._interrupted = True
3528         # 这一轮被取消了，但 provider 仍然欠它一个终结事件（Gemini 是
3529         # interrupted / turn_complete）。记一笔「欠账」：那条终结属于**这一轮**，
3530         # 不能让它去结算之后才铸造的 external turn token —— 逐事件捕获的实现会
3531         # 让它捕获到新 token 并清掉，会话随即显得空闲而外部回合还活着。
3532         # 一次性的：由下一个到达的终结消费掉，或在真正的新回合开始时作废
3533         # （_gemini_support.py 的 turn-start 块），或到期。
3534         self._gemini_cancelled_terminal_pending = True
3535         # 期限是独立于内容的第二道界。turn-start 那处作废只在「合法终结之前先来了
3536         # AI 内容」时才跑得到；裸 turn_complete 绕过它，此后再无内容的情形也绕过
3537         # 它。没有期限时，陈旧欠账会一直挂着直到吃掉某一条不属于它的终结。
3538         self._gemini_cancelled_terminal_deadline = (
3539             time.monotonic() + GEMINI_CANCELLED_TERMINAL_TTL_SECONDS
3540         )
3541         # 期限的起点要等中断真正送达 provider 才算数。Gemini 没有 response.cancel，
3542         # 中断是靠后继内容送出去才生效的，所以 _gemini_send_user_turn 会把它重打
3543         # 一次；这里先打是为了让下面任何一条 return 路径都带着期限离开，不至于落进
3544         # deadline is None 的 fail-open。只允许重打一次，免得后续每次发送都续命。
3545         self._gemini_cancelled_terminal_awaiting_delivery = True
3546         # 身份：让 _gemini_send_user_turn 能认出「这笔欠账是不是我这次发送送达的」。
3547         # 那边是 await 之后才读全局状态的，没有身份的话，一次**更早**发起、此刻才
3548         # 返回的发送会把刚武装的这笔当成自己送的，提前起算 TTL。
3549         self._gemini_cancelled_terminal_id = object()
3550
3551         # 1. Cancel the current response
3552         # Presence, not truthiness — the third site in this file where a
3553         # numeric id of 0 would have read as "no response". Here the cost is
3554         # the worst of the three: the barge-in would mark the turn interrupted
3555         # and never send response.cancel, so generation keeps running and the
3556         # arbiter lane stays held until the provider finishes on its own.
3557         if self._current_response_id is not None:
3558             try:
3559                 await self.cancel_response(send_guard=connection_still_ours)
3560             except ConnectionError:
3561                 if (
3562                     connection_still_ours is not None
3563                     and not connection_still_ours()
3564                 ):
3565                     return
3566                 raise
3567
3568         if connection_still_ours is not None and not connection_still_ours():
3569             return
3570
3571         self._is_responding = False
3572         # Keep the cancelled response identity until its terminal event arrives.
3573         # Clearing it here makes the stale-event filter classify that
3574         # response.done as stale. The filter still forwards stale terminals to
3575         # the arbiter (the lane would reopen either way), but the rest of the
3576         # done handling is skipped for the turn: the done counters and usage
3577         # recording, the _interrupted reset, the transcript flush and the
3578         # on_response_done callback all silently miss one turn.
3579         self._current_item_id = None
3580         # 清空转录buffer和重置标志，防止打断后的错位
3581         self._output_transcript_buffer = ""
3582         self._is_first_transcript_chunk = True
```

### benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_transport.py:4021-4110

Snapshot SHA256 `3f15318310c75880a27f4fc1ef2ec961b5472204f36056068df30ea8043bdae8`; current local source, not a claim of the historical run source.

```python
4021                 elif event_type == "input_audio_buffer.speech_started":
4022                     self._advance_study_grade_ingress_scope()
4023                     self.note_user_turn_started()
4024                     self._ensure_voice_handoff_audio_timeline()
4025                     self._voice_handoff_server_item_id = event.get("item_id")
4026                     self._note_raw_speech_started_scope(event.get("item_id"))
4027                     self._speech_started_total += 1
4028                     logger.info("Speech detected")
4029                     self._response_arbiter.notify_server_vad_started()
4030                     self._bind_input_route_identity_to_item(event.get("item_id"))
4031                     self._audio_in_buffer = True
4032                     # 重置静默计时器
4033                     self._last_speech_time = time.time()
4034                     # Priority 1: server VAD → sync to unified _client_vad_active
4035                     self._client_vad_active = True
4036                     self._client_vad_last_speech_time = self._last_speech_time
4037                     # B: server-VAD 也喂给 _user_recent_activity，保持各 VAD 源对称。
4038                     self._user_recent_activity_time = self._last_speech_time
4039                     if self._is_responding:
4040                         logger.info("Handling interruption")
4041                         await self.handle_interruption(
4042                             connection_still_ours=receive_owner_is_current,
4043                         )
4044                         if await retire_if_replaced():
4045                             return
4046                 elif event_type == "input_audio_buffer.speech_stopped":
4047                     self._speech_stopped_total += 1
4048                     logger.info("Speech ended")
4049                     handoff_boundary_is_current = (
4050                         self._note_voice_handoff_server_boundary(event)
4051                     )
4052                     # Only an ended utterance can causally create the automatic
4053                     # server-VAD response.  Marking this at speech_started can
4054                     # steal an explicit response.created whose create was
4055                     # already accepted but whose echo is still in flight.
4056                     self._response_arbiter.notify_server_vad_response_pending(
4057                         arm_timeout=False
4058                     )
4059                     # The user's turn starts HERE on a server-VAD provider, not
4060                     # at response.created: on_new_message assigns the new
4061                     # speech id and fires USER_INPUT, and the provider's
4062                     # response.created only follows some time later. A release
4063                     # suspended in a host callback would otherwise resume in
4064                     # that gap, still believe the turn is its own, and finalize
4065                     # against the speech id this user turn just took.
4066                     self._turn_epoch += 1
4067                     try:
4068                         if self.on_new_message:
4069                             await self.on_new_message()
4070                     finally:
4071                         # response.created cannot be observed while this receive
4072                         # loop is blocked in on_new_message. Start the missing-
4073                         # created backstop only after the loop can read again,
4074                         # so a slow callback cannot release a real VAD response.
4075                         if receive_owner_is_current():
4076                             self._response_arbiter.arm_server_vad_response_pending_timeout()
4077                     if await retire_if_replaced():
4078                         return
4079                     if handoff_boundary_is_current:
4080                         self._audio_in_buffer = False
4081                     # Update timestamp so grace period starts from speech end
4082                     _now = time.time()
4083                     self._client_vad_last_speech_time = _now
4084                     self._user_recent_activity_time = _now
4085                 elif event_type == "conversation.item.input_audio_transcription.completed":
4086                     if self._consume_study_grade_tail(event.get("transcript", ""), message_ws, message_generation):
4087                         continue # Same sealed input, exact redundant request; no scope revival.
4088                     self._native_barge_in_candidate = None
4089                     already_scoped = self._raw_transcript_was_already_scoped(
4090                         event.get("item_id")
4091                     )
4092                     if not self._has_server_vad and not already_scoped:
4093                         # Compatibility proxies may omit both server-VAD
4094                         # boundary events. The completed transcript is then the
4095                         # first authoritative signal that a new user turn has
4096                         # begun, so stale tool work must retire here.
4097                         self._late_raw_expected_asr_advance = True
4098                         try:
4099                             self._advance_study_grade_ingress_scope()
4100                             self.note_user_turn_started()
4101                         finally:
4102                             self._late_raw_expected_asr_advance = False
4103                     self._begin_raw_input_transcript()
4104                     self._print_input_transcript = True
4105                     transcript = event.get("transcript", "")
4106                     if self.on_input_transcript or self.on_input_transcript_with_route:
4107                         await self._deliver_input_transcript(
4108                             transcript,
4109                             item_id=event.get("item_id"),
4110                             study_input_owner=self._take_study_grade_asr(message_ws, message_generation),
```

### benchmarks/raw/neko-product-host/main_logic/omni_realtime_client/_response_arbiter.py:1817-1875

Snapshot SHA256 `0dc4d0349d518d4bac4a8a1da034e46bde4624e9fa9aa4079af8539ca32e922e`; current local source, not a claim of the historical run source.

```python
1817     def notify_server_vad_started(self) -> None:
1818         """Deliberately leave ownership unchanged until speech_stopped.
1819
1820         The transport keeps this explicit boundary so future callers do not
1821         accidentally treat speech_started as evidence of an automatic
1822         response; only the ended utterance below may arm that correlation.
1823         """
1824
1825     def notify_server_vad_response_pending(
1826         self,
1827         *,
1828         arm_timeout: bool = True,
1829     ) -> None:
1830         """Mark a VAD response pending unless an explicit create won the race."""
1831
1832         owner = self._response_owner
1833         if owner is not None and owner.ticket.sent.done():
1834             # The explicit response.create finished sending before this
1835             # utterance ended. Its response.created echo can still be next;
1836             # do not let the later VAD boundary steal that owner.
1837             return
1838         if (
1839             owner is not None
1840             and owner.response_send_started
1841             and not owner.ticket.sent.done()
1842         ):
1843             # The automatic user turn won while response.create was inside an
1844             # awaited transport write. The create may still reach the server,
1845             # so quarantine it as a server response after the write returns;
1846             # meanwhile the pending marker owns the next response.created.
1847             owner.server_vad_won_during_response_send = True
1848             owner.interrupted = True
1849             owner.interrupt_event.set()
1850         current = self._current
1851         if owner is None and current is not None:
1852             # The automatic user response won while an explicit request was
1853             # still persisting its pre-response item or waiting for its ack.
1854             # Stop that request before it can emit response.create; otherwise
1855             # its first response.created echo is indistinguishable from the
1856             # pending VAD response and can be credited to the wrong turn.
1857             current.interrupted = True
1858             current.interrupt_event.set()
1859             if current.item_ack is not None and not current.item_ack.done():
1860                 current.item_ack.set_exception(
1861                     RuntimeError(
1862                         "response dispatch interrupted by pending server VAD response"
1863                     )
1864                 )
1865         self._server_vad_response_pending = True
1866         self._bump_vad_epoch()
1867         self._server_response_active = True
1868         self._idle.clear()
1869         if arm_timeout:
1870             self._arm_server_vad_pending_timer()
1871
1872     def arm_server_vad_response_pending_timeout(self) -> None:
1873         """Start the missing-created backstop after receive handling resumes."""
1874
1875         if (
```

## Historical run51 observation projection

Metadata-only whitelist projection. Missing provider endpoint events means telemetry absence, not proof that no endpoint occurred. Transcript text deliberately omitted. Complete raw report, WAV and learning database remain local.

```json
{
  "raw_sha256": "851407e50398964ceda04ccc69eca0b360f0eda8a6ad63bbde2260ed414cfef4",
  "turn3": {
    "input_wall": 1792010855.3212926,
    "input_end_wall": 1792010868.3698816,
    "fixed_speech_end_wall": 1792010864.5619829,
    "observation_end_wall": 1792010913.3774524,
    "native_first_pcm_wall": 1792010872.991,
    "playback_first_scheduled_wall": 1792010872.993
  },
  "session_configuration_metadata": [
    {
      "dir": "send",
      "t": 1792010738.784,
      "type": "session.update",
      "turn_config_source": "client_requested",
      "turn_detection_present": true,
      "turn_detection": "server_vad",
      "bytes": 23983
    },
    {
      "dir": "send",
      "t": 1792010738.786,
      "type": "session.update",
      "turn_config_source": "client_requested",
      "turn_detection_present": false,
      "turn_detection": null,
      "bytes": 14394
    },
    {
      "dir": "send",
      "t": 1792010738.801,
      "type": "session.update",
      "turn_config_source": "client_requested",
      "turn_detection_present": false,
      "turn_detection": null,
      "bytes": 14394
    },
    {
      "dir": "send",
      "t": 1792010807.954,
      "type": "session.update",
      "turn_config_source": "client_requested",
      "turn_detection_present": true,
      "turn_detection": "server_vad",
      "bytes": 23983
    }
  ],
  "turn3_wire": [
    {
      "dir": "send",
      "t": 1792010855.373,
      "type": "input_audio_buffer.clear",
      "bytes": 71
    },
    {
      "dir": "recv",
      "t": 1792010868.209,
      "type": "conversation.item.input_audio_transcription.completed"
    },
    {
      "dir": "recv",
      "t": 1792010868.288,
      "type": "response.function_call_arguments.done"
    },
    {
      "dir": "recv",
      "t": 1792010868.293,
      "type": "response.done"
    },
    {
      "dir": "send",
      "t": 1792010871.417,
      "type": "conversation.item.create",
      "bytes": 966
    },
    {
      "dir": "recv",
      "t": 1792010873.461,
      "type": "conversation.item.input_audio_transcription.completed"
    },
    {
      "dir": "recv",
      "t": 1792010876.897,
      "type": "response.audio.done"
    },
    {
      "dir": "recv",
      "t": 1792010876.9,
      "type": "response.done"
    },
    {
      "dir": "recv",
      "t": 1792010876.903,
      "type": "response.function_call_arguments.done"
    }
  ],
  "turn3_native_boundaries": [
    {
      "wall": 1792010868.218,
      "direction": "receive",
      "type": "user_transcript"
    },
    {
      "wall": 1792010873.469,
      "direction": "receive",
      "type": "user_transcript"
    },
    {
      "wall": 1792010876.902,
      "direction": "receive",
      "type": "audio_done"
    },
    {
      "wall": 1792010876.905,
      "direction": "receive",
      "type": "system"
    }
  ]
}
```
