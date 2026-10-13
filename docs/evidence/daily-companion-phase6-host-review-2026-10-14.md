# Phase-six host allowlist review — 2026-10-14

Review target: unstaged changes relative to HEAD `4a33054` in `C:\Users\Shmily\.codex\worktrees\daily-companion\LiveTutor-Lab`, limited to `scripts/neko_desktop_tutor_host.py`, `scripts/neko_material_audio_patch.py`, `scripts/neko_daily_voice_probe.py`, and new/untracked `scripts/test_neko_proxy_idle.py`. Diff and connected source were read; no tests, host, APIs, audio, ledger or process operations were run. Only this report in the main project was added.

Main reports voice15 text correctly refused by the old-controller route guard, terminal539/54/0; voice16 three-WAV scene was pending during review. No pending or earlier scene is treated as proof that stage-six tools played correctly.

## P2: three-turn loopback duration does not cover the permitted scene duration

Worktree `neko_daily_voice_probe.py:319-320` records a fixed245s loopback for `teaching_chain`. Each of the three input turns can independently take:

- WAV duration plus4s of inserted silence (`332-349`, one second before and three after).
- Up to75s after input completion while waiting for actual end/inactive playback (`360-377`).
- An additional3s settling and snapshot work (`378-401`).

The nominal three-turn bound is therefore **sum(WAV durations) + 246s**, before snapshots/startup jitter. A successful response completing near the third per-turn deadline can produce real Native audio after the loopback has already stopped. This is a reproducible measurement gap from the source bounds; no running voice16 truncation was claimed or inspected.

Smallest fix: read all three WAV durations before host startup and calculate meter duration plus its `communicate` timeout from that bound with a small margin, or impose a shorter explicit whole-scene deadline that cannot exceed the recording window. Final device review must verify that the loopback's actual end covers the last turn's terminal/playback boundary. Do not interpret earlier loopback loud chunks as proof of the final grade/summary. Changes should be made after the current source/online scene is frozen, without rerunning a paid scene solely to extend a recording already sufficient for its actual timestamps.

## No further blocking source finding in the reviewed deltas

- Material binding captures only the exact four trusted plugin tools and current Native provider/connection/batch owner. Quiz validates string `question`; answer/summary/explain validate string `reply`. Degraded/error/wrong-field/stale activation results cannot bind (`neko_material_audio_patch.py:39-109`).
- Trusted noncurrent invocation now returns `stale_study_role_scope` before dispatch; absent invocation still dispatches with explicit empty recipient `_ctx`. Current trusted calls override guessed model context with manager role. Copied arguments preserve original exact-inflight identity; foreign plugins remain outside this rewrite (`273-340`). All four trusted result paths strip host-only binding even when capture is unavailable. This closes the prior stale-model-recipient finding by source inspection; no new SDK/device proof is inferred.
- Existing material controls preserve source/boot/seq/context and actual provider/connection/lease/activation fences. Their one bounded close/connect/listener swap and no-old-PCM behavior are unchanged by the four-tool extension.
- Relay patch changes only established CONNECT sockets to blocking, retaining header/connect20s and existing allowlist/accounting. Pump EOF/error now shuts down both ends before close to wake the paired reader (`neko_desktop_tutor_host.py:713-751`). No timer, automatic CONNECT retry, fake onset, barge-in replay or changed provider was added.
- New socketpair test reads actual tunnel/pump code, mocks only local upstream creation, checks short and21.2s quiet/duplex plus EOF termination. It does not call the named remote host. This review did not execute it or claim its result. Its direct `_tunnel` call bypasses `_handle` spending intentionally, so unchanged `spent` is not independent validation of the budget ledger.
- Fixed text-chain mode now rejects before startup; three-WAV mode requires isolated existing-picture state and forbids mixed follow-up/manual/point/replacement modes. Files are checked before launch; PCM uses the existing authorized stream input rather than bypassing the role/socket routing guard. New post-quiz database check prevents grading a missing/consumed question (`voice_probe.py:83-102,398-404`).
- Abnormal session/character-switch terminal signals stop the bounded input loop. Early failure terminates the loopback and explicitly marks it incomplete, then existing cleanup shuts down task-created Native/host processes; no unrelated pre-existing host is selected for cleanup. `finalized` denotes artifact processing completion, not model/device PASS.

Known source limits were retained rather than classified as fresh P2 defects: blocking established relays rely on peer/owner shutdown and bounded host lifetime; real remote idle beyond the local20s fix is unverified; default-off queued narration remains outside this allowlist review. New three-turn mode has no automatic all-stage device acceptance classifier, so final teaching semantics/attempt history/each output and loopback coverage still require Main's actual evidence review.

Conclusion: one measurement P2 above; no other concrete new trusted-role/binding/relay bug found in this limited diff. Review frozen, production/tests untouched.
