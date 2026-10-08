# Project N.E.K.O base maintenance audit

**Review date:** 2026-10-07  
**Scope:** Infrastructure and upstream-maintenance risk for a 6–12 month integration. Pedagogy and the final LiveTutor base selection are out of scope.

## Executive finding

N.E.K.O can stay reasonably close to upstream if tutor behavior is added as a separately versioned plugin/adapter and custom state remains outside N.E.K.O's agent, voice, screen, and memory internals. The public Python backend and shared web UI have clear integration seams. The repository is actively maintained, but its active development rate is high: sampled API history shows 100 commits from Sep 28 through Oct 7, 2026, with another 100 from Sep 6 through Sep 28. Core voice/session ownership, plugin lifecycle, screen handling, memory, and desktop integration all receive meaningful changes.

The forecast changes if the tutor needs patches to the main loop, voice turn arbitration, screen bridge, or desktop host. Those are moving implementation areas, and an Electron fork would start with a source-visibility/build-reproducibility gap. Keep upstream changes as additive plugins and small contract proposals; pin tested revisions and upgrade in batches. A custom plugin is feasible, but it should not assume the plugin API is frozen: the v0.9 migration removes or deprecates several old surfaces.

**Answer to the main question:** yes for an adapter/plugin-led integration; no guarantee for a fork that carries ongoing edits in core realtime, screen, memory, or desktop-shell code. The latter would incur regular merge work and Windows regression checks.

## 1. Exact revisions and evidence inspected

- Main repository: [`Project-N-E-K-O/N.E.K.O`](https://github.com/Project-N-E-K-O/N.E.K.O), Apache-2.0, default branch `main`, inspected at **`1d814cf32fba8c02b5727d2890710e4e7b8ece24`** (2026-10-07). The `main` tree response resolved to this same SHA.
- Stable reference: **`v0.9.0`, `435a033983152e13520b1f6cb9912ea0e8c9dc75`** (tagged 2026-08-20). Also checked release metadata back through `v0.7.4` and the `nightly` release (2026-10-02).
- Official Tauri host: [`Project-N-E-K-O/N.E.K.O.-Tauri`](https://github.com/Project-N-E-K-O/N.E.K.O.-Tauri), Apache-2.0, inspected at **`b7b4fd70692489ca94457bc95f968e36ed61c4c4`** (2026-07-29).
- History evidence: queried paginated GitHub commit API history at pages 1, 2, 5, 10, 20, and 30 (page 1 spans Sep 28–Oct 7; page 2 spans Sep 6–Sep 28; page 5 spans Aug 1–Aug 7; page 10 spans Jun 24–Jul 2; page 20 spans Apr 21–Apr 28; page 30 spans Nov 27–Dec 6, 2025). Also inspected file lists/stats for representative screen, plugin, memory, provider, VRM, core cancellation, and session-handoff commits. This was API history inspection, not a local clone.
- Key reference files: [developer guide](https://github.com/Project-N-E-K-O/N.E-K.O/blob/1d814cf32fba8c02b5727d2890710e4e7b8ece24/docs/guide/index.md), [frontend overview](https://github.com/Project-N-E-K-O/N.E-K.O/blob/1d814cf32fba8c02b5727d2890710e4e7b8ece24/docs/frontend/index.md), [agent architecture](https://github.com/Project-N-E-K-O/N.E.K.O/blob/1d814cf32fba8c02b5727d2890710e4e7b8ece24/docs/architecture/agent-system.md), [memory architecture](https://github.com/Project-N-E-K-O/N.E.K.O/blob/1d814cf32fba8c02b5727d2890710e4e7b8ece24/docs/architecture/memory-system.md), [TTS pipeline](https://github.com/Project-N-E-K-O/N.E.K.O/blob/1d814cf32fba8c02b5727d2890710e4e7b8ece24/docs/architecture/tts-pipeline.md), [plugin migration](https://github.com/Project-N-E-K-O/N.E.K.O/blob/1d814cf32fba8c02b5727d2890710e4e7b8ece24/docs/plugins/migration-v0.9.md), and Tauri's [README](https://github.com/Project-N-E-K-O/N.E.K.O.-Tauri/blob/b7b4fd70692489ca94457bc95f968e36ed61c4c4/README.md).

The main repository API reports Apache-2.0. The Tauri host also declares Apache-2.0. This review did not inspect or validate third-party model/runtime licenses bundled with distributed builds.

## 2. Architecture map

| Subsystem | Open-source status and location | Current stability / extension surface | Desktop coupling and likely custom patches |
|---|---|---|---|
| Python/core backend | Public Apache-2.0 repo `N.E.K.O`; FastAPI/Uvicorn services in `app/`, conversation logic in `main_logic/`, memory in `memory/`, configuration in `config/`. | Broad and working product surface, but actively refactored. HTTP/WebSocket contracts and service boundaries are more suitable than importing deep internals. | Low for service/domain logic. Avoid core edits; an adapter can call local APIs or run as a plugin. |
| Main agent loop | Public `brain/`, `app/agent_server/`, `main_logic/cross_server.py`; `DirectTaskExecutor` assesses and dispatches channels. | Internal runtime, channel priority, task routing, cancellation, and delivery are changing. Extension exists through agent channels and user plugins, but is not a stable embedded SDK for changing turn semantics. | Low direct shell coupling; integration runs through local services and WebSockets. Tutor-specific turn changes in `main_logic/core/` are likely patches. |
| Provider abstraction | Public `utils/llm_client/`, `config/api_profiles.py`, `config/api_providers.json`; provider/model tiers and OpenAI-compatible plus Anthropic clients. TTS uses `utils/tts/provider_registry.py` and `main_logic/tts_client/workers/`. ASR has modular workers under `main_logic/asr_client/workers/`. | Provider registries and worker boundaries are real seams. Config schema, routing precedence, provider availability, and model tiers continue to evolve. Treat worker call signatures as implementation contracts unless documented/versioned. | Little shell coupling for cloud providers; local runtimes need platform-specific packaging. A custom provider may touch config, worker registry, UI, tests, and locales. |
| Memory | Public `memory/` plus `app/memory_server/`; per-character recent history, time-indexed journal, facts, reflections, persona, retrieval. | Subsystem is decomposed and documented, but schemas, ranking, lifecycle, and write paths are under active optimization. No public plugin SDK for persistent semantic recall in the v0.9 migration. | Low shell coupling. Keep tutor progress/lesson state in the tutor's own store; do not fork the memory schema for it. |
| Plugin system | Public `plugin/` runtime/SDK and `docs/plugins/`; separate plugin manager at `frontend/plugin-manager/` (Vue). | Strongest extension surface for a Tutor adapter: `NekoPluginBase`, entries, typed bus, config/storage, database, UI and model slots. API is versioned but recently breaking/deprecating; pin SDK compatibility. | Mostly local HTTP/event bus; hosted UI is web-rendered. A plugin avoids shell patches unless it needs native capture/window APIs. |
| Marketplace plugins | Public client/server bridge and release workflow in `plugin/server/market_protocol_handler.py`, `plugin/server/routes/market_bridge.py`, `frontend/plugin-manager/`, `.github/workflows/plugin-market-*`. Marketplace distribution is a remote service/release convention, not just an in-process plugin API. | Hash-to-release binding, safe upgrades, install lifecycle, and auth/CSRF received recent fixes. The mechanism exists, but its service and publication policy are externally operated; compatibility and availability should be verified for the intended distribution. | Low shell coupling. Keep a custom Tutor plugin separately versioned and install locally/private until marketplace publication requirements are confirmed. |
| Voice / STT / TTS | Public frontend capture/playback and backend ASR/TTS trees. STT includes local faster-whisper and cloud/provider workers. TTS includes native realtime audio and external provider workers. | Broad provider coverage; concurrency, handoff, retry, late-callback, and session ownership are nontrivial and frequently patched. Extension seams exist at worker/registry level, but end-to-end voice behavior belongs to moving core. | Browser/WebView mic/audio APIs; device handling differs by browser and desktop shell. Voice changes can involve both frontend and backend. |
| VAD / endpointing | Public `main_logic/asr_client/endpointing/`: Silero VAD, activity evidence/admission, SmartTurn v3 ONNX, coordinator, provider VAD/fallback paths. | Implemented with unit/replay coverage, but SmartTurn is explicitly **not approved as product-quality endpointing** in the human/Electron validation design; a model replay pass does not certify the live route. | Shell supplies microphone/audio timing; tune through configuration where possible. Expect platform/hardware validation before trusting it. |
| Interruption / barge-in / arbitration | Public `main_logic/omni_realtime_client/`, `main_logic/core/`, TTS lifecycle, frontend playback queues and turn events. | Implemented: native response cancellation, speech-ID ownership, TTS interrupt/shutdown sentinels, stale callback fencing, turn arbitration. Recent PRs still repair races and session handoff. This is substantial machinery, not evidence of universally robust behavior on real devices. | Frontend playback and mic lifecycle cross the WebSocket/shell boundary. Core patches here have high rebase and regression cost. |
| Echo and self-hearing | Public frontend mic constraints request browser/platform `echoCancellation: true`; there are input suppression, mic leases, recent-playback/transcript and turn-admission gates. | Heuristics and platform AEC request are implemented. No independent N.E.K.O acoustic echo canceller/reference-signal pipeline was identified in inspected source. `echoCancellation` is a browser/device request, not a guarantee. | Depends on WebRTC/WebView and audio driver. Requires real hardware/headset/speaker tests; do not assume it is production-grade from source alone. |
| Proactive behavior | Public `main_logic/proactive_chat/`, `main_logic/core/proactive.py`, settings and REST APIs; screen-aware proactive behavior is gated by a user privacy setting. | Feature-complete enough to reuse but policy, candidate selection, timing, delivery and activity interfaces have active refactors. Use documented settings/API and keep tutor scheduling/policy in the adapter. | Screen awareness needs screen capture path; other proactive logic is shell-light. Tutor-specific scheduling should remain separate. |
| Screen capture and source selection | Public `static/app/app-screen.js`, `static/app/desktop-capture-provider.js`, `utils/capture_bridge.py`, capture routes; Electron provider is external. Tauri native implementation is public in the Tauri repo. | Shared UI has a provider resolver and explicit remembered-source logic. Platform bridges are less stable; source IDs and self-exclusion differ by shell. Screen source behavior has recent fixes. | **High shell coupling** for native source enumeration/capture and self-window exclusion. Tauri implements capture, but not the full Electron source feature set. Likely custom work if capture semantics must match exactly. |
| Renderer / avatars | Public shared web UI in `static/`, `templates/`, `frontend/react-neko-chat/`; Live2D uses Pixi/Cubism, VRM/MMD use Three.js, PNGTuber has its own renderer. | Strong reusable surface and independent renderer concepts. Shared frontend uses globals/events and template load order, so not a clean component-only architecture. Renderer features still change. | Mostly shared web code, but transparent full-screen overlay, pointer hit-testing, always-on-top, drag/window bounds, and native input shape need a host. |
| Electron host / IPC | Shared backend docs/workflow are public. Electron main/preload and `window.electron*` APIs are documented as living outside `N.E.K.O`. Workflow defaults to `Project-N-E-K-O/N.E.K.O.-PC`. That repository was not discoverable in public org search and direct public API lookup did not return readable source (404); it may be private, renamed, or access-restricted. | Public integration contracts exist, host implementation does not appear available from the public source reviewed. Public Windows desktop workflow builds on maintainers' infrastructure, with `ELECTRON_REPO_TOKEN`/`GITHUB_TOKEN` for the separate checkout. This is not independently reproducible from public source alone unless that repo is made accessible. | Very high shell coupling. Avoid forking an opaque host. Do not depend on undocumented preload APIs. |
| Tauri host / IPC | Public Apache-2.0 `N.E.K.O.-Tauri`; small Rust/Tauri 2 wrapper and bridge scripts. | Experimental standalone shell. It deliberately uses the upstream Python service and shared web UI, with provider bridges. Windows code exists, but public CI tests web and Rust on Ubuntu only. | Shell-specific Rust provider; it implements transparent/always-on-top full-screen window, click-through, native source listing/capture and backend startup. It is a plausible open host to evaluate, not yet a validated Windows replacement. |
| Frontend/backend boundary | Public FastAPI main server typically on `127.0.0.1:48911`; REST, WebSocket, static page, React chat, plugin server/manager; agent and memory run as service modules/ports. | Clear enough integration boundary to add a plugin/adapter. However the shared page still has legacy globals and front-end contracts across vanilla JS, React, and Vue. | Electron/Tauri load backend-served UI and inject bridge globals. Most UI features are shell-neutral until native capture or window controls are used. |
| Desktop lifecycle | Public Tauri `backend_runtime.rs` checks `GET /health`, attaches to an existing N.E.K.O service without owning it, or starts a configured source/executable/bundled child and terminates only that child. Electron release workflow and public deployment docs describe packaged Python backend plus separate Electron app. | Tauri lifecycle code is explicit and small. Electron lifecycle source is not available in this review. | Core architectural boundary is local HTTP; process launch/ownership, restart, shutdown, updater and IPC remain host responsibilities. |

## 3. Electron and Tauri findings

### Electron

- Publicly available: the Python backend, shared frontend, REST/WebSocket contracts, Windows desktop build workflow, packaging/release documentation, and some Electron acceptance tests.
- The public `N.E.K.O` tree contains no Electron main or preload source. Its frontend docs explicitly say main/preload implementation is outside this repository. The Windows workflow names a separate default repository, `Project-N-E-K-O/N.E.K.O.-PC`; public search/direct API lookup could not read it. This is more precise than calling the product simply closed-source: the backend and UI are open, while the reviewed Electron host source is unavailable publicly.
- The workflow is visible and automates backend Nuitka packaging and Electron assembly, but its default Electron checkout depends on repository access/token. Maintainers can run it; a public outsider cannot establish a reproducible source-to-installer build without the Electron source and its dependencies/configuration.
- Electron's packaged JavaScript is generally inspectable when distributed as an ordinary `resources/app.asar`: ASAR is an archive, not encryption. If a user has the installer/unpacked app, its archive can ordinarily be listed/extracted and minified JS examined. Minification/source-map removal can make analysis harder; native `.node` modules and compiled binaries are not equivalent to source. This review did not download/extract an installer, so it does not claim which exact current package contains which archive or whether a particular release applies additional obfuscation.
- Thus the practical boundary is: Electron host source was not found in the public checkout; corresponding bundled JS may be recoverable from a distributed artifact, but artifact-only inspection is not a reproducible source/build pipeline. The exact app.asar contents remain unverified here.
- Desktop workflows build Windows, macOS, and Linux variants. The existence of a workflow is evidence of a packaging path, not public reproducibility or a successful clean rebuild by this review.

### Official Tauri work

- `N.E.K.O.-Tauri` states that it owns only the desktop host; Python logic and shared chat/avatar UI remain in upstream `N.E.K.O`. It checks for service on port 48911, connects without adopting an external process, otherwise launches development source or a bundled/external backend executable.
- Current wrapper config requests a transparent, undecorated, always-on-top main window. Windows code sets always-on-top, spans the virtual desktop bounds across enumerated monitors, and uses Tauri's ignored-cursor-events API for click-through. Platform logic is split into Linux/macOS/Windows modules.
- Its injected bridge exposes native screen/window listing and capture using `xcap`; source lists omit minimized windows, but do not filter the Tauri/N.E.K.O window. It captures a selected source, scales to max width, and JPEG-encodes. Shared UI can resolve this provider at runtime.
- Maturity is low: the README calls it experimental; the public repository has a short burst of about 15 commits around July 24–29, no published GitHub releases, one star at review time, and no subsequent commits in the inspected history. CI only runs Ubuntu web/Rust checks. Windows source exists, but Windows build, window layering, capture, and multi-monitor behavior have not been established by that CI.
- Compatibility is intentionally achieved by consuming the main N.E.K.O server and shared UI rather than copying them. Tauri has a Tauri-specific capture and click-through provider, which the shared `desktop-capture-provider.js` resolves. That is a sound separation in concept; it still needs same-revision integration and Windows testing.

## 4. Screen pipeline

There are several different capture paths; they should not be treated as one universal screenshot API.

1. **Interactive screen sharing:** shared `app-screen.js` resolves a native desktop provider when present and otherwise uses browser capture/portal paths. Source selection is stored in frontend state. Source labels and optional remembered window title are stored in local storage; title-based re-match is explicitly user controlled. Screen IDs and names can change, so the code tracks selection generations, source metadata, screen index and reconciliation when sources change.
2. **Native provider seam:** `desktop-capture-provider.js` resolves `tauriDesktopCapturer` or `electronDesktopCapturer` at call time and applies bounded timeouts. Electron provider methods are supplied by its external preload. Tauri injects `tauriDesktopCapturer` after navigation and exposes `get_screen_capture_sources`/`capture_screen_source` through IPC commands.
3. **Tauri native selection:** Tauri lists each monitor and non-minimized window through `xcap`; IDs are `screen:<id>` or `window:<id>`. It captures the chosen current ID and returns a resized JPEG data URL. It does not list thumbnails in current code and does not self-filter N.E.K.O-owned windows. The UI may select a monitor/window, but there is no N.E.K.O exclusion in the Rust enumerator.
4. **Electron capture bridge:** Python's `/api/capture/*` endpoints and `utils/capture_bridge.py` send capture requests to a connected Electron renderer over the main WebSocket. The source is resolved by the renderer's `electronDesktopCapturer` bridge. Capability flags include `captureSourceWithoutNeko`, region capture and computer-use capture; this indicates an Electron-specific self-exclusion capability, but its implementation cannot be confirmed from the inaccessible host source. The bridge is loopback-restricted and serializes image capture requests.
5. **Computer-use/proactive screenshot:** local agent capture requests go through the renderer bridge where available; headless/Linux fallbacks use Python desktop capture helpers (`utils/desktop_capture.py`, e.g. MSS/PyAutoGUI or Wayland system tools). These paths do not necessarily share interactive source selection. Proactive vision is user-gated.
6. **Remembered windows and multi-monitor:** shared UI persists an explicit selected window/title only when its remember-title setting is enabled; it keeps source ID/name/index metadata and reconciles when source lists refresh. Multi-monitor state is queried and cached briefly; screen labels use indexes. Tauri enumerates every monitor and its Windows host sizes the overlay across virtual desktop bounds. This is implemented, but monitor ordering/negative coordinates/DPI/source ID persistence still need Windows validation.

**Shell-dependent parts:** native source enumeration, screenshots/frames, thumbnails, source IDs, portal prompts, self-window exclusion, transparent overlay, and click-through. The shared picker/state/reconciliation logic is frontend code, not Python core. Keep a future tutor's screen observation behind a provider interface and request only the needed source; avoid embedding shell-specific IDs into tutor persistence.

## 5. Realtime voice: implemented versus strong

| Capability | Implemented in source | Strength evidence and practical limit |
|---|---|---|
| STT | Realtime native-provider audio plus independent ASR clients/workers (Gemini, OpenAI, Qwen, GLM, Grok, Soniox, Step and local faster-whisper paths). | Broad routing and recovery mechanisms. Quality/latency depends on provider/network/device and is not uniform. |
| VAD / endpointing | Silero local VAD, activity evidence/admission, SmartTurn v3 ONNX, coordinator retries, and provider/server VAD in relevant routes. | SmartTurn v3 validation doc explicitly says it is not approved as product-quality endpointing for Chinese, English or Japanese; live Electron route acceptance is separate from model replay. Treat as implemented, not proven production-grade. |
| TTS | Provider-native realtime audio plus external queue/worker path for custom/cloned voices and selected providers; multiple streaming WebSocket and HTTP-sentence provider classes. | Solid abstraction breadth. Provider workers and completion markers have recent fixes; latency, voice quality and behavior remain provider-dependent. |
| Interruption | User activity can cancel native response generation and external TTS (`__interrupt__`), clear playback, mute late callbacks and associate audio with speech/turn IDs. | Extensive ownership and race protections exist. Core session handoff and cancellation recently changed across many files; source tests do not replace listening and speaking over real audio. |
| Response arbitration | Response/session arbiter tracks provider response ownership, turn epoch and completion; candidate admission coordinates transcripts and pending speech. | Implemented with substantial unit/regression coverage, but internal and frequently changing. Do not custom-patch unless the tutor absolutely requires new turn semantics. |
| Echo/self-hearing | Mic request asks for `echoCancellation: true` where supported; app also uses mic leases, mute/input suppression, playback state and transcript/turn guards. | No standalone software AEC implementation was identified. Platform AEC is opportunistic and can fail with speakers, virtual devices, Bluetooth or WebView differences. Echo behavior is not validated here. |
| Fallbacks | ASR admission/recovery, provider switching, no-VAD/ID-less turn sealing, bounded timeouts and lifecycle cleanup. | Fallback logic is evidence of resilience engineering, not a guarantee that each fallback sounds or feels natural under live use. |

The voice subsystem is valuable to reuse but should be treated as a high-change subsystem. An external Tutor plugin can consume events/entries and use its own session-level policy; if it needs custom barge-in, audio arbitration, or endpointing, expect a recurring upstream-sync burden.

## 6. Upstream churn analysis

Release cadence is roughly monthly during the observed period: `v0.8.0` May 8, `v0.8.1` May 18, `v0.8.2` Jun 12, `v0.8.3` Jun 27, and `v0.9.0` Aug 20. A `nightly` artifact was published Oct 2. Stable tags are a safer integration target than tracking each commit.

Commit count alone understates the cost. Examples of materially broad changes in the inspected history:

- **Core/session and voice ownership:** Oct 2 session-handoff repair touched ASR runtime, core lifecycle/session/streaming/TTS, realtime response arbitration, WebSocket/frontend state, and dozens of ownership/race tests. The commit listed 11,182 changed lines including tests. Oct 3 cancellation repair spanned core, offline realtime, state, frontend and screen-history contracts (10,170 lines). These are high-risk merge surfaces.
- **Screen/history coupling:** Oct 2 screen-history correction crossed core context/lifecycle, offline client, memory recent history, LLM history and tests. Recent source-sharing fixes also adjust front-end source enumeration and restart/picker behavior.
- **Plugin churn:** Oct 1 introduced source hot reload and lifecycle recovery; Oct 2–7 commits adjust install/update/lifecycle, marketplace hashes, plugin subprocess startup performance, SDK metadata/schema, CSRF and bus events. A custom Tutor plugin is a good extension seam, but pin its SDK expectations.
- **Breaking plugin contract:** the v0.9 migration removes script plugins, removes high-level plugin memory/`MemoryClient`, removes `get_message_plane_all` and deprecates v1 `push_message` fields. This is concrete API churn, not a hypothetical risk.
- **Provider churn:** adding Requesty touched API profile/config, server routes, provider client, docs/locales and tests. TTS provider registry/worker paths and ASR provider lifecycles are also active. Provider addition is distributed across config, worker, UI and localization rather than a single stable package hook.
- **Memory churn:** a recent hot-path optimization touched retrieval/fact/persona/time index. Agent and memory work is split into modules, but semantics and storage contracts are evolving; persistent semantic recall is not exposed as a plugin contract.
- **Avatar churn:** recent VRM movement work touched renderer runtime, manager, router and tests; the renderer is reusable but still active.
- **Tauri churn:** small short-lived burst in July around screen capture, transparent overlay/platform splitting and standalone backend lifecycle; then no subsequent commits in inspected history. Lower observed churn currently means lower evidence of maintenance, not mature stability.

Interfaces that appear relatively stable are the main local HTTP/WebSocket service boundary, the plugin package/entry model at v0.9, and the desktop capture provider shape (`getCapabilities`, `getSources`, `captureSourceAsDataUrl`). The latter remains shell-dependent and should be versioned/contract-tested by an integrator.

## 7. Extension stability

- **Best seam — plugin/adapter:** implement Tutor orchestration in a normal plugin using documented v0.9 `NekoPluginBase`, entries, storage/database, typed bus and model slots. Keep plugin data, tutor state and external APIs in that package. Pin against a specific N.E.K.O/plugin SDK release and run the plugin checker during upgrades.
- **Good seam — sidecar/service adapter:** a separate process can talk to N.E.K.O's local REST/WebSocket boundary. This avoids core merges and makes switching host easier, at the cost of service/process configuration and an explicit auth/transport contract.
- **Good seam — frontend hosted plugin UI:** use documented hosted TSX/plugin UI surface for modest tutor controls. Larger custom learner experiences can be a separate web UI that calls the adapter.
- **Conditional seam — provider workers:** use a documented plugin model slot where possible. A new core TTS/ASR provider currently tends to require registry/config/UI/localization work, so upstream a generic provider contract before carrying a local implementation.
- **Weak seam — persistent memory:** plugin bus memory is bounded recent in-memory context, not facts/reflections/persona. Keep tutor mastery/progress in a tutor-owned database rather than reaching into N.E.K.O internals.
- **Weak seam — realtime core:** do not build tutoring policy directly into `main_logic/core`, `omni_realtime_client`, `voice_turn`, ASR endpointing, or `tts_runtime` unless upstream accepts the feature.
- **Weak seam — desktop capture:** use the resolver/provider interface; native self-exclusion and source metadata differ. A feature requiring `captureSourceWithoutNeko` may need Tauri work or an upstream provider capability proposal.

## 8. Fork-maintenance simulation

Assumption: one Tutor adapter, one custom plugin, and minor Study Companion adjustments.

- **Adapter + isolated plugin:** low-to-moderate recurring cost. If both live outside N.E.K.O, most upstream merges should be clean. Expect a compatibility update around plugin SDK changes and validate any local event/API assumptions per release.
- **One plugin in a separate repository:** lowest core sync burden. Use supported config, storage, bus/events, model slots and UI. Pin plugin dependencies and SDK target separately from N.E.K.O.
- **Minor Study Companion changes in the core repo:** moderate cost if they are UI copy or a small additive API. High cost if they alter `main_logic/core`, memory records, mic/audio lifecycle, or screen routing. Keep a patch series small and seek an upstream seam before the first long-lived patch.
- **Provider implementation:** moderate if it is an adapter against a stable public endpoint; high if it requires edits in provider registry, settings schema, plugin manager, and many locale files.
- **Desktop host changes:** high for Electron because reviewed source is inaccessible and the public build depends on it; moderate-to-high for Tauri until Windows CI/releases and compatibility contracts mature. Avoid having the tutor require native changes in both shells.

Practical estimate: with add-on-only features, expect approximately **a few hours per monthly upgrade** for review/compatibility and occasional plugin migration work, not continuous rebasing. A fork carrying core voice/screen/memory patches can reasonably become **multiple days per upgrade**, plus repeated platform regression work, especially around the large session/voice changes sampled above. These are planning estimates, not measured project history.

## 9. Recommended Git/upstream strategy

Use a conventional remote setup: `origin` = the LiveTutor-owned fork, `upstream` = `https://github.com/Project-N-E-K-O/N.E.K.O.git`. Keep tutor plugin/adapter repositories separate from the core fork. Store the selected N.E.K.O tag/SHA, plugin SDK target, plugin release and any desktop-host revision together in a small compatibility manifest.

1. Fetch upstream tags and `main` on a weekly or biweekly cadence to review relevant changes; do not merge or deploy every commit.
2. Integrate at stable releases (or a pinned commit only when a required fix is not in a release). The sampled release cadence is monthly-ish, so review after each stable release and keep nightly adoption opt-in.
3. Pin a known-good N.E.K.O SHA/tag for production and pin the Tutor plugin/adapters independently. Do not use floating `main`, `latest`, or unpinned marketplace versions for a working tutor installation.
4. Before upgrading, inspect changes in `plugin/`, `main_logic/core/`, `main_logic/asr_client/`, `main_logic/omni_realtime_client/`, `memory/`, `static/app/app-screen.js`, provider config/registries and desktop workflows. Use API commit/file history and compare the pinned SHA to target.
5. Rebase the LiveTutor core branch on the new tag only if it carries necessary core patches; otherwise keep core clean and upgrade the separate plugin/adapter. Submit generally useful seams upstream as small PRs.
6. Test the adapter contract (plugin load, settings, storage, bus/event delivery, model slot, permissions), startup/shutdown and upgrade/migration behavior. For any screen or voice change, run real Windows capture and mic/playback checks on the intended shell; Cloud review cannot validate those.
7. Pin plugin/Study Companion versions separately and keep a compatibility matrix (N.E.K.O SHA ↔ plugin SDK/version ↔ screen provider version ↔ desktop host SHA). Roll back as a unit if an upgrade breaks the integration.

## 10. SAFE TO EXTEND

- Separate Tutor adapter/service calling local REST/WebSocket APIs.
- A normal v0.9 `NekoPluginBase` plugin with its own storage/database and settings.
- Hosted plugin UI for a small tutor control surface.
- Tutor-specific progress/mastery data in the plugin's own schema.
- Provider selection/configuration through supported model slots and settings.
- Avatar and chat presentation through shared frontend/plugin surfaces where no new native window behavior is needed.
- Additive upstream changes that define versioned event/provider/capture contracts.

## 11. RISKY TO PATCH

- Plugin runtime/lifecycle, marketplace install/update and SDK compatibility internals.
- `main_logic/core/`, realtime session ownership, transcript admission, turn arbitration, TTS interruption and ASR endpointing.
- `static/app/app-screen.js`, screen IDs, capture bridges and source filtering.
- Memory fact/reflection schemas, post-turn writes, retrieval and new-dialog context.
- Provider configuration/routing where it crosses settings, registries, UI and localization.
- VRM/Live2D host interactions where input hit-testing, full-screen geometry, drag and click-through meet native window behavior.

## 12. NEVER FORK UNLESS NECESSARY

- Electron `N.E.K.O.-PC` main/preload implementation: reviewed public source is unavailable, so a fork cannot be maintained/rebuilt confidently from this evidence.
- Core session handoff and response arbitration solely to customize tutor turn-taking; use an adapter/plugin or propose an upstream contract.
- N.E.K.O persistent memory internals for tutor-specific knowledge tracking; own a Tutor data store instead.
- Native screen capture in both Electron and Tauri before the chosen host has been validated; define a shared provider contract and implement only the selected host's required behavior.
- Plugin marketplace security/update code for a one-off custom plugin; use a pinned local/private plugin release.

## 13. Infrastructure reuse coverage estimate

These are infrastructure-only qualitative coverage estimates for the inspected source, not scores for tutoring or pedagogy. The overall estimate weights the ten infrastructure areas equally; it measures implemented reusable capability, not proven reliability on a target Windows PC.

| Area | Reuse coverage | Basis |
|---|---:|---|
| Desktop shell | 45% | Public Tauri host implements core shell primitives but remains experimental/unvalidated on Windows; Electron host source is unavailable publicly. |
| Avatar | 85% | Shared Live2D, VRM, MMD and PNGTuber renderers already exist; overlay/window behavior remains host-specific. |
| Voice | 75% | Multi-provider STT/TTS and realtime audio paths exist; target-device quality and handoff edge cases require validation. |
| Interruption | 70% | Cancellation, turn ownership and playback lifecycle exist, with meaningful race/churn and live-audio validation needs. |
| Screen | 75% | Selection, remembered source, multi-monitor, native bridges and capture paths exist; Tauri self-exclusion/thumbnail parity and Windows behavior remain open. |
| Proactive | 65% | Proactive scheduling/generation/vision gates exist; tutor-specific policy and study state are separate work. |
| Memory | 80% | Persistent recent/facts/reflections/persona and retrieval exist; Tutor learning state must be separate and plugin access is limited. |
| Provider abstraction | 75% | Multiple LLM/ASR/TTS providers and routing exist; extension points are uneven and config/UI updates are cross-cutting. |
| Plugin/extensibility | 85% | Versioned package SDK, storage, bus, entries and UI exist; v0.9 breaking/deprecated changes require pinning. |
| Windows suitability | 60% | Main project has Windows desktop builds; Tauri Windows code exists but its public CI does not test Windows and no GUI/audio validation was run. |

**Infrastructure reuse coverage: 72%** (rounded average of the table; confidence medium-low because this review did not run the app on Windows).

Expect LiveTutor to build or own roughly **25–35% of its infrastructure**: Tutor-specific orchestration/state, integration UX, compatibility/versioning, and the final validated desktop/capture/audio glue. The share could rise if Windows shell parity or custom realtime arbitration is required.

## 14. Unresolved risks requiring real Windows testing

- Build the official Tauri app from a pinned compatible pair of Tauri and N.E.K.O revisions; confirm the backend artifact build, install, restart and clean shutdown.
- Verify transparent full-screen overlay, always-on-top, click-through toggling, interactive avatar hit regions, settings windows, DPI scaling, negative monitor coordinates and mixed-DPI multi-monitor geometry.
- Enumerate/select/capture screens and windows; confirm the Tauri window can be excluded or hidden during capture, source IDs survive refresh safely, minimized/permission-denied windows fail clearly, and monitor order is stable enough for remembered selections.
- Exercise Windows Graphics Capture/portal fallback behavior, screen-share start/stop/source-switch races, and proactive/computer-use screenshot routes on actual Windows versions and GPU drivers.
- Run live microphone, headset and speaker loops on the target WebView/audio devices: STT language accuracy, VAD endpoint timing, SmartTurn false stops/continues, barge-in latency, TTS tail cancellation, echo leakage, device changes and sleep/wake.
- Confirm actual Electron package structure and `app.asar` inspectability against a current official Windows artifact; verify whether `N.E.K.O.-PC` source can be obtained and whether external builds are permitted/reproducible.
- Validate plugin SDK v0.9 migration, permissions/privacy for screen and conversation events, plugin process lifecycle, and pinned Marketplace/local installation across an N.E.K.O upgrade.

No GUI, microphone, speaker, or real screen-capture validation was attempted in Cloud.
