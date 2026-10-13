# Quiz material provenance — stage six, 2026-10-14

Status: source and targeted offline PASS; Native integration/model/device/human acceptance not performed by this agent. Read contract/plan/status/blockers before work. Main agent reports latest ledger 537 DeepSeek / 53 Lanlan.app / 0 tech and feature remote `4a33054`; this agent made no external requests or ledger/process/deployment changes.

## Changed scope

Only these files were changed:

- `patches/neko-study-2026-10-10-product/payload/study_companion/entry_tutor_question_entries.py`
- `scripts/test_neko_quiz_material_guard.py` (new)
- this report (new)

Existing dirty work was preserved. No shared product/helper/fixture/manifest/host file was edited. The main agent separately owns Native wrappers, consumer, answer/summary and shared prompt filtering.

## Delivered behavior

`study_generate_question`, `study_generate_targeted_question` and `_generate_question_payload` accept optional private `_material_context` without adding it to public input schema. Public entries also snapshot scope themselves when it is omitted, before their first await. Session initialization may fill an initially empty session ID only; existing session replacement, course change or relevant material change is rejected with `course_context_changed`.

The resolved context goes into existing context/finalizer as `_material_context`. Checks occur at initial admission, after session ensure, when entering generation, after building context, after model completion, before finalization and before returning. Generated learning context must match the captured course/session. The existing shared finalizer supplies its lock-coordinated material check immediately before SQL append, degraded error-state guard and live question/progress guard; no model/network work runs under the state lock.

For current submitted picture requests, the main wrapper passes captured full image/OCR context plus image payload and OCR. For legacy OCR fallback, the entry captures current full material identity. Explicit text/image input and targeted topic practice default to course/session subset: their supplied source is immutable, so replacing an unrelated saved picture does not invalidate them or pretend that picture was inspected. Topic/text practice without an explicit image overrides automatic saved-picture/old-pipeline vision context with disabled/empty vision. No saved image is added to targeted practice.

Question origin is stored at `current_question['internal_private_payload']['source_material_context']`; interaction metadata also records `source_material_context`, alongside the shared finalizer's `material_context`. Existing public question filtering removes the private payload. Answer hiding, safe hint filtering, question/attempt IDs, selected-topic identity and attempt semantics are unchanged. Targeted practice's existing revision/key check after model and inside its finalization scope lock remains intact. No new generation cache, deduplication policy or memory system was introduced.

A follow-up prompt test reproduced a real nested-history privacy gap: metadata origin hashes reached the next model prompt even though top-level context filtering excluded private fields. The main agent fixed the existing shared `llm_prompts._PROMPT_PRIVATE_FIELDS` to remove `material_context`, `source_material_context`, `_material_context` and `_study_material_binding` recursively. The final passing test verifies both first-call and subsequent-history prompt privacy while Store origin remains present. This shared fix is required integration, not an edit made by this agent.

## Offline evidence

Command:

```powershell
& benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -I -B scripts/test_neko_quiz_material_guard.py
```

Final result: **12 tests, 1.312 seconds, OK**. Tests execute actual canonical quiz methods, actual learning-context/finalizer and existing Store against a fresh temporary SQLite DB. Local async model callbacks supply controlled outputs/races. SDK Ok/Err construction and image payload validation are lightweight fixture boundaries; these tests do not establish SDK transport, real image model accuracy or Native audio delivery.

Covered:

- Successful current-image question: source image reaches model callback, origin survives existing state persistence/reload, public result/history payload hides answers/private origin, first and next prompt omit material hashes/binding.
- Stale supplied full context rejects before any session ensure/model.
- Initially empty sessions may initialize for both entries; already active session replacement rejects. Empty-session course/OCR changes also reject.
- Course/session/image changes during context building or model completion reject without history/new question/live progress.
- A truly suspended async model request completing after course switch cannot overwrite the new course's held question.
- Wrong course snapshot rejects even when current live identity still matches.
- Literal/targeted source ignores unrelated saved vision and survives image-only change.
- Both existing targeted practice scope checks still reject revision changes.
- Replacement just before actual SQL append writes no history; replacement waiting on a short SQL append preserves the committed old history but rejects old return/live seed/question.
- Stale degraded reply cannot set a new-material error or create a question.

Earlier intermediate result: original ten tests passed; adding second-turn privacy test produced one failure (11 tests), which was resolved by the main agent's shared recursive filter. No failures were hidden or replaced with offline claims about real models. Final source diff whitespace check passed. Old complete teaching/audio suites were not rerun.

## Integration and remaining boundaries

Main-owned Native wrapper must capture/resolve material before awaits, pass the full current image context for empty-topic picture quiz and subset for topic/targeted sources, verify returned question/attempt IDs against held state and attach successful binding. Consumer must accept trusted `study_quiz` with `question` as its spoken field, retaining actual connection/scope/provider ownership and stripping host-only metadata. This agent has not deployed or tested those paths.

Grade can read the existing private question origin above, while preserving immutable held-question grading and existing identity/attempt/cache semantics; image-only changes should not relabel or discard that question. Public UI generated questions are now guarded by these entries, not only by the Native wrapper.

Committed history remains committed if replacement occurs after SQL append; no deletion/reset is used. The internal `_generate_question_payload` retains legacy behavior when no private context is passed, for existing internal callers; both public generation entries now resolve a guard themselves. Already queued/sent Native audio, same-material concurrent distinct quizzes and transport cancellation belong to main host/wrapper lifecycle, not this entry-only change. No new claim of real model, device playback or human experience.

All three owned files frozen after final checks; next step is main-agent integration and only necessary affected regressions.
