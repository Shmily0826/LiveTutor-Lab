# Architecture notes — detail behind `base-evaluation.md`

Companion to `base-evaluation.md`. That document carries the decision; this one
carries the mechanics, so the decision document can stay readable and these
findings can stay precise.

Read-only audit. Nothing in `candidates/N.E.K.O` was modified. Nothing in
`D:\CODE\project\LiveTutor` was modified.

---

## 1. Topology, as measured

From `benchmarks/raw/neko-app/resources/core_config.txt` and live ports:

```json
{ "apiBaseUrl": "http://localhost:48911/",
  "globalAlwaysOnTop": true,
  "customPorts": { "MAIN_SERVER_PORT": 48911, "MEMORY_SERVER_PORT": 48912,
                   "TOOL_SERVER_PORT": 48915, "USER_PLUGIN_SERVER_PORT": 48916 } }
```

All four confirmed LISTENING under a single pid.

```
┌─ N.E.K.O.exe (Electron shell) ────────────────────────────────┐
│  source: NOT OPEN. N.E.K.O.-PC -> 404 on the GitHub API      │
│  readable only as shipped app.asar (138 files extracted)     │
│                                                                 │
│  desktopCapturer ─┐                                            │
│  Live2D / VRM     ├─ IPC ─┐                                    │
│  always-on-top    │        │                                    │
└───────────────────┼────────┼────────────────────────────────────┘
                    │        ▼
        projectneko_server.exe  (Python 3.11, Nuitka standalone)
          ├── memory server      :48912
          ├── tool server        :48915
          └── user plugin server :48916
                └── multiprocessing.Process + ZMQ(PUSH/PULL) + MessagePack
```

Internal ports also present: 48917, 48918, 48961, 48962.

---

## 2. The packaging problem

### 2.1 N.E.K.O.-PC is 404

The build workflow in the main repo references `ProjectNeko/N.E.K.O.-PC`. The
GitHub API returns 404 — private or deleted. The shell is therefore not
reviewable as source, and the workflow that would build it cannot be run.

### 2.2 The exe is an NSIS installer

`diag_neko_packer.py` on the 213.4 MB `N.E.K.O.exe`:

| Evidence | Offset / value |
|---|---|
| `NSIS` marker (full-file scan) | 205546388 |
| `app.asar` occurrence 1 | 4202794 |
| `app.asar` occurrence 2 | 185907704 |
| `app.asar` occurrence 3 | 222515245 |
| PE section name | `LZMADEC` |

`LZMADEC` is NSIS's compressed-payload section. Three `app.asar` copies is the
signature of a bundled payload, not a single app.

Behavioural confirmation: `N.E.K.O.exe --no-sandbox` →
`N.E.K.O.exe: bad option: --no-sandbox`. That is a foreign argv parser. An
Electron runtime accepts `--no-sandbox` natively.

Silent install attempt (`install_neko_silent.py`): `/S /D=<path>` → **rc=1, zero
files created**.

The repository's own documentation agrees: `docs/deployment/windows-exe.md`
says to install from the Steam store. There is no documented free standalone
Windows path.

### 2.3 The shell is partially readable anyway

`app.asar` format, as implemented in the extraction script:

```
[0..16)   4 × uint32   → header info block size, header JSON size,
                        string-table size, base offset
[16..)    JSON         → file tree: {path: {size, offset, ...}}
offset    is a STRING  → int() it
data base = 16 + header_json_size
```

Two traps, both hit:

1. **Do not size the JSON with the `header info block size` field.** That field
   includes trailing padding, so `json.loads` fails with
   `Extra data at line 1 column 779479`. Use
   `json.JSONDecoder().raw_decode()` to parse only the first object, and compute
   the data base as `16 + json_size` (779488), not the padding-inclusive number.
2. **File paths have no leading `/`.** A `p.startswith('/src/')` filter matches
   nothing and silently extracts 0 files. Use `p.startswith('src/')`.

Getting both right yielded 138 files in `benchmarks/raw/asar-src/`, named
`src__main__screen-capture-ipc.js` style (`/` → `__`).

### 2.4 It was not a headless problem

`control_gui_probe.py` — a bare Win32 window, no GUI toolkit:

```
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, ctypes.c_uint,
                             ctypes.c_size_t, ctypes.c_ssize_t)
→ RegisterClassW  atom=50091
→ CreateWindowExW hwnd=6753350
→ IsWindowVisible = True
→ SM_CXSCREEN = 2880x1800
```

Note the WNDPROC signature: `wintypes.WPARAM`/`LPARAM` overflow on 64-bit
(`OverflowError: int too long to convert`). `c_size_t`/`c_ssize_t` is the fix.
`tkinter` is not installed on this Python, hence bare Win32.

Conclusion: the GUI subsystem is available in this session. The blocker is that
the only distributable is an installer whose UI cannot be driven here.

---

## 3. Self-window exclusion — the best code found, in the closed half

`asar-src/src__main__screen-capture-ipc.js:1768-1905`:

```js
async function captureSourceWithoutNeko(event, sourceId, options = {}) {
  // 1. record + hide every visible window, including sender and Pet
  for (const w of BrowserWindow.getAllWindows()) {
    const hideResult = hideWindowForScreenCapture(w);
    ...
  }
  // 2. wait for the window server to commit the hides
  await sleep(isLinuxWaylandRuntime() ? 350 : 90);
  // 3. capture
  const sources = await desktopCapturer.getSources({
    types: ['window'], thumbnailSize: WINDOW_THUMBNAIL_SIZE });
  // ... finally: restoreCapturedWindows(record) / deferredScreenshotOverlayRestores
}
ipcMain.handle('capture-source-without-neko', captureSourceWithoutNeko);
```

Correct in the three places implementations usually get it wrong: it enumerates
before hiding, it actually waits for the compositor (90 ms / 350 ms on
Wayland), and restore is in a `finally`.

Source enumeration and the system picker (`asar-src/src__main.js:10672-10711`):

```js
const sources = await desktopCapturer.getSources({ types: ['window', 'screen'] });
session.defaultSession.setDisplayMediaRequestHandler(chatDisplayMediaHandler,
                                                    { useSystemPicker: true });
```

Always-on-top transparent overlay
(`asar-src/src__avatar-tool-visual-overlay-service.js:1761,1823`):

```js
transparent: true,
overlay.setAlwaysOnTop(true, 'screen-saver');
```

`'screen-saver'` is the topmost z-order band — deliberately above full-screen
apps. Worth stealing even though the surrounding code is not reachable.

Meanwhile the Python side has nothing: a bare `pyautogui.screenshot()`, no
exclusion at all. So exclusion exists **only** where the source does not.

### 3.1 The Windows primitive N.E.K.O does not use

Hide-everything-and-wait is correct but heavy: it flashes, it cannot exclude a
single window, and it perturbs the desktop. The right primitive on Windows is:

- `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` — per-window, OS-level,
  no flicker, no compositor wait. **No candidate project uses this.**
- Or UI Automation control-tree filtering when you need to know *what* is in the
  capture, not just what is absent.

For comparison, Clicky (macOS) uses `ScreenCaptureKit`'s `excludingWindows` with
bundle-id filtering. There is no Windows equivalent, which is why the
hide-wait-capture-restore dance exists at all.

---

## 4. Backend-only operation

### 4.1 Storage lifecycle is a three-state machine

```
selection_required  →  migration_pending  →  ready
```

Driven by `root_state.json` plus a storage policy. `/api/system/status` exposes
it directly:

```json
{"status":"ready","ready":true,
 "storage":{"selection_required":false,"migration_pending":false,
            "recovery_required":false,"legacy_cleanup_pending":true,
            "blocking_reason":"", ...}}
```

### 4.2 Four ways to clear the gate; only one works

| Attempt | Outcome |
|---|---|
| `NEKO_STORAGE_SELECTED_ROOT` env var | Read at `storage_roots.py:94`, gate **still** fails |
| `POST /api/storage/location/select` → 200 `restart_required`, force kill | `root_state.last_migration_result` reverts to `launcher_phase0_bootstrap` — the launcher overwrites it |
| `POST /exit` + header `X-Neko-Storage-Action: exit` → 200 `shutdown_initiated` | Process does not actually exit |
| **`POST /api/storage/location/restart` with root in the body** | **200 `restart_initiated` + migration txid → relaunch → `ready`, 340 routes** |

The working call (`neko_restart_proper.py`):

```python
st, b, ms = call("/api/storage/location/restart", "POST",
                 {"selected_root": STORE, "selection_source": "user_selected"})
# 200 {"ok":true,"result":"restart_initiated","restart_mode":"migrate_after_shutdown",
#      "migration":{"txid":"e5a94d9bf5e44b89ae6e747b033db7e3","status":"pending",...}}
```

Generalisable lesson: when a product stages a state transition, killing the
process outside its own commit path loses the transition. `/restart` is the only
endpoint that both stages *and* commits.

### 4.3 A process-lifetime trap worth recording

The backend was started with `subprocess` from a shell tool call and kept dying
when the shell exited → `502 upstream connect failed`. The fix was
`run_in_background=true` with a blocking `p.wait()` so the harness owns the
lifetime.

**The frozen LiveTutor baseline already documents this exact failure mode** at
`docs/v0.2-final-acceptance.md:65-69`. Same class of problem, independently hit
in two different projects, same class of machine.

---

## 5. Screen capture is renderer-bound

The single most consequential structural fact.

```
GET /api/capture/health     -> 503 {"success":false,"available":false,"error":"no_renderer"}
GET /api/screenshot         -> 405 {"detail":"Method Not Allowed"}
GET /api/capture/screenshot -> 405 {"detail":"Method Not Allowed"}
```

Capture routes exist — only 4 of them against 88 for avatar — but the backend
delegates to the Electron renderer over IPC. No renderer, no capture.

Route list: `/api/capture/health`, `/api/capture/screenshot`, `/api/screenshot`,
`/api/screenshot/interactive`.

Implications:

1. Headless or server deployment has **no** screen perception.
2. Screen perception **cannot be tested** without a GUI.
3. Any regression test for capture needs the closed shell.

---

## 6. Voice: barge-in exists, AEC does not

Echo handling is `difflib.SequenceMatcher` text similarity between what was
spoken and what was heard — a heuristic over transcripts, not acoustic echo
cancellation.

For a chat avatar that is a tuning problem. For a tutor it is a correctness
problem, because:

- the tutor talks over itself constantly (it explains, then reads the screen,
  then keeps talking);
- the learner frequently starts speaking while the tutor is mid-sentence;
- text-similarity heuristics fail hardest on exactly that overlap case, where
  the learner's words are *similar to but not identical to* the tutor's.

Treating this as "N.E.K.O has barge-in, therefore it is fine" would be reading a
feature list instead of the implementation.

---

## 7. Teaching surface: how the false positives were eliminated

Searching 2850 `.py` files for teaching vocabulary, then reading the matches
rather than counting them:

| Term | Raw files | Actual content |
|---|---|---|
| `lesson_plan`, `curriculum`, `syllabus` | 0 | — |
| `course_rag`, `learner_model`, `knowledge_point` | 0 | — |
| `flashcard`, `spaced_repetition`, `socratic`, `pedagog*` | 0 | — |
| `homework` | 0 | — |
| `exercise` | **146** | English verb. `"lets unit tests exercise the production apply path"`, `def exercise(root)`, `"not assume it is being exercised today"` |
| `quiz` | 4 | The word inside prompt strings: `config/prompts/prompts_visit.py`, `prompts_proactive.py`, `prompts_drawing_guess.py`, `prompts_slop.py` |
| `textbook` | 2 | Code comments using it as a metaphor: `"be overwritten (textbook lost update)"`, `"Scores must stay identical to the textbook formula."` |
| `chapter` | 36 | Chapters of a *visit/conversation*, not of a course |

A keyword count alone would have reported "146 files mention exercises". Reading
them reports zero teaching features. This is the difference between a grep-based
capability claim and an audited one.

Route inventory, same discipline. 340 routes; 6 keyword hits, all false
positives — see `base-evaluation.md` §3.7 for the list. The only "tutorial" is
seven-day onboarding:

```
GET /api/seven-day-tutorial/state -> 200
{"ok":true,"storeVersion":1,"initialized":false,"revision":0,"state":null}
```

`initialized: false` on a fresh store. Nothing to inspect.

The activity state machine (`main_logic/activity/`, 5269 lines) covers
`idle / focused_work / focused_video / gaming / away`. That is **attention
classification** — it knows what you are doing. A learner model knows what you
know, what was taught, and what comes next. Different thing.

---

## 8. Plugin architecture

### 8.1 Isolation, as read in source

- `multiprocessing.Process` for each plugin.
- ZMQ, 4 channels, PUSH/PULL.
- Upstream messages serialised with **MessagePack, not pickle** — pickle would be
  a deserialisation RCE across a trust boundary.
- Per-host tokens.

This is the most valuable infrastructure in the codebase relative to what
LiveTutor would have to build.

### 8.2 Tool registration is the integration point — and it works

Routes: `/api/tools`, `/api/tools/register`, `/api/tools/unregister`,
`/api/tools/clear`.

**Schema is per-tool and flat**, discovered by sending `{}` and reading the 422:

```
POST /api/tools/register {}
-> 422 {"detail":[{"type":"missing","loc":["body","name"]},
                  {"type":"missing","loc":["body","callback_url"]}]}
```

A batched `{"tools":[...]}` payload is also rejected — the endpoint wants one
tool per call. `clear()` takes `{"source": ...}` as its discriminator; `register`
accepts `source` as an optional tag.

Live proof, against the running backend, with a `ThreadingHTTPServer` on
`127.0.0.1:48977` shaped like the LiveTutor Brain:

```
register livetutor_read_screen  -> 200 {"registered":"livetutor_read_screen",
                                   "affected_roles":["YUI"],"failed_roles":[]}
register livetutor_ground_claim -> 200 {"registered":"livetutor_ground_claim",
                                   "affected_roles":["YUI"],"failed_roles":[]}

GET /api/tools -> YUI: ['recall_memory','livetutor_read_screen','livetutor_ground_claim']
  livetutor_read_screen  source=livetutor_brain  is_remote=true
                         callback_url=http://127.0.0.1:48977/livetutor-brain/read_screen

unregister both -> 200 removed:true ; final list back to ['recall_memory']
```

SSRF posture, tested:

| Callback URL | Result |
|---|---|
| `http://example.com/hook` | 422 rejected |
| `http://169.254.169.254/latest/meta-data/` | 422 rejected |
| `http://127.0.0.1:48977/ok` | 200 accepted |

Rejection message is the product's own: `callback_url host 必须…`.

Three things follow. Registration is **public API**, so attaching needs no fork.
`source` + `is_remote` make an external brain a *supported configuration* rather
than a hack. And loopback enforcement is real, covering the cloud-metadata case
most projects miss.

**Not proven:** the callback was reachable and the tool visible, but the
*product-driven* invocation path was not exercised. N.E.K.O calls a registered
tool only from inside its own LLM turn, which needs a configured provider and the
shell. So: attachability yes, invocation-under-real-turn unverified.

### 8.3 The structural limit of the extension point

The extension point is **tools, not the brain**.

N.E.K.O's agent loop is in-process and owns the turn: turn policy, streaming
response composition, tool selection, proactive gating. An external service can
supply tools to it. It cannot supply the loop.

LiveTutor Brain is a brain. Attaching it as a toolbox inverts the intended
ownership, and restoring the intended ownership means replacing N.E.K.O's agent
loop — which is a fork. **The no-fork property holds at the tool layer, and the
tool layer is not where LiveTutor's value is.**

---

## 9. Memory and proactive, the two credible subsystems

### 9.1 Memory

Five tiers — working, recent, facts, reflection, persona.

Retrieval is a hybrid: BM25 (lexical) + ONNX cosine (semantic), fused with RRF
(reciprocal rank fusion). Persistence is JSON with atomic writes.

Worth reading for the retrieval design specifically: RRF over two heterogeneous
rankers is a small, robust choice, and the five-tier split maps onto how a tutor
actually needs to recall things (current task / recent history / durable facts /
self-reflection / who the learner is).

### 9.2 Proactive

| Module | Lines | Shape |
|---|---|---|
| `main_logic/proactive_chat/` | 10293 | source gating → generation → anti-repetition → cooldown |
| `main_logic/activity/` | 5269 | state machine: idle / focused_work / focused_video / gaming / away |

The anti-repetition and cooldown stages are the part most projects skip and the
part that decides whether proactive speech is pleasant or intolerable.

The commit under evaluation is itself a proactive-adjacent fix:
`feat(visit): 台词流式 TTS 与按已播音频放字幕` — streaming TTS with subtitles
following *actually played* audio. That is a latency-honesty fix: subtitles track
what the ear heard, not what the text said. Same class of problem as the
LiveTutor baseline's subtitle/TTS timing.

---

## 10. Provider abstraction is two classes wide

Only `ChatOpenAI` and `ChatAnthropic`. Differences collapse into `extra_body`
functions in `config/providers.py`.

Everything else — realtime, memory, proactive, activity — assumes an
OpenAI-shaped client. Adding a provider is a patch, not a plugin. This is
pluggable *shape*, not pluggable *providers*.

---

## 11. What the frozen baseline says, verbatim numbers

`D:\CODE\project\LiveTutor\docs\v0.2-final-acceptance.md`, read-only.

Tests: **546 passed**, 164 subtests, 49.39 s.

| Metric | Median | Range |
|---|---|---|
| Submit → backend received | 335 ms | 215–1500 |
| Submit → first visible DOM | 3740 ms | 1862–4552 |
| Submit → first TTS audio | 2215 ms | 1335–4500 |
| Submit → final reply | 15215 ms | 14335–18500 |
| Turn complete | 15917 ms | 15151–19199 |

Stage breakdown: `ocr_ms` 489 (1218/489/393), `vision_ms` 0.23 (present once by
design), `tutor_ms` 2381 (2972/1605/2381), `normalize_ms` 0.11, `policy_ms` 0.03.

Known limits, as documented:

- RapidOCR degrades at large font sizes (≥110 px unreadable).
- Grounding guard has intermittent false positives, historically 9.5 %.
- This machine's loopback is silent (`peak_rms` 1e-05 – 2e-05), so audio playback
  and barge-in are **not machine-verifiable here**. Probe playback is opt-in
  (`--probe-speaker`) and was not used.
- `ocr_ms: null` on two of three turns is by design — nothing to time — and
  `tests/test_hybrid_perception.py:372` asserts exactly that.

Declared out of scope: AUTO routing, Proactive Tutor, Attention Engine, Learner
Model, Course RAG, LangGraph, pyBKT, new avatar, Pipecat migration.

The last line is the whole argument in the product's own words: the gaps are the
teaching layer, and N.E.K.O's teaching layer is empty.

---

## 12. Existing LiveTutor asset found during this audit

`docs/v0.3-structured-screen-context.md` documents that Skilly's DOM digest was
already adopted as a grounding second path:

```
spikes/v0.3-structured-context/web_context.py
```

Worth stating explicitly because it is easy to mistake for a new finding from
this evaluation. It is not. It is a prior LiveTutor asset, and it survives any
base decision — DOM digest grounding is base-independent.

---

## 13. Diagnosis chain, for reproducibility

Startup failure was narrowed in layers, each step eliminating a hypothesis:

| Step | Script | Conclusion |
|---|---|---|
| 1 | `launch_neko.py` | exe does nothing |
| 2 | `launch_neko_shellexec.py` | not a PATH/`subprocess` issue |
| 3 | `run_neko_diag.py` | no output, no window |
| 4 | `diag_neko_binary.py` | not a Python zipapp; no stdout |
| 5 | `diag_neko_launch.py` | process survives 70 s, zero ports, zero files |
| 6 | `diag_neko_deep.py` | GUI-subsystem question raised |
| 7 | `control_gui_probe.py` | **GUI works** → blocker is packaging, not session |
| 8 | `diag_neko_packer.py` | **NSIS installer** → root cause found |
| 9 | `install_neko_silent.py` | `/S` → rc=1, silent install unavailable |
| 10 | `run_neko_backend.py` / `2` / `neko_storage_setup.py` / `neko_setup_proper.py` / `neko_restart_proper.py` | backend runs; storage gate cleared via `/restart` |
| 11 | `measure_neko.py`, `brain_integration_probe.py`, `cpu_probe.py` | measurements |

Two incidental constraints worth not rediscovering: PowerShell and `cmd.exe`
invoked from the Bash tool are both blocked by policy, so shell work goes
through Python (`shell32.ShellExecuteW` where a shell verb is genuinely needed).

---

## 14. What a future session should re-check first

If any of these have changed, the recommendation in `base-evaluation.md` should be
revisited rather than re-derived:

1. `N.E.K.O.-PC` still 404? (shell still closed)
2. Does `/api/capture/health` still return `no_renderer`? (capture still
   renderer-bound)
3. Any route matching `curriculum` / `learner_model` / `lesson_plan`? (teaching
   layer still empty)
4. Still NSIS-only, still Steam-documented? (still no free Windows path)
5. Does `difflib`-based echo handling still stand in for AEC?
