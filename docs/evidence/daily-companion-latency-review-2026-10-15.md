# Phase 27 — independent latency diagnostic review

Scope: additions to `scripts/neko_spoken_turn_analysis.py`, its tests, and the grade-only observer call sites. No production edits, host, provider, audio/device, DB, ledger, or online action. This report records source / synthetic-offline findings; it does not establish latency for a new real session.

## Two concrete P2 findings sent to Main

1. **Marker connection/scope inconsistency still produces attributed timings.** `analyze_grade_latency` checks three stages, four matching teaching identities, ordered walls and a changed relay token, but does not require or validate physical connection/scope fields. In the existing `GradeLatencyTest.scene()` fixture, changing `grade_complete.connection` to `9`, or adding `grade_complete.scope=99` while the other scopes are missing, still returns `observed_single_grade_turn` and `one_completed_write_in_this_turn`. The phrase join only compares its connection generation to `accepted.connection`; it cannot fix a mismatched completed/relay chain. Minimal repair: require non-boolean integer connection/scope on all three actual markers, accepted/complete equality, and the known controlled relay transition (connection +1, increasing scope); missing/conflicting values must yield unavailable metrics. The existing fixture needs the actual scope shape. This is diagnostic misattribution; formal grade acceptance remains a separate guard.

2. **Provider ASR observations are deduplicated by timestamp alone.** `provider_asr` uses a set of `t`; two distinct transcription-completed records with the same wall time collapse into one. Appending a same-time record with a different `transcript_chars` to the existing fixture still yields `input_end_to_provider_asr=9.99`. That cannot establish one unambiguous ASR observation. Minimal repair: only deduplicate complete identical safe observation projections (including available connection/item identity); different records at the same clock must remain ambiguous. Where identity is unavailable, do not infer that records are duplicate logger output solely from equal timestamps. Omit that metric when ambiguity remains.

These were reproduced with memory-only synthetic dictionaries, not a host, socket or provider. Main owns repairs; this agent did not modify the three reviewed files.

## Confirmed limited behavior

`parse_phrase_deliveries` outputs only its explicit count/clock whitelist plus fixed result/timebase labels; arbitrary transcript, PCM, token and path fields are dropped. Exact projected duplicate phrase records from the two logger handlers are deduplicated. Invalid finite/nonnegative inputs and unsupported result/timebase are rejected. The analyzer additionally checks integer positive sample counts, full-write equality, turn-clock bounds and accepted connection generation; multiple distinct eligible deliveries yield `ambiguous_multiple_writes`, with no phrase metrics. Phrase log data has no scope ID, so exact provider utterance or scope authority cannot be derived from it.

The functions operate on supplied values only, do not issue requests or change scene data, and output no learner text or token. Wall clocks remain separate from arrival-derived phrase sample estimates. Positive PCM is required; zero binary messages and old-token frames cannot establish first new PCM. `chunk_scheduled` is a Native scheduling observation; physical start is explicitly `unverified`, never inferred from receipt or schedule. A negative relay-write-to-first-PCM interval can be a legitimate observation because the completion logger can follow fast PCM; it is not a service-only latency claim.

Observer wiring calls both additions only inside `grade_current`, reads only fresh host log suffix already collected, stores the diagnostic after the separate `grade_acceptance` computation, and retains exit behavior based on acceptance/failure/cleanup. No retry, protocol/runtime change, additional grade read, budget mutation or ordinary-mode branch was added by these call sites.

## Independent tests

- `python -X utf8 -B scripts/test_neko_spoken_turn_analysis.py`: **11 PASS**, 0.007 s.
- `python -X utf8 -B scripts/test_neko_native_grade_probe_plan.py`: **8 PASS**, 0.256 s; actual observer AST stops at a mocked port-constructor sentinel, no real port.
- `python -X utf8 -B scripts/test_neko_voice_probe_completion.py`: **7 PASS**, 0.001 s; pure AST fixtures.

These existing 26 tests pass despite the two additional repro cases above. They are not a substitute for the missing negative coverage or evidence from an actual completed run. Main's forthcoming read-only derivation of existing37/38 artifacts is separate work; this agent did not generate or reinterpret those latency artifacts during this review.

## Exact repair closure — final frozen review

Both P2 findings above are **closed at SOURCE / OFFLINE level** in Main's revised implementation; the historical findings are retained. The analyzer now requires integer, non-boolean connection/scope on every marker, positive initial connection, equal accepted/complete connection and scope and token, then exact relay connection +1 with increasing scope and distinct token. Missing, foreign, float and boolean values refuse attributed metrics. The fixture now includes the real scope shape.

Provider-ASR observations are no longer deduplicated: repeated records, including equal-time duplicates or equal-time records with different observed fields, suppress the single-ASR metric. This is deliberately conservative when the log lacks a proven event identity. Exact public phrase logger records remain deduplicated separately; the two sources no longer share an unsafe timestamp assumption.

The revised phrase quiet metric is `sealed_estimated_wall - speech_end_estimated_wall`, comparing the same arrival-derived sample-estimate timebase, named `estimated_phrase_quiet`. The actual observed `sealed_wall - fixed_speech_end_wall` is separately named `input_end_to_phrase_seal`. It no longer describes a mixed-clock subtraction as the configured quiet period. Remaining write/grade/PCM/schedule intervals retain their existing labels and physical-playback limitation. Grade-only observer wiring and independent acceptance/exit conditions remain unchanged.

Independently reran revised `test_neko_spoken_turn_analysis.py`: **12 PASS in 0.007 s**, including marker connection/scope/token and same-time ASR ambiguity regressions. The earlier 8 grade-preflight and 7 completion checks were independently run before this exact analysis-only repair; no observer code changed between those checks and closure. No additional service, provider, device, budget or real scene was used. No concrete remaining P1/P2 was found within the bounded revised code.

Final reviewed SHA256:

- `neko_spoken_turn_analysis.py`: `e70e5fb3e0c5adfe2ad9fff2a3c3e36a4448c0654c033b1094f104b51cac070e`.
- `test_neko_spoken_turn_analysis.py`: `559d19117fc9b8b8ffe47bc589f27f8d4d9aaedf7c36eec0d71348aed5e40656`.
- `neko_daily_voice_probe.py`: `dbef45686e5a0c86398014a04140c4369a478c5d98c0875ccee53c2ace05ee32`.

Main's original latency37/38 draft remains historical; forthcoming v2 derivations are not evidence produced or inspected by this review. Native schedule continues to mean schedule, not heard playback or human acceptance.

## Scene39 real failure — readonly narrow diagnosis and next design

Original private `daily-companion-20261015-native-short39.json` was read without modification; SHA256 independently confirmed `3199f88767ef1eec3d6e73c04663d6bc71c3d49af400e09bbf1ef726413180e0`. Main's original terminal FAIL is retained. No new service, model, device, DB, budget call or replay was performed for this diagnosis.

Recorded observations:

- A fresh question/attempt was pending before input and evaluated afterward, QA **4→5**, correct/100, old formal rows preserved. Two provider `study_answer` calls appear at 1791993817.429 / 1791993819.116. There are **no local grade markers**. This is a formal grade reached through provider tool calls, not proof of the intended local automatic-grade claim/authoritative relay path.
- One successful phrase delivery reports 113432 source samples, 109782 output/written samples, 3650 compressed zero samples, connection generation 1. The provider still emits **two** transcription-completed events at 1791993817.421 and 1791993818.948. A collector phrase, individual append event IDs and local frame/sequence counters therefore do not establish a provider utterance ID or a single provider transcription.
- Actual Native ASR contains a current-question personal answer declaration (WEX→NUD), then a short isolated grading tail. Feeding these two original segments separately to the current pure classifier returns **None / None**. The first lacks the required judgment request; the second lacks current-question/personal-answer context. The checker must not concatenate those segments to manufacture authorization or claim that a locally owned grade occurred.
- The short Native reply refers to already having graded and repeats the prior scene's feedback. Its text is not an authoritative delivery of this newly held question's local grade transaction. Captured formal records alone do not repair that conversational failure.
- Actual output-only receipt says installed, flag/readonly true, captureBlocked true, with all eight denied APIs. Most later acceptance booleans remain their initial false values because missing markers cause an early conservative exception; `output_only_capture_guard=False` in that aggregate is **not** evidence that capture blocking actually failed. Similarly it must not be read as evidence of a cleanup failure: the raw cleanup list is empty.

### Why a classifier-only declaration change is insufficient

`neko_study_answer_intent.py:42` currently needs explicit target + personal answer + judge for an ordinary answer. `neko_native_grade_patch.py:46` consumes the saved first-audio question pin when taking the first valid ASR. `_start_study_grade_claim` (line 127) requires current input authority and owner, and schedules the grade through `source._create_tool_task`; `_study_grade_claim_current` compares actual input sequence, Core activation/socket and current tool owner.

Actual deployed `_transport.py:3995–4019` processes every no-server-VAD, not-already-scoped transcription-completed event by `_advance_study_grade_ingress_scope()` then `note_user_turn_started()` before delivering ASR. Actual `_tools.py:414–453` advances tool scope, increments material user epoch, and cancels/marks retired the previous tool tasks. Its `_tool_task_owner_is_current` at line 146 explicitly rejects a changed scope or provider connection. Thus accepting only the first declaration can start work that the second provider segment retires about 1.527 seconds later. This is the existing guard's intended behavior; do not disable it, reset the retired owner, or claim that both ASRs share an utterance merely because only one local phrase was written. The raw has no claim, so this cancellation sequence is a source-supported counterfactual, not an observed local-claim cancellation in scene39.

### Smallest defensible implementation increment

These are proposed changes, not implemented or verified here:

1. If product policy accepts a quiz answer declaration as a request to grade, add a **narrow pending-question-only** intent form such as explicit “current question + my answer is …”, using the original segment verbatim. Retain quote/hypothetical/refusal/new-question exclusions; do not broaden vague “I think” or bare grading tails. Evaluated attempts still require explicit correction, never implicit retry. This is an intentional admission-policy change from the existing judge-required classifier, not a wording-only regex repair.
2. Pair that admission change with an **early controlled retirement** of the exact old provider connection before slow SDK/model work. The existing `_relay_study_grade_once` cancellation/frame-lock/swap-lock/close/drain/connect/token guards (patch line 224 onward) currently run only after grading; they are the reusable mechanism to factor, not permission to bypass owner checks. A Core-owned transaction must capture a still-current first-PCM pin, activation/socket, input sequence, old physical provider/token and expected question state synchronously, then retire the old physical source under exact guards. It must not retain a cancelled old tool task as an owner or silently recapture the newest scope.
3. Formal entry admission after that controlled transition needs an explicit limited Core transaction authority, with exact original question/course/session pin and the **actual new controlled connection**, distinct from provider-generated tool-call ownership. Current source does not expose a ready, proven-safe authority getter that performs this entire transfer; do not invent one or simply pass an old owner to a new connection. Every await must recheck the original Core/input authority; newer PCM, activation/socket replacement, course/question change, unknown transition or extra generation must cancel/suppress old output. A provider ASR/scope change that wins before exact old connection retirement must fail closed, not be adopted. Holding and SDK execution also need a bounded deadline and honest failure status.
4. Deduplicate competing provider grading through that exact transaction; do not replay PCM or append the unbound grading tail to the answer. If a later segment cannot be proven related, it contributes no authorization or modified answer. If safe early retirement or authoritative whole-utterance ASR is unavailable, retain an honest partial result and use the existing text grading entrance rather than claim this voice case passes.

Before another paid scene, require actual offline Core/Omni tests for the recorded two-segment ordering, second ASR before/during SDK or swap, provider duplicate tool calls, late old source messages, new positive PCM before/during/after swap (new input wins), refusal/correction/foreign pin, connection/activation replacement and timeout cleanup. None of those future cases is established by the current 12 latency tests. This proposal changes the grade admission/transaction sequence; it must not be presented as a pure diagnostic fix or a completed B/C/F acceptance.

Scene39 diagnosis is frozen here. Main owns next implementation, runtime evidence, ledger and publication; the previous two phase27 diagnostic P2 closures remain valid and do not erase this new real failure.
