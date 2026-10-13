# Accepted native Tutor teaching update

This branch extends the published `fix/neko-realtime-barge-in` change with the locally accepted Tutor runtime and teaching fixes. It includes the required avatar/OCR/code-tool modules and launcher dependencies, without publishing unrelated local master history or user learning data.

The accepted behavior covers concept explanations, a calculator addition example, quizzes, wrong/partial/correct grading, targeted correction, pending-question persistence, course-scoped history, and recovery of earlier mistakes after a complete host restart. Ordinary human barge-in and basic human teaching were confirmed separately. A later fixed-WAV scene verified the actual superseded voice-owner heartbeat path and subsequent native output; latest spoken tool contracts were verified with real provider callbacks. These are separate proof layers.

The main fixes are truthful quota/provider failure diagnostics, persisted question IDs, retained course answer records, durable onboarding/configuration, complete playback eligibility receipts, and removal of competing spoken/web output contracts. The product overlay has 20 hash-sealed files; the twentieth is an existing code-tool mixin required by the avatar module and added during publication dependency closure.

The canonical payload and patches are under `patches/`; the source/native launchers and replayable voice patch are under `scripts/`. This repository continues to depend on the local packaged N.E.K.O base and source/runtime dependencies described by the existing patch READMEs and manifests. The ignored `benchmarks/raw` and `candidates` runtime trees are not bundled in this commit. No provider credentials or room audio are included.

Reviewable evidence is in [docs/evidence/tutor-teaching](evidence/tutor-teaching). The JSON exports retain actual teaching outputs, final provider callbacks, the native continuity audit, human stage confirmation, final cleanup, and hashes of their original local evidence files. See the [final acceptance report](evidence/teaching-quality-goal-accepted-2026-10-13.md) for the complete scope, launch shape and limitations. References to full `benchmarks/raw/evidence` captures in historical reports are local provenance, not files shipped by Git.

Offline checks use the existing configured host Python after runtime preparation:

```powershell
python -B scripts/test_neko_tutor_start.py
python -B scripts/test_neko_product_course_memory.py
python -B scripts/test_neko_teaching_failures.py
python -B scripts/test_neko_voice_owner_heartbeat.py
python -B scripts/test_neko_realtime_barge_in.py
python -B patches/neko-study-2026-10-10-product/test_avatar_reply_shape.py
python -B patches/neko-study-2026-10-10-product/test_code_tool_boundaries.py
node scripts/test_neko_native_barge_in_playback.js
```

Some checks read the prepared upstream runtime; a repository-only checkout cannot substitute for that dependency. Published source content is compared with the locally tested files after LF normalization required by repository attributes. The publication manifest seals LF payload bytes and retains accepted local raw hashes where CRLF differed. Replayable scripts also use LF for stable fingerprints.

The last accepted cumulative ledger was DeepSeek 173/300, Lanlan.app 19/30 CONNECT, Lanlan.tech 0, in the same `bargein-autocheck-20261012` round. These are local reservation counters rather than invoice amounts. Future paid tests require current authorization and ledger checks. Microphone/speaker activity must be arranged in advance; automated fixed-WAV inputs can avoid the room microphone.

This update does not claim new human cross-playback-end barge-in coverage, long-term stability, arbitrary future format compliance, diagram vision, or voice identification. Diagram understanding is the next work item.
