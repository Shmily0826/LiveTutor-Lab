# Phase 29 — specific error diagnosis prompt review

Status: **SOURCE REVIEW ONLY**. Independently read the new seven-line rule 4b in canonical `patches/neko-study-2026-10-10-product/payload/study_companion/prompt_templates.py:187` and its immediate evaluation/system/language requirements. No concrete P1/P2 or conflicting instruction was found within this small change. No implementation, shared records, tests, provider, host, audio/device, DB or budget was changed or run.

The addition addresses scene40's observed mismatch directly: an answer about WEX→NUD to a NUD→REZ question identifies a different arrow; a true reversal of that requested arrow is REZ→NUD. Rule 4b defines reversal by the same two supported endpoints in opposite order and requires an exact supported comparison before using that diagnosis. It also covers selecting a different node, function or step without forcing those unrelated mistakes into a direction label.

Compatibility checks:

- Existing rule 4a still distinguishes explicit contradiction from omission. Rule 4b refines **which contradiction/mismatch** is present; it does not reclassify every wrong selection as an omission, forbid naming a supported contradiction, or force a reversal label when an endpoint/step is absent.
- The existing evidence limits remain: system prompt says judge only supported context; rule 4a requires supplied diagram/question evidence rather than identifier order or invented return flow; rule 11 uses the expected answer and current question without inventing facts. New 4b reinforces these limits by requiring an honest insufficient-evidence statement instead of a fabricated cause. The same-endpoint definition is a necessary comparison rule, not permission to invent an unseen directed relation.
- Applying the distinction to feedback, misconceptions and step_feedback avoids correcting only one visible sentence while retaining an inaccurate diagnosis elsewhere. No JSON key, verdict enum, score range, coverage/omission scoring rule or math-equivalence claim was changed. Short, direct, actionable feedback and the existing next teaching step remain required.
- `STUDY_STRUCTURED_LANGUAGE_TEMPLATE` still requires every natural-language field in the selected language. English wording of the instruction and error-category examples do not require English learner-facing output; no language override or new language-specific exception was added.

This prompt cannot itself prove reliable model compliance, image reading, concise feedback, or consistency across all output fields. Main's planned bounded silent model check should distinguish a genuine same-endpoint reversal from a different selection and from missing/insufficient evidence; it must examine all relevant feedback fields rather than only verdict/score. The prior phase28 Native/ASR/owner tests need not be repeated for this prompt-only change. Scene40's historical semantic PARTIAL remains unchanged.

Reviewed canonical `prompt_templates.py` SHA256: `01fb645b91dff762fddfe8924c2b8d18833cb5ddbff87e39af7c5d0ce62f7099`. Any real model outcome belongs to Main's later evidence, not to this source-only review. Physical output and human acceptance are outside scope. Review frozen.

## Model41 follow-up: semantic credit and source selection

Main reports the original model41 artifact remains FAIL: different-arrow / reversed-arrow cases were correctly distinguished, but the correct concise relation was scored partial/60 for not literally labeling the start, and a temporary Chinese request was rejected before the model because a time modifier plus an arrow noun was treated as a picture reference. This reviewer did not independently open that raw artifact; these are Main's supplied findings, not results of the offline checks below. They do not erase model41's original failure or make scene40 fully accepted.

Independently reviewed only Main's new rule 4c, current-picture predicate change and the new explanation-language test method. No concrete P1/P2 was found within this bounded change:

- Rule 4c gives semantically equivalent concise content the same credit: “A points to B” already specifies its start and end. It prohibits manufacturing a missing rubric point solely because the words start/end were omitted, while retaining explicitly required additional explanation. This complements 4a/4b's specific-mismatch diagnosis and does not remove 7a's penalty for genuinely missing rubric content or 7b's requirement for a correct relevant fact before awarding points. It does not claim symbolic verification or prescribe a score without source support.
- `study_explain_tool` now sets current-picture intent from its explicit picture-reference predicate rather than a separate broad combination of any temporal/deictic term and any visual noun. The reviewed “这一次 / 这次 / this time” inputs therefore retain supplied relation text and select only a temporary requested language. Actual contiguous visual references include “这条箭头 / 那条箭头 / this arrow / that arrow”, and current-picture requests continue to discard stale summary text and fail honestly when image context is missing. Existing explicit source-choice conflicts, rejection of pictures, literal identifiers and original material/session/queue guards remain present. This is coverage of the specified language forms, not a claim to disambiguate every possible natural-language reference.

### Independent authorized offline checks

Ran with `benchmarks/raw/neko-product-host/.venv/Scripts/python.exe -X utf8 -B`:

- `scripts/test_neko_explanation_language.py`: **5 PASS**, 0.379 s. Actual avatar wrapper methods with existing temporary SQLite preferences and a fake explanation backend; the new method verifies all three temporal modifiers preserve relation notes and temporary language, restores course/default language, and requires visual-context-missing with no backend call for genuine picture references.
- `scripts/test_neko_native_material_guard.py`: **25 PASS**, 2.919 s. Actual wrapper/guard methods with offline fixture seams cover current image binding, old-summary discard, changed material/session, queue/SQL races, ambiguous correction, literal code / image identifiers, rejected pictures and explicit source conflicts. The new language scenario is included through the harness. Fixture messages about cancellation submission being unavailable are not real runtime cancellation evidence.

These are offline tests, not another model41 run, live image analysis, SDK/provider request, Native playback or human acceptance. No application host, online call, device, ledger or shared status/plan was changed. Main owns the bounded follow-up for only the two failed model cases and restart behavior; previously passed arrow-diagnosis or phase28 voice chains need not be repeated for this patch.

Final reviewed SHA256, superseding the earlier prompt fingerprint:

- canonical `prompt_templates.py`: `89dbaaf7540a5cd1dae6e5a1a068ab764c2c398053fa984111852e53be74181a`.
- canonical `study_avatar_tools.py`: `848abd960be3db3834575429a295e2efcb68e13e25d7f7847bc21aea994f4db0`.
- `scripts/test_neko_explanation_language.py`: `deeee312843986b27f168eda9b294617de17a5b995f884d862268239b6e4dc89`.

Follow-up review frozen at SOURCE / OFFLINE. Model compliance, physical output and human experience remain distinct pending evidence.

## Temporary-language no-save parser follow-up — one P2 found

Main reports original model42 exit0 but semantic PARTIAL: correct concise NUD→REZ now correct/100 and restart English/course/QA continuity passed, while temporary Chinese still returned English. Its diagnosed source issue is the prior global `长期` scope check treating an explicit **refusal to save** as a persistent request. This reviewer did not open/rewrite that raw artifact or treat its helper exit0 as full acceptance.

Independently reviewed the new parser-only copy transformation and sixth language test. The source preserves the original request supplied to the backend and strips only from a separate matching body; the intended no-save Chinese and English examples now select one-turn Chinese while cfg/course/DB preference are restored to English. Explicit positive long-term and language-negative fixtures remain in that test.

Command `.\benchmarks\raw\neko-product-host\.venv\Scripts\python.exe -X utf8 -B scripts/test_neko_explanation_language.py`: **6 PASS in 0.434 s**. These remain actual wrapper + temporary SQLite with fake teaching backend, not a model or host/device run.

**Concrete additional P2, sent to Main:** the new Chinese exclusion permits up to forty arbitrary clause characters between `不要/别/不用/无需/不必` and `保存/记住/存储/设为/记为`. It therefore swallows a positive reminder to persist language, e.g. `这次用中文；不要忘记以后用英文并保存为长期偏好。` or `这次用中文；不要忘了以后一直用英文并保存成长期偏好。`. A pure AST execution of only `_COURSE_LEVEL_REQUEST`, `_TURN_LANGUAGE` and `_turn_language_request` returns `zh-CN` for both; the positive future-course request should keep this one-turn parser's return empty and go through the existing course-language path. Before the new deletion, `以后/一直/长期` correctly prevented one-off admission.

Minimal repair is to restrict the negative-saving grammar (reviewed object/把 constructions rather than arbitrary intervening verbs), or at least refuse positive `不要忘记/不要忘了/别忘` reminders from this deletion, then add a mixed temporary + positive-long-term regression while retaining the exact model42 no-save case and English variants. The English negative-save grammar requires the save verb immediately after its negation and does not exhibit this particular gap. No production edit was made by this reviewer; closure remains pending Main's narrow repair. No online, host, device, budget, shared-state or model-repeat action occurred.

## Final parser repair closure and independent41/42/43 evidence read

The reminder P2 is **closed at SOURCE / OFFLINE level**. The Chinese parser now requires the negation to directly precede a saving verb (allowing only the reviewed 再/也/长期/永久 modifiers), or an explicit 把/将 object construction before that verb. It no longer consumes arbitrary intervening verbs. `不要忘记`, `不要忘了` and `别忘了` positive future reminders therefore remain visible to the existing course-level guard. The original no-save request and English no-save variants still select temporary Chinese and preserve remembered English state; no original backend request text is rewritten.

Independently reran the six-test language suite with the existing host Python: **6 PASS in 0.435 s**. The sixth test now includes all three positive-reminder counterexamples and the previous positive long-term / negative-language cases. This is actual wrapper/temporary-SQLite behavior with a fake teaching backend. Final canonical avatar SHA256 is `01a145791e184ccfa9fcf172d37f463b9fcc29853263dabb143ba5b4d0cfe432`; final language test SHA256 is `b2d8689f86d9ae22eef4a485246df98e057e59c8f299e21e586218a2a283c295`. These supersede the earlier avatar/test hashes in this report. No remaining concrete P1/P2 was found in this bounded final parser change.

Independently read only the relevant step results and snapshot identities/hashes in Main's original task artifacts, without reading full knowledge guidance or rewriting artifacts:

| Original artifact | Independently confirmed outcome | Limit |
| --- | --- | --- |
| `daily-companion-20261015-semantics41.json` | Adjacent WEX→NUD answer to NUD-outgoing question: wrong/0, feedback and misconceptions identify a different arrow. REZ→NUD: wrong/0, misconception correctly identifies reversed NUD→REZ endpoints. English explanation is two sentences. | Correct NUD→REZ was still partial/60 for not explicitly labeling start/end; temporary Chinese was degraded visual_context_missing. Original FAIL remains. |
| `daily-companion-20261015-semantics42.json` | Correct concise NUD→REZ: correct/100, no missing points, explicit equivalent-content feedback. Original three QA hashes preserved; post-grade fourth QA and remembered English course are identical after restart, with a two-sentence English explanation. | Temporary-Chinese step actually replies in English despite its request, so semantic PARTIAL even though Main's harness exits0. |
| `daily-companion-20261015-language43.json` | Same full temporary-Chinese/no-save request receives two Chinese sentences; next default request receives two English sentences. Both complete step snapshots equal the original four-QA/course-English snapshot, which equals42's after-restart snapshot. | This real path used the earlier no-save parser fingerprint, not the final reminder-tightening source. It proves these recorded positive language transitions; final reminder protection remains source/offline only. |

For42, independently compared before_restart==after_boot==after_temporary; verified every original QA hash is retained in after_grade; verified after_grade==after_restart. For43, both recorded step snapshots exactly equal before_snapshot, including all four QA hashes, course and course-English map. Its first actual request is the same reviewed Chinese sentence ending in refusal to save as a long-term preference. Replies are semantically about NUD→REZ, with WEX→NUD correctly described as arriving rather than leaving.

Original SHA256 values independently verified:

- semantics41: `f36545263ab5dd4bb726de0264935b79d676566faf56209f6dfebdefd63f3867`.
- semantics42: `26610cdee7ef9002b8ad35bd981e43d06833b2ba340b7d9f0a772f5f761df218`.
- language43: `d26ba02a523033a0d48d82e2ee1bbbd8a10b22ead50ade9990c3624a0af95f77`.

The originals retain `semantic_result=PENDING_REVIEW`; these written human-readable conclusions do not mutate their historical result fields. All three explicitly record audio/avatar/microphone/capture/loopback=False. This reviewer did not start or replay any real scene or inspect devices, accounts or the ledger. Main's harness exit status is distinct from child-host fields (43 records host_exit=1); no blanket clean-zero process-exit claim is made from the result text. Source41/42 original shortcomings are preserved,43 is the bounded real positive path, and final reminder tightening is strictly offline. No three grading cases or restart scene was repeated. Review frozen.
