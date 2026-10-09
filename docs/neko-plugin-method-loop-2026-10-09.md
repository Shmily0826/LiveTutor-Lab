# Isolated Study Companion loop — 2026-10-09

## Result

`PASS_PLUGIN_METHOD_LOOP` at **2026-10-09T01:30:16Z**. The fixture instantiated the genuine extracted `plugins.study_companion.StudyCompanionPlugin` from the raw resource tree, paired with the candidate N.E.K.O SDK runtime. The plugin `__init__.py` SHA-256 is `4825aaf2195f8b33a581f6e7de08efd7bce04e0b47cd4c776b15ab340c84cbeb`.

This is real plugin-method execution with a local deterministic agent double. It is not a host launch, packaged/frozen N.E.K.O safety result, live model grading, OCR, or genuine browser UI E2E.

## Plugin method trace

- Synthetic lesson: `例题2：计算 ∫x·e^(x^2) dx。令 u=x^2，则 du=2x dx。`
- Called methods: `study_start_session` → `study_explain_text` → `study_explain_text` with the literal `为什么例题2有1/2？` → `study_generate_question` → `study_evaluate_answer` → `study_get_session`.
- The follow-up call context contained the earlier Example 2 lesson. Its response explicitly used `du=2x dx`, `x dx=du/2`, and the `1/2` coefficient. The fixture rejects the response if these details or the exact earlier material are missing.
- Every local agent-double context used session ID `study-3e8c39be1256477db110d37c2b1d0abe`; the persisted session record and all four interaction rows used the same ID.
- Mastery for `u-substitution` moved from `0.0` to `0.6189` after answer evaluation. The deterministic agent double returned `correct`, score `100`; this is not evidence of model grading or reasoning quality.
- SQLite opened only the unique project-ignored `.tmp-uv-cache/neko-study-method-fixture/run-*` store (`sqlite_temp_opens=3`). No production or user study database was configured.

Timestamped, sanitized runtime proof: [neko-study-plugin-method-20261009T013016Z.json](../benchmarks/raw/evidence/neko-study-plugin-method-20261009T013016Z.json). It includes the plugin fingerprint, session/interaction consistency, mastery pre/post values, blocked-attempt counters, downstream counters, and safe metadata for config/data-like file reads. The recorded config/data reads were extracted-plugin i18n and knowledge-seed resources. The fixture does not claim that every project file read was blocked or that no project config was read; no file contents or config values are recorded.

## Isolation evidence and limits

Before plugin construction, the fixture stimulated blocked provider import, socket connection, and audio-sink routes. Blocked attempts: provider import `2`, network `1`, fixture audio sink `1`. Provider/socket/audio downstream counters were all `0`; outside-root reads, writes, directory writes, and SQLite opens were `0`, `0`, `0`, and `0`. The three real SQLite opens stayed inside the isolated fixture subtree. The runtime also blocks process creation and provider, speech, audio, and capture imports before plugin import/instance creation.

The audio evidence is an offline fixture sink plus source-level import guards. It does not establish a host-wide mute or packaged N.E.K.O audio safety. No OCR/capture, microphone, audio playback, live provider, model call, or API credential was used.

The earlier import-only probe's denied outside-file attempt was characterized using safe metadata only: user-profile path class, config/data suffix class, caller `config.network._read_port_overrides`. The path and contents were not retained or read. Fixture-local `APPDATA`, `LOCALAPPDATA`, and storage-root environment values point into ignored temp; no operating-system settings were changed.

## Shipped UI browser flow

`PASS_SHIPPED_STATIC_UI_PLUGIN_LOOP` at **2026-10-09T01:42:51Z**. The adapter served the extracted Study Companion static assets on loopback and mapped the shipped `/runs` create/poll/export protocol to allowlisted methods on the genuine extracted plugin instance. A temporary, headless Chromium context held the page through asynchronous UI actions and reload. It used the Playwright Core dependency already bundled with the shared web-inspector tool; nothing was installed and no user Chrome profile or tab was opened.

The plugin's legacy `u_substitution` seed lacks the stage fields required by the current practice-scope validator. The isolated fixture therefore inserted one synthetic calculus topic through the extracted store API, called the real `study_set_practice_scope`, and used the real targeted-question path. The browser-driven UI then performed:

1. Visible initial explanation of `例题2：计算 ∫x·e^(x^2) dx。令 u=x^2，则 du=2x dx。`
2. Contextual follow-up `为什么例题2有1/2？`; the actual plugin method and local agent double produced a response using the previous example and its `du=2x dx` factor.
3. A targeted practice question, answer submission, and visible `correct / 100` evaluation.
4. Session summary, page reload, and a second summary using the same persisted session.

The timestamped proof is [neko-study-plugin-ui-20261009T014251Z.json](../benchmarks/raw/evidence/neko-study-plugin-ui-20261009T014251Z.json); the sanitized final-state screenshot is [neko-study-ui-dom-flow-20261009T014251Z.png](../benchmarks/raw/evidence/neko-study-ui-dom-flow-20261009T014251Z.png). It records session `study-661f756924004ed9881d7afd6b7587c1`, nine persisted interactions with matching session IDs, and synthetic-topic mastery `0.0 → 0.6189`. The proof only reports PASS after all required UI events, page-reload reuse, persistence checks, and browser-gate counters passed.

The proof timestamp is `2026-10-09T01:42:51.863741+00:00`; it records the extracted plugin fingerprint above and the ordered entrypoint sequence. The UI path exercised these distinct plugin entrypoints: `study_status`, `study_memory_list_decks`, `study_get_practice_scope`, `study_explain_text`, `study_question_context`, `study_generate_targeted_question`, `study_evaluate_answer`, and `study_summarize_session`. Fixture setup also inserted the synthetic topic and called `study_set_practice_scope`. The JSON stores no individual `/runs` correlation IDs, so it supports the ordered method trace and session ID, not per-visible-action `/runs` correlation.

The proof records the DOM milestone names and timestamps (`initial_explanation_visible`, `contextual_follow_up_visible`, `plugin_question_visible`, `plugin_answer_evaluation_visible`, `persisted_session_summary_visible`, then `same_plugin_session_reused_after_ui_reload`). The PNG is a readable 1280×2552 PNG of the synthetic Study Companion page after reload; it is a final-state capture, not a frame-by-frame record. At verification, its SHA-256 was `7323332AA9450E8323B5554F276B4EE7784902C6F67337761DB5BE4EF6C8BAF8`; the JSON SHA-256 was `2197481FF19037BA809E1109F6F38A0574402D5D41E713FC224A39424F2E10EE`.

Before navigation, the fresh headless browser context allowed requests only to the adapter's loopback origin, blocked service workers, granted no permissions, and launched with per-process audio muted. The page's own fail-closed guards were stimulated once per page phase: AudioContext, speech synthesis, media play, microphone, WebSocket, and external fetch each recorded attempted `1`, blocked `1`; the browser request interceptor observed zero non-loopback requests. Console and page errors were empty. The adapter's provider/socket/audio/WebSocket/external-fetch downstream counters were all zero. The loopback server was stopped afterward; a follow-up check found no listeners on any fixture port.

This is genuine DOM-driven interaction with the shipped static UI and extracted plugin methods, but it still uses a deterministic local agent double. It is not a live model/OCR result, packaged/frozen app test, or proof of host-wide mute. No OCR/capture, live provider, API credential, microphone access, audio playback, or N.E.K.O host lifecycle was used. The adapter's `/runs` routes called the actual extracted plugin entrypoints under the fixture; the mock `/runs`-only UI fixture is not the evidence source for this result.

The one-off browser-control script was created under the OS temporary directory for that run and was removed; it is not a checked-in reproducer. The saved adapter command below reproduces its server side. Reproducing browser control requires the same fresh headless Chromium context using the shared web-inspector Playwright Core, with loopback-only request routing, service workers blocked, no permissions, per-process audio mute, and the page-side sink guards stimulated before UI actions. No browser dependency was installed in this repository.

## Synthetic OCR bridge

`PASS_NORMAL_OCR_ENTRYPOINT_AND_PLUGIN_CONTEXT` at **2026-10-09T02:42:50.630Z**. This is `PLUGIN_METHOD` evidence: a synthetic Pillow raster was supplied through the extracted plugin's normal `study_ocr_snapshot` entrypoint and then into real extracted Study Companion explanation methods. It is not a browser-capture or full UI E2E result. This supersedes the earlier OCR bridge run below, which called the pipeline directly and manually populated plugin OCR state.

The harness [`neko_study_synthetic_ocr_fixture.py`](../scripts/neko_study_synthetic_ocr_fixture.py) generated a 1500×760 synthetic Example 2 image (SHA-256 `904b5368f80fc509f6648f457e0d8cac9d118227de7178c6c88d0e7ae2e1fe5b`) inside the ignored fixture temp directory. Before plugin construction it replaced only `plugins.study_companion.entry_ocr_entries.capture_interactive_region` with a stub returning that in-memory image. It invoked `StudyCompanionPlugin.study_ocr_snapshot(capture_mode="interactive", allow_fullscreen_fallback=False)`; the real entrypoint called `StudyOcrPipeline.snapshot_from_image` and set `last_ocr_text`. No desktop capture or loopback request was reachable. The OCR result was:

```text
Example 2: u-substitution
Let u = x^2
Then du = 2x dx
So x dx = (1/2) du
Integrate exp(u) after substitution
```

Expected-token recall was **4/4 (100%)** for `Example 2`, `u = x^2`, `du = 2x dx`, and `1/2`. End-to-end `study_ocr_snapshot` latency was **3,012.54 ms**, including lazy model initialization and inference. The capture stub was called exactly once, and the method returned `status=ok`, `capture_mode_used=interactive`, with returned text equal to the updated plugin state. The loaded modules came from the ignored project venv: `rapidocr-pillow` 1.4.4.post1, `onnxruntime` 1.25.0, NumPy 1.26.4, and Pillow 12.3.0. OCR pipeline and entrypoint source hashes plus model SHA-256 values are recorded in the proof JSON.

Without assigning `last_ocr_text` in the harness, the fixture called real `study_explain_text(text="")`, exercising its `ocr_snapshot` fallback and `_build_learning_context`; the deterministic agent double observed matching OCR text in `input_text` and context. It then called `study_explain_text("Why does Example 2 have a 1/2 factor?")`; the follow-up context retained that same OCR text. Both calls and `study_get_session` used session `study-c5c8684fa4f04af8b789d10150f7c86d`. SQLite returned two interactions with matching session IDs. Plugin method latency was 105.29 ms for the OCR fallback explanation and 14.51 ms for the follow-up.

The timestamped evidence is [neko-study-plugin-ocr-20261009T024255Z.json](../benchmarks/raw/evidence/neko-study-plugin-ocr-20261009T024255Z.json), SHA-256 `12b069399524c6708b82671cb03d022e26c6d304ea086bddc3cb451b40c5a513`. It records the entrypoint and capture injection seam, the synthetic image hash, OCR text, token checks, package provenance, source/model hashes, timings, session consistency, and guard counters. The LLM remained a deterministic double; this does not establish model reasoning quality or general OCR accuracy.

### Process and filesystem guard findings

The first blocked process attempt was a guard false positive during NumPy test-helper import: safe stack metadata showed `platform._syscmd_ver` → `platform.win32_ver` → `platform.uname`/`platform.machine` → `numpy.testing._private.utils`. The standard-library version probe tries Windows `ver`. A second import-time NumPy diagnostic calls Linux-only `lscpu` from `numpy.testing._private.utils.check_support_sve`. The fixture substitutes empty results only for those exact optional probes; the class-compatible `Popen` guard and all other process denials remain active. The successful run recorded one `lscpu` attempt substituted and zero process launches/downstream calls.

RapidOCR's Pillow contour path passes byte paths to `tempfile.mkstemp`; the previous guard treated those as unresolvable. The fixture now decodes byte paths before applying the same allowed-root check. On the successful run, outside reads/writes/directory writes were zero, all three SQLite opens were under the isolated temp root, provider/socket/audio downstream calls were zero, and audio/network/provider attempts were stimulated and blocked. No host, live model/provider, microphone, or audio was used.

## Run

```powershell
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B scripts/neko_study_plugin_methods_fixture.py
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B -u scripts/neko_study_plugin_ui_adapter.py
```

The adapter binds to `127.0.0.1` on an ephemeral port. Stop only the adapter process started for the fixture when finished. No commit or push was made.

## Unified browser-pixel OCR / Study UI loop — final acceptance

`PASS_UNIFIED_OCR_STUDY_UI_LOOP` at **2026-10-09T03:51:22.773Z** (**16:51:22 Pacific/Auckland**). This run combines the earlier independently tested components in one reproducible flow. The shipped static UI and genuine extracted plugin entrypoints required no new teaching implementation: the OCR stop was caused by fixture assertions, including whitespace-sensitive formula matching and a question predicate that did not match the deterministic agent's actual question.

Final evidence:

- [Unified acceptance, reopened SQLite and cleanup](../benchmarks/raw/evidence/neko-study-unified-b254eb6e-571b-4139-a3f7-d49e0edf953d.json)
- [Plugin results, UI milestones, request/run IDs and OCR provenance](../benchmarks/raw/evidence/neko-study-plugin-ui-20261009T035120Z.json)
- [Browser screenshot provenance](../benchmarks/raw/evidence/neko-study-browser-pixels-b254eb6e-571b-4139-a3f7-d49e0edf953d.json) and [actual synthetic course pixels](../benchmarks/raw/evidence/neko-study-browser-pixels-b254eb6e-571b-4139-a3f7-d49e0edf953d.png)
- [Visually reviewed final UI after reload](../benchmarks/raw/evidence/neko-study-ocr-ui-final-b254eb6e-571b-4139-a3f7-d49e0edf953d.png)

Correlation ID: `b254eb6e-571b-4139-a3f7-d49e0edf953d`. Session: `study-7a6e1411f4e143e2bbea484c070724b8`. The plugin `__init__.py` fingerprint remains `4825aaf2195f8b33a581f6e7de08efd7bce04e0b47cd4c776b15ab340c84cbeb`.

### Requirement-by-requirement evidence

| Requirement | Observed evidence |
| --- | --- |
| Browser pixels, not prefilled OCR | Shared web-inspector CLI rendered the correlation-specific synthetic HTML into a 1440×900 PNG. The runner uploaded the actual bytes; their SHA-256 matches the adapter and real OCR capture evidence. |
| Real RapidOCR and normal plugin entry | The original OCR button called `study_ocr_snapshot`, which called the real pipeline on the uploaded image, updated plugin OCR state and populated the UI input. One capture call; four required tokens recognized; latency 4516.05 ms. Package versions, OCR source hashes and three ONNX model hashes are recorded. |
| Raw OCR preserved | Visible input and first explanation request equal `ocr.text`. Whitespace and `²` normalization affect assertions only. This run recognized `Let u =x^2`; the superscript variant is covered by the focused regression check. |
| Explanation plus continuous follow-ups | Three `study_explain_text` runs: original OCR, `为什么例题2有1/2？`, then `为什么要令 u=x^2？`. The mock's second follow-up rejects context missing the exact original OCR, first question or first response. All three passed and mapped to SQLite interaction IDs 7, 8 and 9. |
| Question and grading correlated | `study_generate_targeted_question` produced question `q_ad0974bab4ce448fb883e8df501dda06`, attempt `a_92564095bd8f4e7998afacae570e9c17`. UI answer submission supplied those same identities; real plugin evaluation returned mock `correct / 100`. Question and grade persisted as interaction IDs 10 and 11; grade metadata contains the same identities and verdict/score. |
| Session and Mastery persisted | After browser and server shutdown, a separate process opened only the fixture database with SQLite `mode=ro` and `PRAGMA query_only=ON`; integrity check was `ok`. Five exact interactions, one question in the Session and the synthetic topic are present. Latest Mastery snapshot ID 2 has `0.6189`, increased from `0.0`. |
| Refresh reuses learning state | The original UI reload called `study_summarize_session` again with the same active persisted Session. Both summary calls received the same five SQLite interaction IDs; their summaries match. Session/correlation and Mastery were retained. |
| Results actually visible | The fixture selects `college` through the original onboarding button rather than hiding the modal. All action milestones check rendered visibility and absence of the onboarding overlay. The supervisor viewed the final screenshot: no overlay obscures the Session summary. |
| Cleanup and isolation | Fresh headless Chrome context and browser closed; correlation-specific stop route shut down the adapter normally; its listener was no longer reachable. No page/console errors or non-loopback page requests. Python provider/socket/audio and server external-fetch/WebSocket downstream counters all zero. Browser audio/speech/media/microphone/WebSocket/external-fetch guards were exercised before initial UI actions and again after reload. |

The SQLite file is confined to `.tmp-uv-cache/neko-study-method-fixture/run-8687094ab99b4272b4d6b5efe8b561b3/runtime/plugins/study_companion/data/study_companion.db`. It is deliberately retained as isolated evidence. Five SQLite opens stayed under the guarded fixture root; outside-root read/write/directory/SQLite attempts were zero. The one blocked process diagnostic is the existing NumPy `lscpu` optional probe, not a process launch.

### Reproduce

From `D:\CODE\project\LiveTutor-Lab`:

```powershell
node scripts/neko_study_ocr_ui_e2e.mjs
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B scripts/test_neko_study_context_fixture.py
```

The Node reproducer starts the existing Python adapter, uses `node D:\AI\tools\web-inspector\cli.mjs <synthetic-lesson-url> --screenshot --json` for the synthetic pixels, then keeps the asynchronous Study UI alive using Playwright Core already installed with that shared tool. It installs no dependency and opens no user browser profile or pre-existing tab. It saves evidence with fresh correlation IDs, cleans up its browser/server and then invokes [`neko_study_ui_persistence_check.py`](../scripts/neko_study_ui_persistence_check.py) against only the recorded temporary database. The focused regression script passed five tests, including wrong exponent/derivative and missing-prior-turn rejection.

On this machine the restricted workspace-write sandbox hung inside Python's `asyncio.new_event_loop()` → internal loopback `socketpair` → `accept`, before plugin initialization. A 20-second stack dump identified that location; the supervisor stopped the diagnostic session. The acceptance commands were then approved for execution with loopback available. This is an execution-environment requirement, not an external login/Chrome-profile task. The runner has a bounded startup wait and fails with cleanup if loopback is unavailable.

### Sol Supervisor / Luna Developer collaboration

The supervisor explicitly spawned `/root/ocr_flow_fix` with `model="gpt-6-luna"`, `reasoning_effort="high"`, `fork_turns="none"`, passing only the bounded task and guardrails. The dispatch was accepted; these are the tool's explicit model/effort settings, not an independently measured backend identity or token-cost benchmark.

Luna owned the assertion-only OCR equivalence, two distinct follow-ups/context checks, matching the deterministic question predicate, and the focused negative/positive regression checks. It reported a diagnosis before editing and two intermediate checkpoints. It edited only `neko_study_plugin_ui_adapter.py`, `neko_study_plugin_methods_fixture.py`, and its new focused test. The main agent owned the reusable browser reproducer, real-plugin result checks, read-only SQLite reopen, graceful cleanup, screenshot review and final acceptance.

Concrete supervisor review/correction:

1. Before edits, the supervisor compared the actual mock question against the browser predicate and directed Luna to align the predicate without changing the mock just to make the test pass.
2. At the first checkpoint, code review found Luna's initial patch normalized the adapter but still rejected `²` in the context double. Luna was sent a bounded correction and added five regression tests, including negative cases.
3. The supervisor independently ran the browser flow. The first completed UI run was correctly retained as PARTIAL because the evidence collector still required the old single-follow-up milestone and the supervisor's added check assumed a `history_persisted=true` success field that this plugin omits. The supervisor inspected the SQLite rows and success/failure protocol, updated the milestones and left disk persistence as an independent exact-content assertion.
4. Visual review of an earlier passing screenshot revealed an onboarding overlay could reappear after the fixture merely hid it. The supervisor changed the scenario to use the shipped stage-selection control and added actual visibility assertions, then independently repeated the full acceptance flow. The final screenshot was viewed again and accepted.
5. Luna's hung async test/diagnostic sessions were separately audited: known handles were terminal or explicitly interrupted with exit code 1; the successful synchronous class regression exited 0. The final acceptance browser/adapter exited normally and its listener check passed.

This collaboration was useful because the delegated work was bounded and the supervisor caught real omissions before final acceptance. There was one developer subagent, no additional reviewer or recursive delegation. No quota/cost comparison was measured, so this result does **not** demonstrate an actual percentage saving.

### Limits and preserved state

This PASS covers the requested **synthetic, isolated UI/plugin integration**. It uses a deterministic Mock LLM and does not establish live-model teaching/grading quality, arbitrary OCR accuracy, desktop capture, microphone/TTS behavior, or a packaged N.E.K.O host release. Targeted practice uses the existing synthetic calculus scope. On reload, Session history and Mastery remain usable through the genuine plugin summary; the UI's transient input/question fields are reset, as visible in the final screenshot.

The formal EXE, production learning database, system volume, user browser/profile and other projects were not changed. Existing dirty work was preserved. Only scoped fixture/reproducer/report work was added; no commit, push or reset was performed. Earlier partial and passing evidence was preserved rather than overwritten or retroactively relabelled.
