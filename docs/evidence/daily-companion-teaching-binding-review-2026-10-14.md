# Stage-six teaching binding review — 2026-10-14

Read-only scope: new canonical answer entry, three Native wrappers/helpers, material-audio patch's trusted four-tool dispatch/binding, and necessary shared context/finalizer fragments. Only this report was added. No product/test/manifest/ledger/process changes, deployment, host, online model, audio, or new agent.

Main reports grade7 / integrated Native5 / Core31 / affected failure5 offline PASS. This review did not rerun those suites. It used four small in-memory probes of actual methods with the existing offline fixture classes, fresh temporary SQLite and owned local mocks. No provider calls. Findings describe source/local reproduction, not observed model/device accidents.

## P2 findings requiring integration fixes

### 1. Immutable held-question grade still receives the newly saved picture

`entry_tutor_answer_entries.py:75-79` correctly declares ordinary grading an immutable-question operation with course/session subset. However its learning-context extra at `228-263` only specifies vision fields when caller supplies `vision_image_base64`; otherwise it does not override default vision. Shared `_build_learning_context:781-801` then automatically attaches the latest saved image or pipeline snapshot and latest OCR is already in the context (`687-688`). A held image-A question graded after selection of image B is thus sent to the model with image B, while Native binds the returned grade to a subset with no image identity.

Actual local Native-wrapper → entry → context/model probe with `llm_vision_enabled=True` and held A question produced:

```json
{"case":"immutable-held-native-grade","vision_enabled":true,"received_new_image":true,"received_new_ocr":true,"bound_subset":true}
```

The model stub still returned the expected fixture verdict, so this is evidence of wrong inputs, not a proven wrong real-model grade. Existing picture-only grade test preserves `expected_answer`/origin but does not detect the extra current-image input.

Smallest fix: ordinary grading explicitly sets disabled/empty vision and clears unrelated current OCR/snapshot in extra context, as immutable-source explain/quiz already do. Only explicit current-picture grading should receive its captured image and full material context. Retain held question/expected-answer/source origin and course/session guard; do not invalidate immutable grading merely because saved image changed.

### 2. Public grading return/event has no final held-question identity fence

Initial question/attempt validation and reservation are real (`90-139,195-215`). The later cache update correctly refuses to mutate a new attempt (`342-354`). Native `_study_bind_native_teaching_result` additionally checks captured question/attempt before speaking/binding (`study_avatar_tools.py:932-943,1053-1054`), so the main's Native late-question negative test is valid.

But direct public `study_evaluate_answer` checks only course/session/material after the model and around feedback/return (`265-297,374-393`). A new question in the same session leaves these guards satisfied: old grade is returned as success and `_emit_answer_evaluated_event` receives old feedback. The outer Native guard cannot protect UI/direct entry callers or an already queued event.

Actual entry/finalizer/SQLite probe replaced q-old/a-old with q-new/a-new during the local model callback:

```json
{"case":"direct-grade-late-question","returned_old_success":true,"new_question_preserved":true,"old_feedback_emitted":true}
```

Smallest fix: when using held question, check BOTH captured question ID and attempt ID under the existing state lock before feedback and final public return; reject late delivery if replaced. Preserve the immutable old-question history/QA that has already committed and the current cache/reservation guards. Do not delete history or mark the new attempt evaluated. This can intentionally retain old grade history while suppressing its current-answer delivery.

### 3. Empty active session plus supplied `session_id` can write foreign history without ensuring a session

`entry_tutor_answer_entries.py:217-227` trusts nonempty `kwargs['session_id']` enough to skip `_ensure_active_study_session`. When captured active session is empty, both session mismatch checks are conditional on nonempty original ID. `expected_material` is then replaced with the still-empty current context, while `_build_learning_context`/finalizer use caller's foreign session ID. Shared finalizer checks current material at commit but never equates `extra_context['session_id']` to `_material_context['session_id']` (`entry_tutor_context_support.py:919-942`).

Actual fresh SQLite probe after ending the active session, using a supplied immutable question and `session_id='caller-foreign-session'`, returned:

```json
{"case":"empty-session-caller-session","returned_success":true,"active_session_still_empty":true,"foreign_history_count":1}
```

This entry schema does not advertise `session_id`; the issue requires extra entry kwargs, not the normal Native wrapper (which ensures scope first). It is nevertheless a reproducible history-integrity hole in the real public method.

Smallest fix: always resolve the active request session through ensure, allow initially empty ID initialization only, then require any provided session ID and built context course/session to equal that resolved scope. Do not adopt arbitrary caller session ID when no active session exists. Keep append-history semantics and existing Store.

### 4. Stale/absent trusted tool dispatch preserves model-supplied recipient `_ctx`

Current trusted invocation is correctly copied, injected with only manager role, and never mutates original model arguments used by exact-inflight sharing (`neko_material_audio_patch.py:273-301,318-320`). Allowlists and `spoken_field` are exact; `study_quiz` binds `question`, others `reply` (`39-99`). Trusted result binding is stripped even when capture fails (generated execute fragment `303-316`), and foreign-plugin dispatch is left alone.

However trusted four-tool dispatch with absent/stale `invoking_session` skips trusted role injection and forwards the original call unchanged. If original arguments contain a guessed `_ctx`, it reaches the producer's `material_output_target`; successful wrapper binding can register that guessed recipient in its runtime output-target map even though this Core refuses Native binding. Existing stale-source test uses empty arguments, so it does not cover this variant.

Actual patched `_on_tool_call` probe with a foreign owned fake Provider and `study_answer` arguments containing `_ctx.lanlan_name='ForgedRole'` produced:

```json
{"case":"stale-tool-role","forwarded_forged_role":true,"no_native_binding":true,"binding_stripped":true}
```

No audio cancellation/foreign-role playback was demonstrated: the host ownership refusal and binding strip work. The risk is producer recipient-map contamination and misdirected later control submissions from a stale tool path.

Smallest fix: for the exact trusted plugin/tool allowlist, copy arguments and remove/replace model `_ctx` regardless of current-owner eligibility. If stale/absent, either reject dispatch or supply an empty `_ctx` that prevents private fallback from guessing a recipient; do not assign the current manager's role to stale work. Preserve original call args and leave other plugins unchanged.

## Retained protections / nonfindings

- Current trusted role overrides model `_ctx`; four exact tool names and plugin source prevent unrelated read-only tools or foreign plugins from acquiring teaching output ownership.
- Invalid/degraded/failed result and wrong spoken field cannot bind. Original args are preserved by copied dispatched call. Real connection/provider/batch owner/current activation fences remain present.
- Native answer wrapper checks stored private origin's course, uses held question/attempt IDs and binds only current request subset; image replacement does not silently relabel the held question. New Native quiz wrapper carries full current image/OCR context for empty-topic saved-picture quiz and subset for topic practice.
- Existing initial identity validation, pending reservation, duplicate-grade/cache recovery, attempt-guarded cache update and exception/cancellation reservation cleanup remain. Already committed old history is retained; this review does not request deletion or another Store/memory system.
- Shared finalizer's lock-coordinated SQL append, material check and session-bound live-seed guard are inherited. These do not by themselves validate arbitrary caller history scope or final question identity.
- Separate EventBus queue provenance remains a previously documented independent/default-off boundary; not audited broadly or claimed fixed here.

All four probe results came from one isolated Python `-I -B` stdin script using `test_neko_answer_material_guard.GradeHarness` / `test_neko_material_audio.Harness`; no new executable artifact was written. Scope frozen after report. Main may add focused regressions/fixes and then perform SDK/model/device integration separately.
