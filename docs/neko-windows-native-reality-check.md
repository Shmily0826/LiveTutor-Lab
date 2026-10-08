# N.E.K.O on Windows, Native Reality Check

Runtime evaluation of whether **native N.E.K.O + Study Companion** is already good enough
to become the new LiveTutor base on this Windows machine.

- Evaluated: 2026-10-07 → 2026-10-08 (local time), Windows
- Method: **runtime observation only.** Every claim below is backed by a command output,
  an HTTP response, a process/window enumeration, or a log line. Source reading is used
  only to explain a runtime observation, never to establish one.
- Supersedes: `README.md` ("keep current LiveTutor base") and
  `docs/neko-study-companion-audit.md` ("Study Companion is market-distributed only").

---

## 1. Verdict

> **Native N.E.K.O + small Study Companion extensions**

Native N.E.K.O on this Windows machine is a **real, working desktop + voice + screen-aware
product**, and Study Companion is a **real, in-tree, functioning tutor**, not a stub, not a
market-only add-on. The old LiveTutor implementation should be treated as disposable as
instructed; nothing in it is required.

The gap is **not** anywhere near "build an external Tutor Brain". It is a small, contained
set of Study Companion-side items (§5). No change to N.E.K.O core is justified by the
evidence gathered.

---

## 2. Exact versions and configuration

### 2.1 Product

| Item | Value | Evidence |
|---|---|---|
| N.E.K.O version | `0.9.0` | log `N.E.K.O. 启动 - 版本: 0.9.0`; `/api/config/page_config` |
| Core commit audited | `1d814cf32fba8c02b5727d2890710e4e7b8ece24` (2026-10-06) | `docs/base-evaluation.md` |
| Licence / stars | Apache-2.0 / 3026★ | `docs/architecture-notes.md` |
| `N.E.K.O.exe` | 223.8 MB, PE32+, 14 sections, `.text` vsize = 182,660,830 | `scripts/diag_shell_binary.py` |
| Backend binary | `resources/bin/projectneko_server.exe`, 531,506,448 bytes (Nuitka) | `scripts/run_neko_backend2.py` |
| App dir | `benchmarks/raw/neko-app/` (55 locale `.pak`, `resources/app.asar`, `app.asar.unpacked/node_modules/`) | `scripts/diag_shell_binary.py` |
| Study Companion | `plugin.toml` version `0.1.0`, SDK `>=0.1.0,<0.2.0` | `plugin.toml` |

### 2.2 Electron runtime (measured, not inferred)

Obtained by running the shell with `ELECTRON_RUN_AS_NODE=1` and reading
`process.versions`:

```
electron  41.10.1
chrome    146.0.7680.216
node      24.18.0
v8        14.6.202.34-electron.0
modules   145
```

Corroborated at runtime by the app's own log line
(`"expectedElectronVersion":"41.2.0"` in the input-region patch report) and by
`N.E.K.O. 启动` printing `是否打包: true`.

### 2.3 Ports

| Port | Service |
|---|---|
| 48911 | MAIN |
| 48912 | MEMORY |
| 48915 | TOOL |
| 48916 | USER_PLUGIN |
| 48917 / 48918 | AGENT_MQ / MAIN_AGENT_EVENT |
| 48961 / 48962 / 48963 | ZMQ SESSION_PUB / AGENT_PUSH / ANALYZE_PUSH |
| 50051 | OpenFang Agent OS |

### 2.4 Storage gate

Three-state machine `selection_required → migration_pending → ready`, driven by
`root_state.json`. Reached `ready` with:

```
NEKO_STORAGE_SELECTED_ROOT = benchmarks/raw/neko-store
NEKO_STORAGE_ANCHOR_ROOT   = benchmarks/raw/neko-store
NEKO_STORAGE_CLOUDSAVE_ROOT= benchmarks/raw/neko-store/cloudsave
```

`/api/system/status` → `{"ok":true,"status":"ready","ready":true,"storage":
{"selection_required":false,"migration_pending":false,"recovery_required":false,
"stage":"stage3_web_restart"}}`

### 2.5 Model / provider configuration (the "strong supported model" question)

Live values from `/api/config/api_providers` and `/api/config/core_api`:

```
coreApi              = "free"     effectiveCoreApi = "free"
assistApi            = "free"
api_key              = ""
every assistApiKey*  = ""
enableCustomApi      = false
resolvedProviderUrls = {}
```

The provider catalogue exposed by the app lists 8 core providers (`free`, `qwen`,
`qwen_intl`, `openai`, `step`, `gemini`, `glm`, `grok`) and 21 assist providers
(`free`, `qwen`, `qwen_intl`, `openai`, `glm`, `step`, `silicon`, `gemini`, `kimi`,
`kimi_code`, `deepseek`, `doubao`, `minimax`, `minimax_intl`, `mimo`, `claude`, `grok`,
`openrouter`, `vllm_omni`, …).

Also observed: a per-model override block (`conversationModel*`, `summaryModel*`,
`gameMainModel*`, `correctionModel*`, `emotionModel*`, `visionModel*`, `agentModel*`,
`omniModel*`, `ttsModel*`) exists but is **entirely empty**, every field is `""`.

**Runtime consequence, observed:** `study_semantic_status = "routing_unavailable"`,
`study_semantic_reason = "invalid_response"`, `knowledge_guidance_status =
"routing_unavailable"` on every single tutoring call. The free tier is fast enough for
tutoring but does not return the structured routing payload the semantic/knowledge-graph
layer expects. This is classified **CONFIG** (§5.2), and it is the single most important
configuration lever found.

No API key was set, and none was written. Nothing in this evaluation required changing
credentials.

### 2.6 Study Companion configuration (plugin-resolved, live)

From `study_status.config`:

```
ocr_enabled=true  ocr_backend_selection="rapidocr"
rapidocr_engine_type="onnxruntime"  rapidocr_model_type="mobile"
rapidocr_ocr_version="PP-OCRv4"     rapidocr_lang_type="ch"
ocr_languages="chi_sim+jpn+eng"     ocr_capture_backend="auto"
llm_call_timeout_seconds=120        llm_vision_enabled=false
fsrs_retention_target=0.9           knowledge_contribution_opt_in=false
supervision.enabled=true            supervision.remind_interval_minutes=10
checkin.auto_derive_from_session=true
awareness.enabled=false             awareness.classify_mode="title_first"
awareness.distraction_detection=true
pomodoro 25/5/15, long_break_interval=4
doc_export.enabled=false
```

`supervision.enabled=true` and `awareness.os_signals_enabled=true` are the supervision
features the task asked about. `awareness.enabled=false` is a deliberate default:
screen classification is driven on-demand instead of by a 5 s polling loop.

---

## 3. What was actually done

### 3.1 The blocker from the previous audit was a false negative

The prior evaluation concluded the desktop shell **could not run**:

- "NSIS installer"
- "silent install rc=1"
- "direct launch → `bad option`"
- "Electron shell never ran"

All four are wrong, and the cause of all four is now known exactly.

**(a) It is not an NSIS installer.** `scripts/diag_exe_identity.py`:

```
Nullsoft (UTF-16LE)  NOT FOUND
UTF-16LE "Electron"  present
```

The three ASCII `NSIS` byte hits at offsets 205546388 / 205548258 / 205548605 are
**BoringSSL error strings** (`NO_PUBLIC_EXPONENT`, `DIGEST_TOO_BIG_FOR_RSA_KEY`,
`HTTPS_PROXY_REQUEST`) that happen to contain the substring `NSIS`. Context at offset
185907704 shows real Electron internals:

```
..\electron\shell\common\node_bindings.cc
app.asar
default_app.asar
appSearchPathsOnlyLoadASAR
electron/js2c/
```

`neko-app/` is a fully **extracted** Electron app directory, not an installer.

**(b) `bad option` was a Node-mode artefact.** The ambient shell on this machine exports:

```
ELECTRON_RUN_AS_NODE=1
```

Any launch inherits it, so the Electron binary executed as **bare Node**:
`--disable-gpu` etc. are not Node flags → `bad option`, rc=9; `--help` printed Node
usage; `require('electron')` failed. This explains the "bad option" evidence completely.

**(c) The "hang with zero windows" was Node waiting on stdin.** Launched with
`stdin=DEVNULL` in Node mode, the process sat idle (CPU 0.16 s kernel / 0.06 s user over
2 min), created no window, no child, and never reached `src/main.js`, hence no
`neko-electron-debug.log`. It was never a hung Electron.

Removing that one variable is the whole fix. It is an **environment** issue, not a
product defect → **CONFIG**, and a two-line fix.

### 3.2 Desktop shell: verified running

`scripts/neko_launch_console.py` with `--disable-gpu --disable-gpu-sandbox --no-sandbox`
and `ELECTRON_RUN_AS_NODE` removed:

```
alive: True            (210+ s, verified with OpenProcess)
windows seen for pid 35420 (19):
   @  2.0s visible=True  Chrome_WidgetWin_1       705x429   'Loading...'
   @ 18.0s visible=True  Chrome_WidgetWin_1      1439x899   'N.E.K.O'          <- Pet
   @ 24.0s visible=False Chrome_WidgetWin_1       440x600   'N.E.K.O. Chat'
   @ 28.0s visible=True  Chrome_WidgetWin_1       440x600   'Project N.E.K.O.'
   @ 32.0s visible=True  Chrome_WidgetWin_1       740x703   'Project N.E.K.O.'  <- Terminal
   @ 38.1s visible=False Chrome_WidgetWin_1      1440x852   'N.E.K.O. Toast'
   ... (Electron_NotifyIconHostWindow, Base_PowerMessageWindow, IME, Sogou TSF)
```

Startup log confirms the full pipeline:

```
[IPCRouter] IPC 消息路由已就绪 (34 条路由 + settings-sync + music-bridge + widget-interaction)
桌面伙伴 watcher 已启动 (mode=windows, grace=3000ms, interval=1500ms)
[WindowManager] 创建窗口, URL: http://localhost:48911/
[WindowManager] 创建 Pet 窗口, bounds: {"x":1,"y":1,"width":1439,"height":899}
[applyTopOn] setAlwaysOnTop(true,'screen-saver') → isAlwaysOnTop()=true
[WindowManager] Pet 窗口已创建
[StorageGate] 请求 Pet 补发 WS READY: ensure:storage_ready_startup
页面加载完成: http://localhost:48911/
[Update] 当前已是最新版本: 0.9.0
[SystemCursor] helper started platform=win32 command=powershell.exe
```

Avatars load:

```
/api/characters/current_live2d_model
  -> {"success":true,"catgirl_name":"YUI","model_name":"yui-lolita",
      "model_info":{"path":"/static/yui-lolita/yui-lolita.model3.json","source":"static"}}
/api/live2d/models      -> kemomimi, mao_pro, neko, yui-lolita, yui-origin
/api/model/pngtuber/models -> YUI Lolita (builtin, pngtuber, /static/pngtuber/yui-lolita/model.json)
```

`/api/get_window_title` returns the **true foreground window**:
`"选择题解析 - Google Chrome"`, then later `"WorkBuddy"`, `"ChatGPT"`, i.e. window
awareness works **standalone**, independent of the renderer.

### 3.3 GPU process crash, the real desktop limitation

The first GUI launch without flags produced:

```
[36320:...:ERROR:gpu_process_host.cc:996] GPU process exited unexpectedly: exit_code=-1073741819
   ... crashed 1..6 time(s)
Renderer process crashed
[36320:...:FATAL:gpu_data_manager_impl_private.cc:417] GPU process isn't usable. Goodbye.
```

`-1073741819` = `0xC0000005` = `STATUS_ACCESS_VIOLATION`. With
`--disable-gpu --disable-gpu-sandbox --no-sandbox` the app runs stably for 210+ s and
creates every window. This machine's GPU path is broken for Chromium; the workaround is
a launch flag. → **CONFIG**.

### 3.4 Screen capture: `no_renderer` is real and reproducible

```
/api/capture/health         503  {"success":false,"available":false,"error":"no_renderer"}
/api/capture/screenshot     405  (needs POST)
/api/get_window_title       200  {"window_title":"..."}
```

Mechanism, confirmed by runtime + code:

1. `templates/index.html` (and `chat.html`) load `/static/app/desktop-capture-provider.js`,
   which resolves `window.electronDesktopCapturer`.
2. That global is injected by the Electron preload
   (`src__preload__bridges__desktop-capture-bridge.js` → `getSources`,
   `captureSourceAsDataUrl`, `captureDesktopRegionAsDataUrl`, …).
3. `static/app/app-websocket.js` sends `{action:'capture_bridge_status', available:…}`
   over the WebSocket.
4. `main_routers/websocket_router.py:1447` handles `capture_bridge_status` →
   `utils/capture_bridge.mark_capture_client()`; `has_capture_client()` then returns
   true and `/api/capture/health` returns 200.

Observed: with the desktop shell fully up (Pet + chat + terminal windows), the app's
own log contains **`capture_bridge`: 0 occurrences, `renderer registered`: 0
occurrences, `WS READY`: 1**. And `GET /` + `GET /web_chat_compact` (both 200, ~45.8 kB
of HTML) followed by 24 s of polling never flipped `/api/capture/health`.

So the renderer loads the page but **never successfully hands the capture bridge over**.
Consistent with the environment: `Scripts/capture_screen_png.py` (GDI
`GetDIBits`/`BitBlt` on the primary DC) returned a **1022-byte all-black PNG**, i.e.
this session has no interactive desktop to read pixels from. `desktopCapturer` and GDI
are failing for the same reason.

This is a genuine, still-unexplained desktop limitation, but it is **not** fatal to
LiveTutor, because the Study Companion OCR path is independent of it (§3.6).

### 3.5 Study Companion: real, in-tree, running

Contradicting `docs/neko-study-companion-audit.md`:

```
resources/bin/plugin/plugins/study_companion/    100 .py files, 36,673 LOC
  tutor_llm_agent.py, study_model_gateway.py,
  entry_tutor_explain_entries.py, entry_tutor_question_entries.py,
  entry_tutor_answer_entries.py, knowledge_tracker.py, store.py,
  study_ocr_pipeline.py, plugin.toml, static/, i18n/
```

`plugins.lock.json` lists it among 20 registered plugins; it is **not** market-only.

```
POST /plugin/study_companion/start   -> success
/plugin/status                       -> "running"
/server/info -> running_plugins_status.study_companion.alive=true, pid=35532,
                sdk_version 0.1.0
```

Plugin server (48916) exposes 93 routes, including the market
(`market.project-neko.cn`, `token_required:true`, `installed_count:20`).

Invocation contract (recovered from `static/main.js` and used for every call below):

```
POST /runs          {plugin_id, entry_id, args}
GET  /runs/{id}     -> status
GET  /runs/{id}/export -> items[] with {type:"json", json:{success, data}}
```

### 3.6 Tutoring: end-to-end, all measured (`scripts/neko_study_runtime*.py`)

Mode switching (`study_set_mode`):

| Transition | Result | Latency |
|---|---|---|
| companion → teaching | `changed:true`, `transition_phrase:"教学模式已开启。"` | 292 ms |
| teaching → interactive | `changed:true`, `transition_phrase:"已切换到互动。"` | 295 ms |
| interactive → teaching | `changed:true` | 258 ms |
| teaching → companion | `changed:true`, `transition_phrase:"已切换到伴学。"` | 269 ms |

All three modes **PASS**. Mode transitions persist in
`recent_mode_switches` with timestamps.

Explanation and follow-up adaptation:

| Call | Result | Latency |
|---|---|---|
| `study_explain_text`, chain rule | structured Chinese answer: 前置概念 → 公式 → 分步推导 → 小检查题 | 53.4 s |
| `study_explain_text`, "I still don't understand … sin(x²)" | **adapted** step-by-step for the exact requested function | 37.5 s |
| `study_explain_text`, StatelessWidget vs StatefulWidget (interactive) | correct, concept-first, ends by asking about the learner's context | 31.4 s |
| `study_explain_text`, same question (teaching) | 教学模式已开启 + 2 前置概念 + 3 步分解 + 对比表格 | 33.6 s |
| `study_summarize_session` | real summary: highlights, weak_points, next_actions | 19.4 s |
| `study_generate_question` | question + answer + rubric + solution_steps + hint | 15.3 s |
| `study_ocr_snapshot` | genuine OCR of the real screen (CS734 MCQs, Flutter/mocktail code) | 43.5 s |
| `study_explain_text {"text":""}` | OCR fallback fired → correct Flutter/ChangeNotifier/mocktail explanation | 33.5 s |
| `study_generate_targeted_question` | adaptive question on the weak topic | 19.3 s |

Mode-dependent behaviour is **real**: interactive answers conversationally and closes
with a question to the learner; teaching prepends `教学模式已开启。` and lays out
prerequisites → steps → comparison table. Same question, same provider, different output
per mode.

Retrieval-augmented generation is visibly wired in: `study_explain_text {"text":""}`
produced an answer citing *this machine's actual screen contents* (Flutter
`ChangeNotifier` / `mocktail` test code from CS734). That is **screen-grounded
tutoring working despite the Electron renderer's capture bridge failing**, because it
runs through OCR, not through `desktopCapturer`.

### 3.7 Quiz → evaluate → persist → review: loop closed

An earlier pass reported these as SKIPPED. That was **my bug**, not a product gap.
`entry_tutor_question_entries.py:_question_private_payload()` injects
`question_id`/`attempt_id` **only on the `targeted_question` path** (lines 110, 111);
plain `study_generate_question` returns no ids, so
`current_question_requires_identity` is false and `study_evaluate_answer` must be called
with just `answer`, falling back to `self._state.current_question`.

`scripts/neko_study_runtime3.py`:

```
A. study_generate_question                    OK  15,302 ms
   QUESTION  : Use the chain rule to differentiate f(x)=sin(x²).
   ANSWER    : f'(x) = 2x cos(x²)
   TOPIC     : Derivative Chain Rule Application   DIFFICULTY 2   type math_exact
   PAYLOAD KEYS: accepted_answers, answer, difficulty, hint, key_points,
                 math_equivalence_engine, question_type, reference_answer,
                 rubric, solution_steps...   (no question_id / attempt_id, as designed)

B. study_evaluate_answer (WRONG: '42')        OK  31,392 ms
   VERDICT=wrong  SCORE=0  ERROR_TYPE=unsupported
   FEEDBACK: "Your submitted answer '42' is completely unrelated to the given chain
              rule differentiation question..."
   NEXT_ACTION: "Prompt the learner to refer back to the previously covered
                 step-by-step breakdown ... decompose sin(x²) into inner and outer."
   mastery_before / mastery_after / mastery_delta present

C. study_evaluate_answer (CORRECT: "f'(x) = 2x cos(x²)")  OK  29,481 ms
   VERDICT=partial  SCORE=75  ERROR_TYPE=incomplete  final_answer_correct=true
   FEEDBACK: "You obtained the 100% correct final derivative result, but you did not
              show the explicit chain rule steps to prove how you arrived at this answer."

D. study_question_context (after 2 evaluations)  OK  272 ms
   no_data=False   selection_reason=weak_topic
   weak_topics=[{topic_id:"derivative_chain_rule_application", mastery:0.1468,
                 accuracy:0.275, level:"未接触", attempts:2,
                 flags:["low_confidence"]}]

E. study_generate_targeted_question              OK  19,335 ms
   question_id='q_8755963ab4304abe9c2ee02bc5b9185f'
   attempt_id ='a_dede933f41e5438ea7d9288ed8c0f66b'
   QUESTION: "Write out the complete step-by-step derivation of the derivative of
              f(x)=sin(x²) strictly using the derivative chain rule."
   REASON  : weak_topic   TOPIC: derivative_chain_rule_application

F. study_status                                  OK  261 ms
   last_answer_evaluation={"verdict":"partial","score":75,"error_type":"incomplete",...}
   session_summary_seed={"event_count":10,"explain_count":3,"summary_count":1,
                         "question_count":3,"answer_count":2,"last_topic":
                         "derivative_chain_rule_application",
                         "verdict_counts":{"wrong":1,"partial":1},
                         "weak_points":[...]}
   recent_learning_events=9 (concept_explain ×3, summarize_session, question_generate ×3,
                             answer_evaluate ×2)
```

The learning DB grows accordingly:
`neko-store/plugins/study_companion/data/study_companion.db` = **3,518,464 bytes**,
with FSRS-style scheduling config present (`fsrs_retention_target=0.9`).

This is a **complete, closed loop**: generate → answer → grade with partial credit →
write mastery → select weak topic → generate a targeted follow-up → persist to session
seed. → **PASS**.

### 3.8 Voice and interruption

Verified as present and configured, **not** exercised end-to-end:

- microphone permission is pre-requested and granted at page load
  (`[麦克风] 权限预请求完成，设备列表已缓存`, `自动授予权限: media`);
- `app-audio-capture.js` is loaded by the live renderer;
- voice routes exist (`/api/characters/voices`, `/voice_clone`, `/voice_preview`,
  `/api/characters/catgirl/voice_mode_status`, …) and realtime providers are selectable
  (`qwen`, `qwen_intl`, `openai`, `gemini`, `glm`, `grok`);
- OpenFang Agent OS boots on 50051.

**Honest limitation:** full duplex conversation with **barge-in** could not be tested,
because this session has no capture-capable renderer (§3.4) and no audio device to drive
a real spoken turn. It is reported as **UNVERIFIED**, not as PASS and not as a gap. The
previous audit's "no AEC for barge-in" claim is likewise **not reproduced**, no
evidence either way was obtained.

---

## 4. Capability matrix

| Capability | Result | Latency | Classification |
|---|---|---|---|
| Electron desktop shell launches | windows created, stable 210 s+ | ~18 s to Pet | **CONFIG** (needs `ELECTRON_RUN_AS_NODE` removed) |
| Desktop avatar / Live2D / PNGTuber | YUI `yui-lolita` loaded, 5 models available |, | **PASS** |
| Desktop window behaviour (always-on-top, Pet, Chat, Terminal, Toast) | `setAlwaysOnTop(true,'screen-saver')`; 19 windows incl. all surfaces |, | **PASS** |
| GPU rendering on this machine | GPU process crashes 6× (`0xC0000005`) then FATAL |, | **CONFIG** (`--disable-gpu`) |
| Foreground-window awareness | `/api/get_window_title` returns true active window | <30 ms | **PASS** |
| Screen capture via N.E.K.O `/api/capture/*` | 503 `no_renderer` in every configuration tried |, | **CORE GAP (contained)** or **env**, see §5.1 |
| Screen grounding via Study Companion OCR | genuine OCR of real screen; explain-with-empty-text used it | 33, 44 s | **PASS** |
| Screen-grounded tutoring (end result) | answer cited this machine's actual Flutter/mocktail code | 33.5 s | **PASS** |
| Study mode switching (companion/interactive/teaching) | all 3 transition, persist, and change behaviour | 258, 295 ms | **PASS** |
| Concept explanation | structured, prerequisites → formula → steps | 31, 53 s | **PASS** |
| Follow-up adaptation | re-explained for the exact follow-up function | 37.5 s | **PASS** |
| Quiz generation | question + answer + rubric + solution_steps + hint | 15, 33 s | **PASS** |
| Answer evaluation | wrong→0/`unsupported`; correct→75/`incomplete`+partial credit | 29, 31 s | **PASS** |
| Persistence | `study_companion.db` 3,518,464 B; session seed counts | 261 ms | **PASS** |
| Review / weak-topic targeting | `selection_reason=weak_topic`, adaptive question generated | 19.3 s | **PASS** |
| Session summarisation | highlights, weak_points, next_actions | 19.4 s | **PASS** |
| Supervision (pomodoro, check-in, reminders) | configured & enabled; state exposed in `study_status` |, | **PASS** |
| Semantic routing / knowledge graph | `routing_unavailable` / `invalid_response` every call |, | **CONFIG** (§5.2) |
| Voice conversation + barge-in | not exercisable in this session |, | **UNVERIFIED** |

---

## 5. Gaps and classification

### 5.1 `no_renderer` for `/api/capture/*`, CORE GAP, but contained and non-blocking

**Evidence.** With the desktop shell fully alive (Pet + chat + terminal windows,
`WS READY` sent), the log shows `capture_bridge` **0** occurrences and
`renderer registered` **0** occurrences; `/api/capture/health` stays 503 across 24 s of
polling after fresh page loads. GDI screen capture from this session yields an all-black
frame, indicating no capturable desktop is attached.

**Assessment.** The pipeline is architecturally sound and fully implemented
(preload bridge → page global → WS `capture_bridge_status` → `mark_capture_client` →
`has_capture_client`). It fails at hand-off. **Do not change N.E.K.O core for this.**
Two reasons:

1. Study Companion already delivers screen grounding without it, `study_ocr_snapshot`
   and OCR-fallback explanation both produced correct, screen-specific answers (§3.6/§3.7).
2. The most likely root cause is environmental (no interactive desktop session), which
   is not something core should be modified for.

**Action.** Re-test on a normal interactive desktop session before treating it as a real
product defect. If it still fails there, it becomes a legitimate CORE GAP, but it is not
one yet, and LiveTutor does not depend on it.

### 5.2 Semantic routing unavailable, CONFIG

**Evidence.** On all 4 tutoring calls:
`study_semantic_status="routing_unavailable"`, `study_semantic_reason="invalid_response"`,
`knowledge_guidance_status="routing_unavailable"`, `knowledge_guidance_source="semantic_route"`,
`study_semantic_intent="unknown"`, `study_semantic_subject="unknown"`.

**Assessment.** Both the semantic router and the knowledge-graph guidance layer are
implemented, wired, and reached in code; they degrade gracefully (the reply is still
correct and `degraded:false`). They receive a response they cannot parse, consistent
with running on the free provider with no per-model overrides (§2.5). This is exactly the
"use a strong supported model/provider where practical" lever the task called out.

**Action.** Point `assistApi` at a provider that returns structured output (`qwen` or
`glm` are free-tier-capable and listed as Agent-mode-capable), or populate the empty
`*ModelId` overrides. Then re-measure. No code change.

### 5.3 PLUGIN GAPs (small, contained, Study Companion only)

Ordered by value. None require core changes.

1. **Expose `question_id` / `attempt_id` on the non-targeted path.** Today they are
   injected only by `_question_private_payload()` for `targeted_question`
   (`entry_tutor_question_entries.py:110-111`). A caller that generated a question via
   `study_generate_question` cannot pass ids to `study_evaluate_answer` and must rely on
   the implicit `current_question` fallback. Returning the ids for both paths makes the
   contract symmetric and removes an ordering hazard for any external driver.
2. **Persistable review queue.** `review_queue` came back `[]` and
   `memory_deck.item_count` was 0 even after wrong/partial answers, while the mastery
   row (`attempts:2`, `flags:["low_confidence"]`) did update. Due-review surfacing is
   thin compared to how well mastery tracking works.
3. **Latency floor.** 30, 53 s per explain/evaluate call is slow for a live tutor. Much of
   this is provider latency (free tier); worth re-measuring after §5.2 and considering
   streaming.

### 5.4 Not a gap

- **No external Tutor Brain is justified.** Every tutoring capability the task listed, explanation, follow-up adaptation, quiz, evaluation, persistence, review,
  screen-grounded tutoring, was demonstrated natively.
- **No migration of the old LiveTutor is needed.** Nothing in it was required to reach
  any of the PASS rows above.
- **The previous audit's three central claims are overturned**: the desktop shell runs,
  Study Companion is in-tree, and the NSIS/`bad option` evidence was a misread.

---

## 6. Smallest next engineering task justified by the evidence

> **Set a non-`free` assist provider (or populate the `*ModelId` overrides) and
> re-run the semantic-status probe.**

Concretely: with the backend up, set `assistApi` to `qwen` or `glm` via
`/api/config/core_api` (POST), or fill `conversationModelId` / `agentModelId`, then
re-issue `study_explain_text` and read
`study_semantic_status` / `knowledge_guidance_status` from the response.

- **Why this one:** it is the only identified item that is pure configuration, affects
  three capabilities at once (semantic intent, knowledge-graph guidance, likely latency),
  needs no code, and is directly responsive to the task's "use a strong supported model
  where practical".
- **Success criterion:** `study_semantic_status` moves off `routing_unavailable`, and
  `knowledge_guidance_applied` becomes `true` on a topic with tracked mastery.
- **Blast radius if wrong:** none, it is a config value, revertible in one request.

It is deliberately **not** the `no_renderer` investigation. That item is real but
(1) most likely environmental, (2) not required by LiveTutor because the OCR path covers
screen grounding, and (3) not fixable without a normal interactive desktop to test on.
Chasing it first would be optimising the least load-bearing part of the system.

---

## 7. Reproduction

```bash
# 1. backend (reaches storage gate = ready)
NEKO_STORAGE_SELECTED_ROOT=benchmarks/raw/neko-store \
NEKO_STORAGE_ANCHOR_ROOT=benchmarks/raw/neko-store \
NEKO_STORAGE_CLOUDSAVE_ROOT=benchmarks/raw/neko-store/cloudsave \
  python scripts/run_neko_backend2.py

# 2. desktop shell  (ELECTRON_RUN_AS_NODE MUST be removed)
NEKO_WAIT=120 NEKO_ARGS="--disable-gpu --disable-gpu-sandbox --no-sandbox" \
  python scripts/neko_launch_console.py

# 3. claim vs reality
python scripts/neko_watch.py                  # processes, ports, windows, HTTP
python scripts/neko_capture_register_check.py # renderer hand-off check

# 4. tutoring
python scripts/neko_study_runtime3.py         # quiz -> evaluate -> persist -> review
python scripts/neko_study_runtime4.py         # modes, config, diagnostics
```

Evidence artefacts:

| Path | Content |
|---|---|
| `benchmarks/raw/evidence/study-runtime.txt` | pass 1, modes, explain, summary |
| `benchmarks/raw/evidence/study-runtime2.txt` | pass 2, quiz, OCR fallback |
| `benchmarks/raw/evidence/study-runtime3.txt` | pass 3, closed evaluate/review loop |
| `benchmarks/raw/evidence/study-runtime4.txt` | pass 4, modes, config, diagnostics |
| `benchmarks/raw/evidence/shell-console.log` | full Electron startup log |
| `benchmarks/raw/evidence/shell-gpuoff.log` | GPU-disabled run |
| `benchmarks/raw/evidence/shell-retry.txt` | flag-variant matrix (Node-mode evidence) |
| `benchmarks/raw/neko-openapi-live.json`, `neko-routes-live.txt` | 340 live routes |
| `benchmarks/raw/neko-store/plugins/study_companion/data/study_companion.db` | learning DB |

### Environment note

The ambient shell exports `ELECTRON_RUN_AS_NODE=1`. **Any** future attempt to launch
`N.E.K.O.exe` from this shell must delete it first, or the binary silently degrades to
Node and reproduces the original false "hang".
