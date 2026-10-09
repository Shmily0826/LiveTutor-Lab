# Native desktop tutor on the real N.E.K.O host — 2026-10-09

## Bottom line

| Capability | Status | Evidence |
| --- | --- | --- |
| Real host starts and serves its own plugin server | **VERIFIED on the real desktop host** | [neko-desktop-host-20261009T090253Z.json](../benchmarks/raw/evidence/neko-desktop-host-20261009T090253Z.json) |
| Study Companion loaded by the host (`startup` → entries → `STATIC_UI_REGISTER`) | **VERIFIED** | host log `neko-desktop-host.log`: `[Plugin Process] Starting plugin 'study_companion' …`, `Static UI registered`, `List actions updated: 1 actions` |
| Native Study UI reachable in a browser from the host | **VERIFIED** (`/plugin/study_companion/ui/` → 200, page rendered) | same report (`study_ui`, `study_ui_index`) |
| Continuous **text** tutoring on DeepSeek through the host's own provider path | **VERIFIED, 0 degraded steps** | [session report](../benchmarks/raw/evidence/neko-desktop-tutor-session-20261009T085522Z.json), [browser UI run](../benchmarks/raw/evidence/neko-desktop-study-ui-20261009T090237Z.json) `PASS_DESKTOP_STUDY_UI_TEXT_LOOP` |
| Answer, grading, summary and persistence in the real host | **VERIFIED** (11 host calls, 6 persisted interactions, summary cites the graded mistake) | session report |
| Host audio / egress containment | **VERIFIED as configured + observed**, not proven at binary level | sink allowed only `api.deepseek.com`; denied `community.project-neko.cn` and `118.31.122.91`; zero direct bypass |
| **Real desktop screen teaching** (`active_window` capture) | **NOT DELIVERED — unsafe as implemented** (details below) | guard rejection recorded in the session run |
| Packaged/installed N.E.K.O end-to-end (pet window, TTS, mic, Native Realtime, Proactive) | **NOT STARTED** | — |

Nothing is committed: this round leaves working-tree changes for review. No push.

## How to run it (the product entry)

```powershell
# 1. start the host in a fully disposable app-data tree, text-only, and keep it up
.tmp-uv-cache\neko-study-venv\Scripts\python.exe -B scripts\neko_desktop_tutor_host.py --hold 3600

# 2. open the host's own Study UI:  http://127.0.0.1:48916/plugin/study_companion/ui/
# 3. optional scripted session through the host's plugin /runs protocol
.tmp-uv-cache\neko-study-venv\Scripts\python.exe -B scripts\neko_desktop_tutor_session.py --text "…lesson…"
# 4. stop again
.tmp-uv-cache\neko-study-venv\Scripts\python.exe -B scripts\neko_desktop_tutor_host.py --stop
```

`scripts/neko_desktop_tutor_host.py` owns the safety configuration, so the user does not have to
touch any settings by hand; `--probe` runs the same startup and shuts the host down afterwards.

## Three integration facts found on the real host

These were invisible from the isolated fixture and are the reason the tutor kept failing
`authentication_failed` before:

1. **`NEKO_STORAGE_SELECTED_ROOT` does not redirect the ConfigManager.** The host resolves
   `core_config.json` from `%LOCALAPPDATA%` (`[ConfigManager] ✓ Using app data directory:
   C:\Users\Shmily\AppData\Local`). Pointing only the storage root left the host reading the
   **user's own** settings (`assistApi: free`, no `DISABLE_TTS`), i.e. a provider nobody authorised
   for this test. The launcher now owns `LOCALAPPDATA`/`APPDATA` too, so the whole app-data tree is
   disposable (`benchmarks/raw/neko-appdata`, deleted again after this round).
2. **The `agent` slot resolves through camelCase custom fields.** With `enableCustomApi` on, the
   Study Companion's `get_model_api_config("agent")` needs `agentModelId` / `agentModelUrl` /
   `agentModelApiKey` (`config/api_profiles.py`); `assistApi` + `assistApiKeyDeepseek` alone is not
   enough, and UPPER_SNAKE keys in the file are ignored. Fixed in the launcher; verified the host's
   own gateway then reaches DeepSeek.
3. **A host start does not re-scan plugins.** `study_companion` was registered but *not running*
   (`NOT_READY … Start the plugin via POST /plugin/study_companion/start`), and the UI answered 404
   until `POST /plugins/refresh` + `/plugin/study_companion/start`. Both now happen inside the
   launcher; `preference_persisted:true` means the second launch auto-starts it.

## Host audio / egress boundary, and what it actually caught

Three layers, all in the launcher, plus one observation that does not depend on the app cooperating:

- `DISABLE_TTS: true`, `ttsProvider: ""`, and **no speech or realtime credential at all** in the
  disposable config, so the native-realtime bypass found in the earlier source audit has nothing to
  authenticate with. Proactive and wake word flags off; no microphone path exists in a server-only
  start (the Electron pet window is never launched).
- Every provider call is forced through a loopback sink that tunnels **only** `api.deepseek.com`
  and denies everything else while recording it. It denied `community.project-neko.cn` (a startup
  call the host makes on its own) and `118.31.122.91`.
- A `netstat` poll keyed to the host PID records any *direct* non-loopback connection: **zero**
  observed in both runs, which is also the evidence that the proxy route is honoured rather than
  assumed.

This is containment for these runs, not a binary-level proof: the installed `projectneko_server.exe`
is frozen, so a fail-closed in-code gate (reject + count at the TTS dispatch and the websocket audio
frame) still needs the source-matched build. I am not claiming host-wide mute beyond what was
observed.

Side effects on the user's own profile that I could not redirect, stated plainly: the host writes
`%USERPROFILE%\.neko\bridge.json` and touches `%LOCALAPPDATA%\N.E.K.O\state\root_state.json` /
`state\topic_signals.json`. The user's `core_config.json` was **not** modified (mtime still
2026-08-20, 2 keys, `assistApi: free`).

## The screen-teaching attempt did not pass, and why

`study_ocr_snapshot(capture_mode="active_window")` resolves the **foreground** window
(`entry_ocr_entries.py:37 _foreground_window_target`) and captures whatever is on top. In both runs
the top window was not my synthetic lesson window but the user's own **Save As / File Explorer**
window, so the OCR text mixed the lesson with personal content
(`Save As`, `COMPSCI701 > exercise > w10`, `This PC`, `Xiaomi`, …):

- The captured text is stored by the plugin as `last_ocr_text` and is fed to the model on the next
  explanation, so on the **first** run that personal content was sent to DeepSeek once before I had a
  guard. That is a real privacy event in this round's testing, and the reason I stopped using the
  capture path instead of iterating on it.
- The disposable app-data tree that held it has been deleted; no evidence file, log or committed file
  contains it (grep for the dialog text returns nothing outside the deleted DB).
- The session driver now refuses to use a capture unless ≥3 synthetic-lesson lines are recognised
  **and** no foreign window marker appears; the rejected text is withheld from the artifact and only
  a hash/char count is recorded. That run is in the session report
  (`capture_guard: lesson_lines_recognised 0 … rejected_text_withheld`).

So the product gap for real screen teaching is concrete: capture must target an **explicitly chosen
window** (title/id + its own rect, clipped), must show the user what was grabbed before any provider
call, and must be covered by the same egress boundary. Until then `study_ocr_snapshot` defaults to
`fullscreen`, which is worse, and the Study UI's capture button should not be treated as usable.

## Learning state: fixed and re-checked on the host

The Session Summary defect from the previous round is fixed in the running host
(`entry_tutor_context_support.py`, patch in `patches/neko-study-2026-10-09-ui/`, byte-verified
rebuild chain). In the host session the learner's wrong answer `du = dx` was graded
(`wrong`/partial family with a targeted comment) and the summary then said
*“学习者能设 u=2x+1，但短答中写成 du=dx，漏掉 1/2 因子”* — the graded mistake is now in its own summary.
The browser run, restarted against the same store, produced a summary that still recalled that
mistake, so state reuse across a host restart works; the flip side is that "same session" spans
episodes until explicitly restarted, which is worth deciding on purpose.

Remaining accuracy defect seen in that same summary: it listed practice examples
(`e^{3x+2}`, `e^{5x-1}`) that were never in the material. Summaries can invent plausible extras; the
rubric wording should forbid examples not present in the interactions.

## Measured latency, real host vs isolated fixture

| Step | Real host (ms) | Isolated fixture (ms) |
| --- | --- | --- |
| explain turn (3 calls, incl. routing) | 13,328 / 15,031 / 18,516 | 4,300–6,500 |
| targeted question | 6,140 | ~2,200 |
| grade answer | 11,094 | ~2,500 |
| after-error re-teach | 10,735 | ~4,800 |
| session summary | 18,375 | ~3,000 |
| status / start session / set mode | 32 / 515 / 63 | — |
| browser UI: explain / follow-up / summary | 11,783 / 11,704 / 15,604 | 3,100–6,300 (isolated UI) |

The host path is roughly 3–5× slower for the same model and the same prompts. Leading explanation,
not yet proven: the host route adds its own client construction, token/quota tracking and message
plane per call, and the agent slot may resolve a different `extra_body` (thinking) dialect through
`config/providers.py` than the fixture's host-default. This needs one measured comparison before any
optimisation; nothing was tuned on guesses this round.

## Files this round (all uncommitted)

- `scripts/neko_desktop_tutor_host.py` — product entry: disposable app-data, text-only safety
  config, allow-listed egress sink + netstat audit, plugin refresh/start, `--probe`/`--stop`.
- `scripts/neko_desktop_tutor_session.py` — real-host teaching session over the host's own `/runs`
  protocol, with the capture guard and explicit session id.
- `scripts/neko_desktop_study_ui.mjs` — drives the host-served Study UI (repo's existing
  playwright-core; no new dependency).
- `benchmarks/raw/neko-app/resources/bin/plugins/study_companion/entry_tutor_context_support.py`
  (+ its `plugin/plugins` twin) — session summary scope fix; captured in
  `patches/neko-study-2026-10-09-ui/ui-real-tutor.patch` (now 4 files) with a true pre-image.
- `scripts/test_neko_study_summary_scope.py` — offline regression for that fix (no provider call):
  asserts the summary context keeps every row of its own session and that the graded answer and the
  first lesson are in the summarize prompt. Mock regressions still green: 5/5 focused context tests,
  `PASS_PLUGIN_METHOD_LOOP`.
- Previously **untracked** product code found during review:
  `benchmarks/raw/neko-app/resources/bin/plugins/lab_study_plane.py` and `lab_study_runtime.py`
  (imported by the LIVE plugin entry) had no copy in Git at all. They are now captured byte-identical
  under `patches/neko-study-2026-10-09-ui/host_plane/` (contents unchanged).

## Minimum work left before this is a usable desktop tutor

1. Screen teaching: explicit window target + clipped rect + on-screen preview/consent before any
   provider call; then re-verify with the synthetic window only.
2. Commit the two untracked plane modules into `patches/` (or delete the plane hooks in favour of the
   source-built host patch `host-loop.patch` they were working around).
3. Cut the host-path latency once it is measured (routing call off the critical path; per-call client
   reuse; compare thinking on/off).
4. Audio: in-code fail-closed gate on the source-matched build (reject + count at TTS dispatch and
   at the websocket audio frame), because the current boundary is configuration plus observation.
5. Keep session boundaries deliberate: the persisted active session spans episodes and restarts.
6. Formal installed-host acceptance (pet window, TTS/ASR/realtime/proactive) remains entirely open.
