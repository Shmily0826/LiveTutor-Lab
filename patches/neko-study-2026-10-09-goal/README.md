# 2026-10-09 Study Companion partial portable overlay

This bundle contains a reproducible patch for the five teaching-context files whose exact preimages were preserved in the round-two handoff. `preimage/` is the reviewable base snapshot; `manifest.json` pins the preimage SHA-256 and the current runtime postimage SHA-256. The patch builder checks that the three current source roots have identical postimages for each included file.

This is a **partial** patch. It carries the material grounding, scoped session history, programming-topic classification, and prompt changes. The mute gates, session lifecycle/schema changes, direct command path, and grading normalizer do not have verified original preimages in this workspace and are deliberately not represented as a portable diff.

Regenerate and verify a candidate target before applying. The smoke check applies the patch to a disposable copy and compares file contents after newline normalization; Windows CRLF preimages may keep CRLF, so their byte hashes can differ from the LF runtime snapshot.

```powershell
& 'benchmarks/raw/goal-python/cpython-3.11-windows-x86_64-none/python.exe' -I -S scripts/build_neko_goal_partial_patch.py
& 'benchmarks/raw/goal-python/cpython-3.11-windows-x86_64-none/python.exe' -I -S scripts/build_neko_goal_partial_patch.py --smoke-apply
& 'benchmarks/raw/goal-python/cpython-3.11-windows-x86_64-none/python.exe' -I -S scripts/build_neko_goal_partial_patch.py --verify-target <plugin-root>/plugins/study_companion
git apply --check --directory=<plugin-root> patches/neko-study-2026-10-09-goal/goal-context.patch
git apply --directory=<plugin-root> patches/neko-study-2026-10-09-goal/goal-context.patch
```

Replace `<plugin-root>` with a disposable source checkout's plugin directory. The verifier refuses any file whose SHA-256 differs from the preserved preimage. Review the diff and target checkout before applying. This bundle contains source only; it does not touch plugin databases or runtime configuration.
