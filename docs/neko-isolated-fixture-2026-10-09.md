# N.E.K.O isolated fixture evidence — 2026-10-09

## Outcome

**Overall: PARTIAL; the requested real plugin tutoring loop is not verified.** No installed/frozen app or candidate host was launched. No real audio, microphone, provider, personal screen, or real Study database was accessed. The evidence below separates candidate methods, browser rendering, mock UI API, and plugin runtime.

Candidate source fingerprint: `1d814cf32fba8c02b5727d2890710e4e7b8ece24` (`candidates/N.E.K.O`). The Python probe records SHA-256 hashes for the exact candidate TTS/runtime files. The installed frozen binary was not used as a test subject.

## Evidence by layer

| Layer | Result | Evidence and boundary |
|---|---|---|
| Candidate audio methods | **PASS — offline stub only** | [`neko-audio-isolation-fixture.json`](../benchmarks/raw/evidence/neko-audio-isolation-fixture.json) stimulates candidate `_resolve_tts_worker_spec`, `_start_tts_thread`, `dummy_tts_worker`, `TurnMixin.handle_audio_data`, and actual `TtsRuntimeMixin.send_speech`. A counted fake provider worker is selected; its thread-dispatch attempt is counted and blocked before its body (`attempted=1`, `blocked=1`, `fake_provider_worker_calls=0`). The normal request queue is stimulated and blocked (`1/1`). The candidate callback reaches the actual `send_speech` call-site guard supplied as an always-false fixture seam; the counting socket records zero writes. Reload and child-process restart repeat the same stimuli. **This is not host-wide mute or OS isolation.** |
| Browser output gate | **PASS — renderer fixture only** | [`neko-audio-gate-browser-final-2026-10-09.json`](../benchmarks/raw/evidence/neko-audio-gate-browser-final-2026-10-09.json) and [browser screenshot](../benchmarks/raw/evidence/neko-audio-gate-browser-final-2026-10-09.png). Chromium 154 exercised AudioContext, speech synthesis, media playback, microphone, WebSocket, and external fetch; each was counted as attempted and blocked once. No console/page errors or failed requests. This verifies the renderer fixture's interceptors and CSP, not OS-wide network isolation or the N.E.K.O host. |
| Study UI render | **PASS — static release-bundle UI** | [screenshot](../benchmarks/raw/evidence/neko-study-ui-static-render-final-2026-10-09.png) shows the extracted Study Companion page in Chromium with the fixture safety banner; its initial onboarding dialog is still open. The source is the extracted release bundle's static asset directory, not a candidate-host route. |
| UI interaction | **PARTIAL — synthetic API** | The load-time UI driver used the actual static UI code and posted one `study_explain_text` call to the fixture's local mock `/runs` endpoint for the synthetic substitution lesson. The endpoint's state file records that request and canned reply. The captured screen did not confirm the reply visible; no follow-up, question generation, answer evaluation, session summary, reload reuse, OCR, or Session/Mastery plugin-store persistence is established. This is a UI fixture, not plugin E2E. |
| Genuine Study Companion plugin | **GAP — dependency/runtime blocked** | The extracted release-bundle plugin entry was attempted in a separate CPython process with candidate source/SDK paths. Import stopped at `ModuleNotFoundError: No module named 'pydantic'`, before plugin construction or host launch. Candidate `uv.lock` pins FastAPI 0.141.1, Pydantic 2.13.5, pydantic-core 2.46.5, SQLAlchemy 2.1.1, and related packages. A venv was created only under ignored `.tmp-uv-cache/neko-study-venv`; installation of that minimal locked core cohort was blocked by network policy (`WinError 10013`) before download. No package was installed. The supplied raw plugin tree also lacks `plugin.sdk`; candidate source supplies that SDK, but its dependencies remain unavailable. |

The first-run browser screenshot and one fixture API event should not be described as a completed tutoring loop. The mock returns canned explanations and evaluates an answer with a simple fixture rule; neither result exercises Study Companion service logic or a real model/OCR implementation.

## Commands run

- Python audio probe: `python.exe -I -S scripts/neko_audio_isolation_fixture.py` using the supplied CPython 3.11 at `benchmarks/raw/goal-python/cpython-3.11-windows-x86_64-none/python.exe` — **PASS, candidate selector/callback offline stub**.
- Existing relevant regression suite through that interpreter — **PASS, 38/38**.
- `node --check scripts/neko_study_ui_fixture.mjs` — **PASS**.
- `node scripts/neko_study_ui_fixture.mjs --gate-probe` — **PASS, attempt/block counters and zero downstream calls across reload/restart self-check**.
- Shared browser inspection of `/__audio-gate-check.html` — **PASS, renderer fixture only**; static Study UI route — **HTTP 200, no browser errors**.
- Genuine plugin import in an isolated process — **BLOCKED at missing `pydantic`**.
- Project-local pip install using the candidate lock's core versions — **BLOCKED before package download by `WinError 10013`**.

## Restore and remaining work

The local Node fixture server was stopped after capture. The Python venv remains at ignored `.tmp-uv-cache/neko-study-venv` with only pip/setuptools; package access failed before installing dependencies. A recursive cleanup request was rejected by local filesystem safety policy, so that isolated venv was preserved. No DB or host state was created. Evidence JSON and screenshots are fixture artifacts in `benchmarks/raw/evidence`.

The smallest next safe step is a dependency-capable isolated Python environment (or approved local wheel cache) for the candidate host plus the extracted Study Companion source, followed by a launch-time gate installed before host startup. The host must remain stopped until ordinary TTS dispatch and native `send_speech`/websocket output are both stimulated and blocked by that full gate. Then use a temporary DB, synthetic lesson context, and mock LLM/OCR for genuine plugin entrypoint flow. Do not claim the browser fixture as a substitute.
