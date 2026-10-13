# First-ASR ordering candidate review — 2026-10-14

Read-only scope: `scripts/neko_study_speech_gate_patch.py`, `neko_late_asr_tool_patch.py`, `neko_voice_host_patch.py`, and `test_neko_first_asr_ordering.py`. Only this report added. No source/tests/manifest/other-report changes, tests, host/API/audio, ledger operations or new agent. Main reports6 new actual-tooling tests, old ordering6 and gate14 passed; this reviewer read their source but did not execute or independently reproduce those results.

## Candidate assessment

The new late branch is narrow: exact free `lanlan_app_gemini` / no server VAD, Study prefix, no completed ASR recorded for this client connection, unconsumed speech, quiet greater than2s and at most8s, not fatal/handoff. It queues before `_start_raw_tool_call_now`, independently of executing tool tasks. Release needs ASR receipt within0.4s, equal captured speech-observation sequence and last-loud timestamp, then host callback readiness and exactly one expected scope advance. Current provider/socket/connection, foreign scope and fatal/handoff are rechecked. Missing ASR and full queue reject this branch without a paid dispatcher call.

No direct owner resurrection found in the new2–8s branch: actual old executing work is still retired normally, and queued work captures a fresh owner only after the expected advance. It does not change PCM/onset/barge-in, add CONNECT, replay audio or alias response IDs. The recorded225ms voice16 order is within the new0.4s branch without globally widening the optional gate's200ms prefix rule.

Two source issues/boundaries require attention below.

## P2: `already patched` can bypass the new helper validation

`neko_late_asr_tool_patch.normalize_ordering_helpers:155-171` deliberately rejects duplicate start/end markers and unknown edited helper bodies; only exact reviewed phase-six SHA256 `1c4daa...` is upgraded, known earlier literals are left for existing replay. This is appropriate fail-closed migration logic.

But `neko_voice_host_patch.state:774-787` only counts whether each expected new hunk occurs, and `apply_to:790-793` returns immediately on `patched`. `normalize_ordering_helpers` is called later at799-800. Unlike playback-feedback validation, `_tools.py` helper validation is absent from `state`.

Constructible source case: retain every canonical new hunk, append an extra old/edited helper block carrying another `# late-asr-tool-ordering-v1` marker. All expected hunk membership checks remain true, so `state` says patched and `apply_to` skips normalizer. The normalizer itself would reject its two start markers. An old later method definition can shadow the correct class method, yet the entry point reports “already patched.” No experiment or file mutation was performed here; this follows directly from the source branch order.

Smallest fix: validate `_tools.py` helper shape with the existing normalizer before the patched early return (or in `state`, while preserving partial/pristine reporting). An ambiguous/unknown body must be rejected without overwriting the file even when canonical hunks coexist. Add one focused duplicated-helper/unknown-helper negative case through actual `apply_to`, not only direct normalizer calls. Keep known legacy replay and the single exact phase-six migration; do not normalize arbitrary changed code.

## P2 inherited boundary: at/below2s the first-input negative fence is skipped

The candidate retains original `ordered` for `0 <= now-last_loud <=2.0`, with `late_ordering` only for `2.0 < age <=8.0`. Captured `input_sequence` and `loud_snapshot` are checked only when `record['late_ordering']` is true, both in `same_connection` and `_begin_raw_input_transcript`. The old nongated ordered branch therefore still accepts an expected scope+1 even if actual new speech changed either captured field.

Concrete trace to cover offline: first connection, no completed ASR, queued Study call at age1.999s or2.000s; actual subsequent speech increments sequence/last-loud but nothing is audible so no physical handoff/foreign retirement occurs; first ASR advances scope once and finishes callback. The record is `late_ordering=False`, so both new negative checks are skipped; it can be dispatched in the advanced scope. At age2.001s, the same mutations reject the candidate. The six new tests initialize age2.117s exclusively and do not cover this branch discontinuity.

This is an inherited ordered-path gap, not evidence that the new2–8s branch itself resurrects retired work. The proposal explicitly does not solve all later fragment/natural-pause cases. Still, documentation must not claim “all first-input/new speech is fenced” from the six tests. Smallest follow-up: apply the negative input-snapshot check to the narrowly identified first-transcript Study wait on BOTH sides of2s, without granting the late exception to later input/prefixes. Decide missing-ASR handling separately and explicitly, since old ordering tests intentionally retain original-owner timeout fallback; do not silently change unrelated tools/providers or relax real barge-in.

## Counter/marker evidence boundaries

- `_voice_handoff_input_sequence` is existing per-speech observation evidence, not an utterance ID. Its change reliably refuses this queue; unchanged sequence+last-loud does not prove which opaque provider call belongs to which ASR fragment. This candidate is a bounded initial-input heuristic, not general input identity.
- The new `_late_raw_transcript_connection` marker records receipt, not callback finish, and prevents later same-connection prefixes receiving this exception. Reused client connection generations separate the marker; callback-ready/scope fences prevent second-ASR promotion. No new field-name collision was found in the four-file scope.
- Strict snapshot equality is conservative: additional VAD-positive tail/real speech observation rejects even if a human might consider it the same sentence. This is safer than adopting newer input, but current source/tests do not quantify real-device rejection rate. No stable proxy input/item ID is invented.
- Neighbor wait is0.4s and callback wait separately bounded2s (optional gate retains its bounded total quiet wait). A225ms controlled timing pass does not establish correctness when ASR is missing, reordered across two genuine inputs, or delayed beyond bounds.
- The new fatal/handoff arrival rejection applies to exact free/no-VAD Study even with gate off; source preserves earlier tool retirement. New test mutations cover speech/counter/foreign/connection/socket/second-ASR/fatal/handoff in the late branch, but model/SDK/SQLite and actual device playback are not established by this test file alone.

Review result: source supports a focused voice16 ordering repair in its declared2–8s initial-input range. Address the normalizer entry-point bypass and keep the inherited2s branch limit explicit or close it with a narrow follow-up. No new model/device/human acceptance, deployment or online evidence was produced. Report frozen.

## Follow-up: stage-seven repairs reviewed, both original P2s closed in scope

Read-only follow-up covered the same four files plus `test_neko_late_asr_tool_patch.py`. Main reports new8 tests PASS; this reviewer did not run tests or start any service. Only this section was appended, with prior findings preserved as history.

**First-input boundary resolved.** The first-transcript Study predicate now covers age0–8s, including both sides of2s. When eligible, it sets `late_ordering=True` even when the legacy `ordered` predicate also matches. Captured sequence/last-loud checks therefore apply at ASR receipt and before dispatch for age1.999/2.000/2.001 alike; missing ASR/full queue also retain no-paid abandonment. The new boundary test explicitly iterates those ages plus2.117 with speech/counter/missing-ASR mutations. This closes the earlier first-input discontinuity for the declared eligibility scope.

Eligibility now additionally requires a known connection-attachment foreign-scope baseline equal to the current foreign-scope value. `neko_late_asr_tool_patch.py:183-187` installs that baseline immediately after `_on_connection_attached`, before subsequent connection setup, and the predicate refuses a missing or changed baseline. Foreign retirement before a call cannot borrow the initial exception; foreign retirement after admission is still checked against the queued record. The test harness initializes this baseline explicitly and the new pre-call foreign test verifies no initial exception. No changes to ordinary onset/PCM or already executing task retirement were added.

**Normalizer early-return resolved.** `neko_voice_host_patch.state:778-786` calls `normalize_ordering_helpers` for `_tools.py` before checking canonical hunk membership. Ambiguous/unknown helpers now raise before `apply_to` can reach its `already patched` return; a reviewed legacy migration is reported partial and then normalized in the normal apply path. Canonical helper stays idempotent. The normalizer accepts the two exact reviewed fingerprints (phase-six and prior reviewed stage-seven candidate), existing known literal replay paths and current canonical body; no arbitrary edited helper is accepted.

The added `test_actual_apply_validates_even_canonical_hunks_and_preserves_unknown_files` uses actual `state/apply_to` on a temporary `_tools.py`, checks canonical second apply, then duplicate-marker and edited-constant inputs with byte preservation. Its source covers the entry-point bypass case rather than only testing the standalone normalizer. Execution PASS remains Main's reported evidence.

No further blocking source finding was identified in this limited re-review. This does not extend the compatibility exception to later already-transcribed inputs, post-foreign legacy fallback, quiet beyond8s, or the general fragmented/natural-pause problem. Equal speech counters still supply negative replacement evidence rather than a stable provider input ID. Model, SDK/device quiz speech, ordinary human interruption and deployment remain separate evidence layers; none were newly verified here.

Follow-up report frozen; source/tests/manifest/shared records unchanged by this reviewer.
