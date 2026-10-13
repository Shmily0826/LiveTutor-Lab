# Voice16 first-input epoch review — 2026-10-14

Read full contract/plan/status/blockers first. Main's current recorded baseline is feature `537e573`, ledger552/55/0 and no online session; this agent did not inspect/change the ledger or start anything. Scope: original voice16 JSON/final review, bounded append-log segment and actual deployed input/receive/tool code plus the two patch generators. Only this report was added. No production/test/manifest/other-report changes, tests, host/API/audio calls or new agent.

## Confirmed first-turn order

Sources: `benchmarks/raw/evidence/daily-companion-20261014-teaching-voice16.json` first turn / wire trace / Native trace, corresponding final review, and `benchmarks/raw/neko-desktop-host.log:63138-63179`.

| Event | Wall seconds | Implication |
| --- | --- | --- |
| Fixed first input admitted | 1791924571.414846 | Sole first WAV; no room mic |
| Actual first WAV audio starts | 1791924571.424380 | Same authorized PCM/RNNoise route |
| Last fixed non-silent sample | 1791924581.482526 | WAV threshold endpoint, not exact client VAD timestamp |
| `study_quiz` arguments done | 1791924583.600 | 2.117474s after that fixed endpoint; first ASR not yet received |
| Trusted current role dispatch | approximately1791924583.602 | Plugin request begins in captured scope1 |
| Provider `response.done` | 1791924583.647 | No transcript/audio; Native turn-end receipt at583.652 |
| First input ASR completed,69 chars | 1791924583.825 | 225ms after tool arguments, still same fixed input |
| Scope1→2 retires2 tool tasks | same ASR/log63176 | Actual tool task + collector cancelled, `user_turn_replaced` |
| First input's appended tail finishes | 1791924585.399411 | Remaining silent padding, not a second utterance |
| Next fixed WAV begins | 1791924635.423823 | 51.599s after first ASR; not cause of first retirement |

Native received the matching first command transcript at583.841. First turn has **zero Native PCM**. Its existing DB snapshot nevertheless contains the generated question/IDs; main final review records correct source question and later held grading. A remote plugin/SQLite call can finish after the caller task is cancelled, so “question saved” does not prove that its result survived the Native collector or was spoken.

This is high-confidence **same first input / late ASR ordering**, not a learner barge-in. Local onset was correctly declined because nothing was audible (`63138`); no actual output existed to interrupt. The no-server-VAD completed-transcript path itself advances scope. Do not weaken normal onset/cancellation to repair this.

The function call's response ID (`resp_1791924562816`) and done's response ID (`resp_1791924584221`) differ; ASR trace has no usable item ID. IDs are opaque and do not establish source-input identity or justify a singleton response alias. The existing unannounced-response fallback already records its provider-turn mismatch; the concrete cancellation above is sufficient to explain lost quiz voice.

## Current source explanation

The deployed package uses `main_logic/omni_realtime_client/_transport.py` for PCM/receive handlers and `_tools.py` for ownership. `_input.py` / `_handlers.py` are not files in this deployed package; the report cites the actual code rather than assuming a different module layout.

- `_transport.py:1559-1580` records `speech_active`/RMS evidence into `_last_local_loud_time` before admission awaits. Actual no-VAD sustained RNNoise handling remains at1617-1663; ordinary audible-onset/cancel behavior is separate.
- `_tools.py:728-766` defaults to ordering only when exact free `lanlan_app_gemini`, no server VAD, not handoff, local speech newer than last ASR, and **tool arrives within2s of last local loud**. Otherwise it immediately enters `_start_raw_tool_call_now`.
- Voice16 did not set the optional speech gate (raw has no gate marker; probe only sets the environment/report marker when flag enabled). Its immediate plugin dispatch before ASR shows no effective ordering barrier. Fixed speech ended2.117s before tool and the581.6–583.6 meter has raw_loud0 / a single tail speech verdict (`63164`). The2s eligibility cutoff is the high-confidence missed-admission explanation; the exact `_last_local_loud_time` was not logged, so its numeric value and predicate evaluation are not directly proven.
- `_transport.py:3869-3894` calls `note_user_turn_started` for an unscoped no-VAD ASR, marks expected advance, begins ASR receipt, awaits host transcript handling, then marks callback ready. `_tools.py:414-452` still cancels every executing old-scope task/collector. Expected-ASR flag only avoids advancing the separate foreign-scope counter; it does not save already dispatched tasks.
- Existing ordering pending tasks sit outside `_tool_tasks`, wait0.4s for ASR and separately up to2s for an observed slow callback, and can acquire only one expected scope+1 before dispatch. This is the right repair site: **hold before executing**, not promote an executing/retired task afterward.

## Enabling the existing opt-in gate alone is insufficient

`neko_study_speech_gate_patch.py:30-35` can queue Study calls with unconsumed speech even after the2s freshness window. But `TRANSCRIPT:171-178` / deployed `_tools.py:884-894` only mark gated pre-ASR calls observed when ASR receipt is within **200ms of pending admission**. Voice16's measured tool→ASR225ms (roughly223ms after immediate dispatch point) is outside that neighbor allowance. A deterministic offline225ms replay would reject the gated candidate rather than speak the quiz. Scheduler-dependent later enqueue is not a reliability fix.

Do not simply enlarge the global200ms rule or enable gate by default: that rule deliberately prevents an earlier fragmented prefix from claiming a suffix's scope. Quiet1.2s and “ASR received after loud” cannot prove which provider tool arguments belong to which fragment. Voice16 is fully spoken before the tool; it is not evidence that the general0.9s-pause problem is solved.

## Smallest candidate, with safety requirements

First repair the narrow default ordering eligibility for an outstanding local voice input on the exact free/no-VAD route. Do not decide “no pending input” merely because local loud ended more than2s ago. Reuse the existing independent bounded pending queue and ASR-receipt/callback-ready machinery. Keep0.4s admission wait (the observed225ms fits) and2s callback bound; do not add waits to the receive loop.

Required negative provenance fence: capture the already observed local speech/input counter and current ingress/connection/provider/scope/foreign-scope before queuing, then reject if **new actual speech/input** arrived before expected ASR release. `_transport._note_voice_handoff_input_open:159-166` increments `_voice_handoff_input_sequence` on speech observation and tags its connection; it may be reused as “new speech happened since this admission” evidence. It is **not a stable utterance ID**: it increments per observation/frame and open/boundary state can be cleared. Its equality can reject replacement; equality alone cannot prove that an opaque provider call is the right fragment.

For voice16, a conservative initial unconsumed-input case (no prior completed ASR on this connection, no subsequent voiced input, same owner, no foreign retirement) has strong positive evidence. For later fragmented turns, retain the existing tighter refusal unless a real source-input association is available. Do not retrospectively bless old prefix arguments or bypass an already recorded foreign retirement. Main should choose the narrowest predicate supported by its real input ownership state rather than treating this report as approval for all unconsumed frames indefinitely.

Before starting a paid Study callback, require actual expected ASR receipt **and host callback readiness**. Missing ASR, callback timeout or queue-full must produce bounded no-continuation abandonment rather than a fresh paid dispatch/owner claim. Current nongated fallback can execute after0.4s with no ASR if scope stayed unchanged; widening eligibility must not turn that fallback into delayed self-cancellation or wasted teaching requests. Preserve existing collector ownership/no-response behavior and same-batch handling.

No new CONNECT, fake onset/server-VAD event, old PCM replay, response-ID alias, blanket skip of `note_user_turn_started`, permanent “first ASR already scoped” marker, or lifting of an executing task after cancellation is needed. Real new input/barge-in must retire old work as before.

## Minimum offline reproduction plan (not executed here)

Use actual `_start_raw_tool_call`, scope retirement, `_begin/_finish_raw_input_transcript`, original task owner/collector and a local controlled dispatcher. Fake only clock/provider transport/model callback; no host/API/audio. The test should reproduce these boundaries:

1. First input last-loud about2.117s before tool, tool at583.600, ASR at583.825: current code invokes before ASR and cancels scope1; candidate must invoke exactly once only after scope2 callback-ready, producing one question and one tool result.
2. Run the same225ms sequence with opt-in gate: current200ms neighbor refusal is visible; a scoped initial-input repair must not silently relax fragmented-prefix ownership globally.
3. Insert real subsequent speech/input-counter change, ordinary foreign scope advance, material retirement, connection replacement, handoff or stop between queue and ASR: old candidate must never execute/promote. Include new input whose ASR is delayed and would otherwise look like “expected+1”.
4. Missing ASR, slow/missing callback and queue-full: bounded abandonment, zero paid dispatcher calls and no old-output continuation. Readiness timing must use receipt and completion separately.
5. Already-ready same-scope tool, known same-response siblings and cancellation-resistant old task: normal result/batch behavior stays; never rebind a retired task or alias future siblings.
6. A genuine prefix/suffix pause sequence must keep its old-prefix refusal. A passing voice16 replay alone is not a natural-pause/barge-in regression pass.

Add telemetry of admission predicate/result, last-loud, ASR receipt/ready, captured/current input counter and source scope using only scalar ownership data, not audio/credentials. This closes the current exact-last-loud evidence gap without another paid scene solely for a missing timestamp. Actual model/device quiz and ordinary human barge-in conclusions still require Main's later appropriate evidence; none were newly verified here.

Review/source diagnosis complete and frozen. No tests were run and no implementation was modified by this agent.
