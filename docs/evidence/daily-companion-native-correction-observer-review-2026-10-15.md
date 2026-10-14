# Phase 26 — explicit same-question correction observer

Status: SOURCE / OFFLINE PASS; current correction MODEL / Native runtime / physical output / HUMAN remain unverified. Files frozen after this handoff. No service, provider, audio device, capture, loopback, application host, user DB, or ledger was used or changed.

## API and evidence contract

`scripts/neko_native_grade_acceptance.py` retains `grade_snapshot(db)` and pure `grade_acceptance(report)`. `report.grade_intent` accepts exactly `answer` or `correction`; an absent field means legacy `answer`. Unknown values fail. Returned `grade_intent` exposes the selected mode. Caller-side CLI permission / quiz-preparation checks remain Main's responsibility.

The snapshot remains one existing explicit task SQLite DB, readonly `mode=ro`, `query_only`, timeout zero, with no general interaction history or private answer output. QA projection now additionally returns public `topic_id`, already selected for the complete raw-row SHA. It does not parse arbitrary learning history. Serialized Store questions still project only prompt / question_id / attempt_id; their full original raw row, including private fields and timing, remains covered by the SHA without publication.

Ordinary answering retains the original pending attempt and all previous Native / capture / timing / cleanup checks. It has the existing 19 checks plus `supported_grade_intent`. Correction substitutes clearly named state checks (`evaluated_wrong_or_partial_four_ids`, `same_question_new_attempt_evaluated`) and adds `correction_origin_formal_lineage` / `same_concept_topic` (22 total).

Correction requires:

- Four nonempty input IDs, evaluated old attempt, and a saved wrong/partial last grade. One uniquely matching **formal** old interaction must corroborate that grade and its QA row: exact qid/aid, course, historical session, original input, prompt / serialized question IDs, score and verdict, non-degraded metadata. A historical session may differ from the current resumed session; its own QA / interaction / material-context sessions must agree. Last grade alone is insufficient.
- Same current course, session, question ID and prompt after grading; a strictly new nonempty evaluated attempt ID. Exactly one new QA and one new formal interaction must agree with the final attempt, exact observed ASR input and current course/session. All previous QA raw hashes and public formal interaction records must survive unchanged.
- Old and new QA must have the same nonempty `topic_id`. Missing concept identity fails this correction check rather than claiming concept continuity. This only verifies the Store's persisted topic identity, not pedagogical equivalence of different topic names.
- Markers retain the **old input attempt** in all three input pins; `grade_complete` / `relay_written.result_attempt_id` must be the **new result attempt**. All prior actual-profile, old-token cancellation/retirement, after-grade new-token PCM/scheduling/terminal, capture-policy and bounded-run checks remain in force.

## Actual Store lineage read

Canonical `entry_tutor_answer_entries.py:63` validates exact current qid/aid/course/session, evaluated non-degraded wrong/partial cache, and original course; it deep-copies the held question, creates a new UUID attempt, clears evaluated/cache/reservation flags, and returns `previous_attempt_id` at line 117. That return value is not a persisted QA linkage column.

`study_avatar_tools.py:1112` validates explicit `correction_of`, calls that retry entry, verifies the returned old/new IDs, then calls the normal formal grading entry with the retried held question. `entry_tutor_answer_entries.py:270` derives topic from the held question for current-question grading. `store.py:842` writes the question dict as JSON, original answer and evaluation with the supplied historical session/topic into QA. The checker therefore joins existing formal qid/aid + QA rather than inventing a persisted `correction_of` field. It also checks the public persisted topic directly.

## Independent offline verification

Command: `python -X utf8 -B scripts/test_neko_native_grade_acceptance.py`

Result: **20 tests PASS in 0.566 s** (original 13 ordinary tests plus 7 correction tests). These use actual temporary SQLite tables and Store-shaped serialized question JSON, not an application/SDK/provider instance. Cases include wrong and partial origins, old-session QA after restart, old wrong answer preservation, duplicate/missing old formal joins, same/empty attempt, changed question/course/session, deleted old QA, old-row mutation, duplicate new grade, topic drift/missing topic, unknown/wrong mode, new formal/QA attempt mismatch, and old-input/new-result marker mismatch. Existing ASR, Native cancel/PCM, timing, trace completeness, capture guard and terminal negative cases continue to pass.

Readonly original scene37 regression: original SHA remains `c8484c5ed76bfdca348c43c42dbc605c1020bcdc78814ffca66196a4a81e9035`; current checker returns the candidate result with **20/20 ordinary checks**, no failed check. Neither the original FAIL artifact nor the earlier derived artifact was rewritten. This is an offline reinterpretation of existing evidence, not another real run or retroactive correction of its original exit status.

Frozen helper SHA256: `8dd020380dec7ed1d0de537eb41e402d6a1ee9d531b833dca635b442b5a28099`.

Frozen test SHA256: `40c79e3d2284442bb0cdfc4b0326e85dd50bc1fe27fd66befd24d07aa895a0b0`.

## Remaining boundary

The candidate result still requires semantic review of the real question, correction and feedback. A correct record transition does not establish correct teaching. A Native receive/playback schedule is not a provider ACK or audible output; `physical_output` remains `UNVERIFIED_NO_LOOPBACK`, `human` remains `PENDING`. No real phase26 correction has been executed by this agent. Main owns CLI integration, deployment, budget and any necessary single authorized real scene.

## Narrow observer wiring review — frozen

Independently read Main's current `neko_daily_voice_probe.py` correction additions and `test_neko_native_grade_probe_plan.py`; no concrete P1/P2 found in this bounded change. `--grade-correction` requires `--grade-current` and rejects `--prepare-grade-quiz` before port preflight. The inherited grade scene still requires output-only, one existing fixed WAV and existing isolated task material, with fresh-task provenance; mixed followup/teaching/replacement/manual modes are rejected. It writes `grade_intent=correction` only for this explicit mode, otherwise `answer`.

Before Native launch, the observer obtains one readonly full acceptance baseline and one readonly question pin, compares course/session/qid/aid/evaluated state exactly, requires snapshot `ok=True`, and selects evaluated True + saved wrong/partial only for correction (ordinary requires False). The pin getter itself requires four nonempty bounded strings and a real JSON boolean; the baseline predicate is intentionally not a replacement for that getter or the later formal-lineage checker. No automatic quiz is created for correction, and the snapshot is not reread per frame. The after snapshot is collected once in cleanup; the finalized report invokes the same conservative acceptance function and exits unsuccessfully on failed checks. Full old formal lineage and topic continuity remain final acceptance checks, not claims made by the lighter preflight predicate.

Independently ran `python -X utf8 -B scripts/test_neko_native_grade_probe_plan.py`: **8 tests PASS in 0.242 s**. The suite compiles actual observer function AST and substitutes a port-constructor sentinel, so even its valid branch stops before a real socket/host/device operation. It covers correction outside grade mode / with preparation, mode-specific evaluated state and wrong/partial/correct last verdict, baseline-pin mismatch, original daily/unproven/missing provenance, single-WAV/output-only constraints, and real rich quiz receipt IDs. It does not exercise the async host/SDK/Native portion or establish a real correction result. No port, provider, DB, device or budget was used by this run.

Reviewed Main observer SHA256: `03e8dcdbc995b3d6777ac6d7e70ae0c3b8a2133ad5f200fa0bf31bc7853ca824`; preflight test SHA256: `95735a5a7eb851ed03e1c063ed8d3323949ef56b1c3d72d00c5d59cc7fd63e67`. The earlier helper/test hashes remain unchanged. This appendix does not claim scene38 runtime, model, audible output or human acceptance.

## Scene38 terminal artifact: empty binary message compatibility — frozen

Main supplied the completed scene38 artifact; this agent performed readonly offline analysis only. Its original FAIL is retained. Before this change, exactly `new_token_pcm_after_grade` failed: telemetry recorded eight binary messages, seven positive PCM frames totaling **378480 bytes** plus one zero-byte binary message. All eight carried the new Native token; the other 21 acceptance checks were true.

Source evidence: `scripts/neko_native_telemetry.py:35` increments `binaryFrames` for every non-string WebSocket message, records `size || byteLength || 0`, and tags it using the last `audio_chunk` correlation local to that socket (line 47). Consequently `audio_frame` is a binary-message observation, not a guarantee that a message contains PCM. Actual deployed `static/app/app-websocket.js:3118` passes binary Blob messages to the audio queue. Actual deployed `static/app/app-audio-playback.js:1840` checks epoch / retired Native correlation, then lines 1843–1845 explicitly skip an absent/zero-length ArrayBuffer, before audio context setup. This establishes empty-message handling; it does **not** identify this particular empty message as a completion marker or a provider ACK.

The checker now requires at least one positive integer-byte PCM frame. Each observed in-window binary frame, including empty ones, still must use the exact new token and be after formal completion / accepted old-token cancellation / applicable old playback stop. Byte counts must be nonnegative integers: negative values, booleans, NaN, infinity, fractional counts, strings and missing counts fail. A zero-byte message cannot by itself prove PCM or allow playback scheduling before the first positive PCM frame. Trace completeness for the fresh-renderer retirement alternative still counts every binary message, including the empty one; it was not changed to discard inconvenient events. All formal identity, old/new attempt, profile, capture and terminal guards are unchanged.

Independently ran `python -X utf8 -B scripts/test_neko_native_grade_acceptance.py`: **21 tests PASS in 0.580 s**. Added coverage allows a properly owned/timed zero-byte tail with positive PCM, rejects empty-only streams, malformed byte counts, old-token / before-completion empty frames, and scheduling before positive PCM. Original 13 ordinary and previous 7 correction tests still pass. Readonly scene37 recomputation still has all 20 ordinary checks true, with its original SHA unchanged.

Scene38 recheck now has **22/22 checks true**, returning `CANDIDATE_GRADE_FLOW_PASS_REQUIRES_SEMANTIC_REVIEW`. The raw formal evidence preserves question identity and old wrong/0 answer while producing a new attempt, correct/100, exactly QA **3→4**, unchanged old hashes/formal rows and matching topic. The recorded question asks the outgoing WEX arrow; the correction's original ASR says WEX→NUD, and the one short Native reply agrees. This is consistency of the recorded question, correction, formal result and reply; this agent did not re-inspect image pixels. Native receive/schedule and source-ended terminal evidence are recorded; physical output remains `UNVERIFIED_NO_LOOPBACK`, human remains `PENDING`.

Original private artifact `benchmarks/raw/evidence/daily-companion-20261015-native-correction38.json` SHA256 remains `c421dc05ef6fa71018ca1c00a3923a0b312ad005d1f3af20f4f4036b582161f8`.

Exclusive-created derived private artifact `benchmarks/raw/evidence/daily-companion-20261015-native-correction38-rechecked.json` SHA256: `1f2837ad9f9ffcd44b160f60fd5654d41b9ecafd532b8f30cd3568aa44571cec`. It records source hash, prior failed check, current checks, counts and bounded semantic conclusion; no raw learner text. Neither original scene38 FAIL nor scene37 artifacts were overwritten. There was no repeat real run.

Updated frozen helper SHA256: `7536c254cf6abcb721fad08b2474b28ea7b5d9038e957ae836d145691cf7aee1`; test SHA256: `706440849689669d47bf51dd6a5b86b9856bd369c555a438c250299aa5bd817d`. These supersede the earlier phase26 helper/test hashes in this report.
