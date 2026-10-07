# Base Architecture Evaluation — is N.E.K.O a viable substrate for LiveTutor?

**Question under evaluation:** can Project N.E.K.O replace the base architecture of
LiveTutor, or should LiveTutor keep its current base?

**Verdict: A — stay on the current LiveTutor base. Do not migrate.**

**Date of evaluation:** 2026-10-08
**Evaluator:** read-only. No N.E.K.O file was modified. No LiveTutor file was modified.
**Frozen baseline:** LiveTutor @ `pre-base-reevaluation-2026-10-07` (branch `v0.3-structured-context`)

---

## 0. How to read this document

Sections 1–7 are evidence. Sections 8–13 are judgement.

Two words are used with deliberately different meanings throughout:

- **IMPLEMENTED** — found in the shipped product surface (a live route, or source
  reached from a shipped entry point) and the code does the thing it claims.
- **BLOCKED** — could not be verified in actual use on this machine. Not the same
  as "absent", and not the same as "present". Do not read BLOCKED as a negative
  finding about N.E.K.O; read it as a limit of this evaluation.

One finding is load-bearing and worth stating before the detail:

> **The decisive integration question is answered YES, empirically.**
> An external HTTP brain service registered two custom tools into the running
> N.E.K.O backend, they became visible to the agent role, callback URLs are
> loopback-enforced, and the tools unregister cleanly — with **zero** N.E.K.O
> source changes. Evidence: `benchmarks/raw/evidence/brain-integration.txt`.
>
> N.E.K.O is genuinely pluggable. It is just not a *tutor*.

---

## 1. Exact repo and version tested

| Field | Value |
|---|---|
| Repository | `ProjectNeko/Project-N.E.K.O` (GitHub) |
| Commit | `1d814cf32fba8c02b5727d2890710e4e7b8ece24` |
| Commit date | 2026-10-06 22:09:20 -0700 |
| Commit subject | `feat(visit): 台词流式 TTS 与按已播音频放字幕、隔离会话池（串门 PR-C3a-2，PR-09a 第二段） (#3313)` |
| Clone | `candidates/N.E.K.O`, depth 50, own git history preserved, gitignored |
| Licence | Apache-2.0 |
| Stars at evaluation | 3026 |
| Language | Python, `python_requires == 3.11.*` |
| Repo size | ~752 MB, 2850 `.py` files |
| Desktop shell version | `0.9.0` (from `package.json` extracted out of the shipped `app.asar`) |

The commit is two days old at evaluation time and is a *feature* commit, not a
release commit. Nothing was cherry-picked or patched.

### 1.1 The desktop shell is not in this repository

`ProjectNeko/N.E.K.O.-PC` returns **404** on the GitHub API — private or
nonexistent — yet the main repo's build workflow references it. So the Electron
shell is **not in the open repository**.

This is the first hard fact and it shapes everything below: the desktop half of
N.E.K.O cannot be read as source. It could only be read as a shipped artifact.

### 1.2 What the shell actually is, and how it was read

The shipped artifact `N.E.K.O.exe` is **213.4 MB** and was verified to be an
**NSIS installer**, not a runnable Electron app:

- Full-file scan finds the `NSIS` marker at byte offset 205546388.
- The same exe contains three separate `app.asar` occurrences (offsets 4202794,
  185907704, 222515245).
- The PE section table is named `LZMADEC` — NSIS's LZMA-compressed payload format.
- Launching it with Electron CLI switches produces
  `N.E.K.O.exe: bad option: --no-sandbox`, which is what an NSIS stub does with
  arguments it does not understand. An Electron runtime would have accepted them.

The `app.asar` inside it **is** readable. It was parsed (16-byte header, 4×uint32,
JSON header block, base offset `16 + header_size`, offsets relative to that base)
and **138 Electron source files were extracted** to
`benchmarks/raw/asar-src/`. Listing at `benchmarks/raw/evidence/asar-filelist.txt`.

**Consequence:** the shell is partially auditable, but only as *shipped compiled
output*. Findings in section 3.3 are therefore graded on extracted-source
evidence, not on a repository with history, issues, or a build you can run.

---

## 2. Install and run result

### 2.1 The documented Windows path could not be followed

`docs/deployment/windows-exe.md` in the repo states: *"Install N.E.K.O. from the
Steam store."* There is no documented free/standalone Windows path. Per the
evaluation constraint "do not purchase anything", the Steam path was not taken.

### 2.2 What was ruled out, and how

Each of these was a real attempt, and each was eliminated with evidence rather
than assumption:

| Attempt | Result | Evidence |
|---|---|---|
| Run `N.E.K.O.exe` directly | `bad option: --no-sandbox` → NSIS stub | `nsis-direct-launch.txt` |
| Silent install `/S /D=<path>` | **rc=1, zero files produced** | `install_neko_silent.py` |
| Backend exe directly | No window, single process alive 70 s, zero ports, zero files | `backend-probe.txt` |
| Is the GUI subsystem available at all? | **Yes** — control experiment created a real visible Win32 window (`hwnd=6753350`, `IsWindowVisible=True`, screen 2880×1800) | `gui-subsystem-control.txt` |

The control experiment is the important one. It proves the blocker is *not* a
headless/sandbox limitation of this session. The blocker is that the only
distributable is an installer whose UI cannot be driven here, whose documented
distribution channel is a paid storefront.

So the honest statement is: **the Electron desktop shell was BLOCKED, and the
cause is packaging, not environment.**

### 2.3 What did run: the backend, standalone

The Python backend is a separate Nuitka-built executable,
`projectneko_server.exe`, shipped inside the same bundle. It runs headless.

It was launched, and its storage gate was satisfied through the product's own
documented contract (`benchmarks/raw/evidence/storage-setup-attempt.txt`):

```
POST /api/storage/location/restart
  {"selected_root": "<store>", "selection_source": "user_selected"}
-> 200 {"ok":true,"result":"restart_initiated","restart_mode":"migrate_after_shutdown",
        "migration":{"txid":"e5a94d9bf5e44b89ae6e747b033db7e3","status":"pending",...}}
```

That is the only path that works. Two other attempts that look equivalent are
not, and the difference is instructive:

- Setting `NEKO_STORAGE_SELECTED_ROOT` is read by `storage_roots.py:94` but does
  **not** clear the gate.
- `POST /api/storage/location/select` returns 200 `restart_required`, but a force
  kill after it leaves `root_state.last_migration_result` as
  `launcher_phase0_bootstrap` — the launcher overwrites the transition.
- `POST /exit` with header `X-Neko-Storage-Action: exit` returns 200
  `shutdown_initiated` but the process does not actually exit.
- Only `/restart` with the root in the **body** commits the migration, and the
  relaunched process comes up `ready` with 340 routes.

After the gate: `/health` → 200, `status: "ready"`, all four ports LISTENING,
340 routes live.

---

## 3. Capabilities verified in code

Graded against the shipped surface — a live route, or source reached from a
shipped entry point.

### 3.1 Voice — IMPLEMENTED

- 27 live routes under `/api/voice*`.
- Streaming TTS with per-sentence playback, the newest commit's own subject line
  (`按已播音频放字幕` — subtitles follow actually-played audio).
- ASR present, including a "local-only ASR worker" exercised against a "public
  session contract" (from `git grep` on the ASR module).
- VAD, barge-in and speaker arbitration all present as code paths.

**Honest caveat found in source:** there is **no acoustic echo cancellation**.
Barge-in echo handling is done with `difflib.SequenceMatcher` text similarity
between what was spoken and what was heard. That is a heuristic against a
transcript, not AEC. For a tutor this matters more than it does for a chat
avatar, because a tutor gets interrupted by its own TTS constantly and the user
is often mid-sentence when they start.

### 3.2 Memory, proactive behaviour, activity model — IMPLEMENTED

- 17 live memory routes. Five-tier memory (working / recent / facts / reflection /
  persona), hybrid BM25 + ONNX-cosine retrieval fused with RRF, JSON store with
  atomic writes.
- `main_logic/proactive_chat/` — **10293 lines**: source gating → generation →
  anti-repetition → cooldown.
- `main_logic/activity/` — **5269 lines**: a state machine over
  idle / focused_work / focused_video / gaming / away.
- Only one built-in tool is exposed to the agent: `recall_memory`
  (`GET /api/tools` → `{"YUI": ["recall_memory"]}`).

The proactive pipeline and the activity state machine are the most credible
parts of the codebase. 15.5k lines of state management is not scaffolding.

### 3.3 Desktop / avatar / self-window exclusion — MIXED, split across two halves

- 88 avatar/rendering routes. Live2D and VRM both supported (dual engine).
- Always-on-top transparent overlay: `setAlwaysOnTop(true, 'screen-saver')` in
  `src__avatar-tool-visual-overlay-service.js`.
- 138 Electron files extracted; `desktopCapturer` enumeration with
  `useSystemPicker: true`.

Self-window exclusion — the specific hard problem of "the avatar must not appear
in its own screenshot" — is fully implemented **in the Electron shell only**
(`src__main__screen-capture-ipc.js:1768-1905`):

1. record every currently-visible `BrowserWindow`;
2. hide them all, including the sender and the pet window;
3. wait for the compositor to commit (90 ms, 350 ms on Linux/Wayland);
4. `desktopCapturer.getSources({types:['window']})`;
5. restore in a `finally` via `restoreCapturedWindows` / deferred overlay restores.

That is a correct three-phase implementation with a real wait, which is more than
most projects manage.

**But in the Python backend, capture is naive**: a bare `pyautogui.screenshot()`,
no exclusion whatsoever.

So the honest reading is: **exclusion exists, and it lives in the half of the
product whose source is not open.** Adopting the shell means adopting that
implementation as an opaque binary blob, and any bug in it is unfixable without
upstream cooperation.

### 3.4 Screen / vision — WEAK, and structurally capped

- **Only 4 routes** for screen/vision, against 88 for avatar.
- `main_logic/activity/` exists but there is no VLM loop tied to it.
- Measured, not inferred: `GET /api/capture/health` → **503**
  `{"success":false,"available":false,"error":"no_renderer"}`.
- `GET /api/screenshot` and `GET /api/capture/screenshot` → **405 Method Not Allowed**.

`no_renderer` is the whole finding in one word: **the backend cannot take a
screenshot on its own.** Capture is delegated to the Electron renderer over IPC,
and with no renderer there is no capture. A headless, server-side, or
CLI-driven deployment of N.E.K.O has **no screen perception at all**.

### 3.5 Extensibility — IMPLEMENTED, and the strongest single feature

- 23 live plugin/agent routes.
- Plugin process isolation: `multiprocessing.Process` + four ZMQ channels
  (PUSH/PULL). Upstream messages are **MessagePack**, explicitly to avoid pickle
  deserialization RCE. Per-host tokens.
- Tool callbacks are registered over HTTP with a loopback-enforced
  `callback_url`.

### 3.6 Provider flexibility — WEAK

The abstraction is very thin: only `ChatOpenAI` and `ChatAnthropic` classes, with
per-provider differences collapsed into `extra_body` functions in
`config/providers.py`. Everything else — realtime, memory, proactive, activity —
assumes an OpenAI-shaped client. This is a pluggable *shape*, not pluggable
*providers*.

### 3.7 Study Companion / teaching — **NOT FOUND. Zero.**

Searched all 2850 `.py` files. Results, with false positives eliminated by reading
the matches:

| Term | Files | Verdict |
|---|---|---|
| `lesson_plan` | 0 | absent |
| `curriculum` | 0 | absent |
| `syllabus` | 0 | absent |
| `course_rag` | 0 | absent |
| `learner_model` | 0 | absent |
| `knowledge_point` | 0 | absent |
| `flashcard` | 0 | absent |
| `spaced_repetition` | 0 | absent |
| `socratic` | 0 | absent |
| `pedagog*` | 0 | absent |
| `homework` | 0 | absent |
| `exercise` | 146 | **false positive** — all English verb "to exercise" ("lets unit tests exercise the production path", `def exercise(root)`) |
| `quiz` | 4 | **false positive** — only the word inside prompt strings (`prompts_visit.py` etc.) |
| `textbook` | 2 | **false positive** — code comments using "textbook" as a metaphor ("reproduce the textbook scores exactly") |
| `chapter` | 36 | chapter of a *visit/conversation*, not of a course |

Route inventory corroborates it. Of 340 routes, keyword-matching study/teaching
returns 6, and every one is a false positive:

```
/api/characters/voice_design_preview   <- voice preview
/api/characters/voice_preview          <- voice preview
/api/memory/external_import/preview    <- import preview
/api/memory/review_config              <- memory review config
/api/seven-day-tutorial/state          <- ONBOARDING tutorial
/api/steam/workshop/upload-preview-image
```

The only "tutorial" in the product is the seven-day **onboarding** tutorial.
Measured: `GET /api/seven-day-tutorial/state` → 200
`{"ok":true,"storeVersion":1,"initialized":false,"revision":0,"state":null}`.

**Not experimental. Not abandoned. Not documentation-only. Absent.**

---

## 4. Capabilities verified in actual use

### 4.1 What was genuinely exercised

| Capability | Status | How |
|---|---|---|
| Backend cold start | **VERIFIED** | 3 independent runs: 20 s / 22 s / 26 s to `/health` 200 |
| Backend warm API latency | **VERIFIED** | 10 samples per endpoint, median/p90/min/max |
| Storage gate + migration | **VERIFIED** | via `/restart`, relaunch comes up `ready`, 340 routes |
| Route inventory | **VERIFIED** | 340 routes enumerated from the live app |
| Tool registration from an external service | **VERIFIED** | see 4.2 |
| Loopback enforcement on callbacks | **VERIFIED** | public host and cloud-metadata IP both rejected 422 |
| Backend CPU / RSS | **VERIFIED** | corrected FILETIME probe, idle and under load |
| Screenshot from backend | **VERIFIED NEGATIVE** | `no_renderer`, 405 on both screenshot routes |
| Desktop shell (avatar visible, always-on-top) | **BLOCKED** | NSIS installer, section 2.2 |
| Voice path end to end | **BLOCKED** | needs the shell |
| Barge-in in actual use | **BLOCKED** | needs the shell; and no AEC (§3.1) |
| Proactive speech in actual use | **BLOCKED** | needs the shell for the avatar; backend pipeline exists but its trigger surface is renderer-bound |
| Study Companion in actual use | **NOT APPLICABLE** | nothing to use (§3.7) |
| 5–8 turn dialogue quality | **NOT DONE** | requires a configured LLM provider and the shell |

### 4.2 The decisive experiment: external Brain integration, no fork

This was the single most important question in the evaluation — *can the existing
LiveTutor Brain attach as a plugin/adapter/service without forking N.E.K.O?* — so
it was tested directly rather than answered by reading code.

A `ThreadingHTTPServer` on `127.0.0.1:48977`, shape-compatible with the LiveTutor
Brain (stdlib HTTP server, JSON in/out), registered two tools through N.E.K.O's
own public API.

Schema note: registration is **per-tool and flat** — `{name, description,
parameters, callback_url, source}`. A batched `{tools: [...]}` payload is
rejected 422 with `missing: body.name` and `missing: body.callback_url`.

Results:

```
register livetutor_read_screen    -> 200 {"ok":true,"registered":"livetutor_read_screen",
                                       "affected_roles":["YUI"],"failed_roles":[]}
register livetutor_ground_claim   -> 200 {"ok":true,"registered":"livetutor_ground_claim",
                                       "affected_roles":["YUI"],"failed_roles":[]}

GET /api/tools ->
  YUI: ['recall_memory',
        'livetutor_read_screen',
        'livetutor_ground_claim']
       livetutor_read_screen   source=livetutor_brain
                              callback_url=http://127.0.0.1:48977/livetutor-brain/read_screen
                              is_remote=true
       livetutor_ground_claim  source=livetutor_brain  is_remote=true

unregister livetutor_read_screen -> 200 {"ok":true,"removed":true,...}
unregister livetutor_ground_claim-> 200 {"ok":true,"removed":true,...}
final tool list                   -> back to ['recall_memory']
```

SSRF posture, tested rather than assumed:

```
http://example.com/hook                  -> 422 rejected
http://169.254.169.254/latest/meta-data/ -> 422 rejected
http://127.0.0.1:48977/ok                -> 200 ACCEPTED
```

The rejection message is in the product's own words: `callback_url host 必须…`
(host must be …).

**What this proves:**

1. An external brain service attaches over plain HTTP with **no N.E.K.O source
   change**. The extension point is real and it is public API, not a private hook.
2. Custom tools are attributed with `source` and `is_remote`, and are injected
   into the agent role's tool set (`affected_roles: ["YUI"]`). They coexist with
   the built-in `recall_memory`.
3. Lifecycle is clean: register → use → unregister, with the tool list returning
   exactly to baseline. A LiveTutor Brain could attach and detach at runtime.
4. Loopback enforcement is genuinely enforced, including against the cloud
   metadata address. Security posture is better than most projects at this scale.

**What this does not prove:** the callback was verified reachable and the
registration verified visible, but **the product-driven invocation path was not
exercised**. N.E.K.O only calls a registered tool from inside its own LLM turn,
which needs a configured provider *and* the shell. So: *attachability is proven;
invocation-under-real-turn is not.*

### 4.3 The one machine limitation worth recording

The frozen baseline notes this machine's loopback is silent
(`peak_rms 1e-05`–`2e-05`). That means audio playback and barge-in **cannot be
machine-verified on this host at all** — the existing LiveTutor baseline has the
same blind spot. Any audio claim, for either project, is currently unverifiable
here. Probe playback is opt-in only and was not used.

---

## 5. Study Companion analysis

The requirement was to distinguish implemented / experimental / abandoned /
documentation-only, using real code and real history. The answer is simpler than
the four-way split anticipated.

**Implemented: nothing. Experimental: nothing. Abandoned: nothing.
Documentation-only: nothing. There is no Study Companion feature in N.E.K.O at
any maturity stage.**

Supporting detail:

- The only user-facing "tutorial" concept is a seven-day onboarding tour
  (`/api/seven-day-tutorial/*`), state confirmed `initialized: false, state: null`
  on a fresh store. Onboarding is not teaching.
- The activity state machine (`idle / focused_work / focused_video / gaming /
  away`) is *attention* classification, not a learner model. It knows what you are
  doing; it does not know what you know, what you have been taught, or what you
  are next supposed to learn.
- Proactive chat generates conversation. There is no pedagogical gate, no
  curriculum position, no completion signal, no spaced repetition anywhere.
- `recall_memory` is the only agent tool. A tutor needs at minimum: content
  retrieval over course material, learner-state tracking, and exercise generation.
  None exist.

**Consequence, stated plainly:** adopting N.E.K.O as the base means the entire
teaching layer — the thing LiveTutor exists to build — must be written from
scratch on top of it. LiveTutor already has a working version of that layer with
546 passing tests. This is not "N.E.K.O is missing a feature". It is
"N.E.K.O and LiveTutor are not the same category of product".

---

## 6. Architecture and plugin analysis

### 6.1 Topology (verified from `core_config.txt` and live ports)

```
Electron shell  (source NOT open — N.E.K.O.-PC is 404; only shipped app.asar readable)
  └─ desktopCapturer ──IPC──┐
                            ▼
projectneko_server.exe  (Python 3.11, Nuitka standalone)   :48911  MAIN
  ├── memory server                                          :48912  MEMORY
  ├── tool server                                            :48915  TOOL
  └── user plugin server                                     :48916  USER_PLUGIN
        └── multiprocessing.Process + ZMQ (PUSH/PULL) + MessagePack
```

All four ports confirmed LISTENING. Single process, RSS 580 MB.

### 6.2 The good parts, and they are genuinely good

- **Plugin process isolation with a non-RCE serialization boundary.** MessagePack
  instead of pickle for cross-process messages, ZMQ for transport, per-host
  tokens. This is a considered design, and it is more than the LiveTutor baseline
  has.
- **Loopback-enforced tool callbacks.** Proved by test, including the metadata-IP
  case.
- **Clear service separation**: UI / agent brain / memory / tools are separate
  processes with HTTP boundaries. The boundary LiveTutor's Brain already speaks.
- **Source discriminator on tools** (`builtin` vs `livetutor_brain`), which makes
  coexistence with an external brain a supported configuration rather than a hack.
- **Electron self-window exclusion** (§3.3) — the most valuable single piece of
  code found in the whole evaluation, and it is sitting in the closed half.

### 6.3 The structural problems

1. **The critical half is closed.** Avatar, window enumeration, capture,
   always-on-top, overlay, and the entire self-exclusion implementation live in
   `app.asar` with no public source. Unfixable locally.
2. **Capture is renderer-bound.** `no_renderer` means screen perception is not a
   service, it is a side effect of a GUI being open. That is architecturally
   incompatible with a headless/server deployment, and it is also incompatible
   with *testing* screen perception without a GUI.
3. **No AEC.** For a chat avatar this is a tuning problem. For a tutor that talks
   over itself while the learner is mid-sentence, this is a correctness problem.
4. **Provider abstraction is two classes wide.** Anything not OpenAI-shaped is a
   patch.
5. **No teaching surface whatsoever** (§5).
6. **The extension point is tools, not the brain.** This is the subtle one.
   N.E.K.O's agent loop is in-process and owns the turn. An external service can
   supply *tools*, but not the reasoning loop, not turn policy, not streaming
   response composition, not the teaching decision. LiveTutor Brain is a brain,
   not a tool.

**Verdict on the central question:** Brain can attach *without forking* — proven.
But it would attach as a subordinate tool provider to N.E.K.O's agent, which is
the reverse of the intended ownership. To make Brain the brain rather than the
toolbox, you must replace N.E.K.O's agent loop — i.e. fork. The no-fork property
holds only for the tool layer, and the tool layer is not where LiveTutor's value
is.

---

## 7. Measured latency and resource samples

All figures from this machine, 2026-10-08. Raw: `benchmarks/raw/evidence/`.

### 7.1 Startup

| Metric | Value |
|---|---|
| Cold start to `/health` 200 | **20 s / 22 s / 26 s** (3 runs) |
| Warm API median | 7–16 ms |
| Process count | 1 (`projectneko_server.exe`) |

### 7.2 API latency, 10 samples warm

| Endpoint | Median | p90 | Min | Max | Code |
|---|---|---|---|---|---|
| `/health` | 14.8 ms | 15.6 ms | 2.2 | 28.3 | 200 |
| `/api/system/status` | 28.7 ms | 30.8 ms | 8.2 | 32.0 | 200 |
| `/api/config/preferences` | 9.3 ms | 26.6 ms | 2.8 | 27.3 | 200 |
| `/api/characters` | 14.5 ms | 27.3 ms | 3.0 | 27.8 | 200 |
| `/api/memory/recent_file` | 15.3 ms | 27.7 ms | 2.6 | 27.9 | 422 |
| `/api/activity_signal` | 15.6 ms | 27.7 ms | 3.1 | 27.8 | 405 |

The 7–32 ms spread within a single endpoint is scheduler noise, not real
variance. Warm request handling is a non-issue for either project.

### 7.3 CPU and RAM (corrected probe)

An earlier reading of `cpu=13435848058.8s` was a FILETIME field error and is
**discarded**. Corrected probe (`cpu-ram.txt`):

| Metric | Value |
|---|---|
| RSS | **580 MB** (stable; 582 MB after load) |
| Peak RSS | **732 MB** |
| Idle CPU | **0.23 % of one core** (0.05 s over 20 s) |
| Load CPU | 35.1 % of one core at 51.7 rps |
| CPU per request | **6.8 ms** |

Idle cost is negligible. 580 MB backend-only is comparable to the LiveTutor
baseline's footprint; the full product with the Electron shell would be
materially higher, and **that total was never measured** because the shell was
BLOCKED.

### 7.4 What could not be measured

Startup-to-first-meaningful-response, first TTS, interrupt-stop latency,
screenshot latency: all require the shell. Not estimated, not guessed.

---

## 8. Comparison with the frozen LiveTutor baseline

Baseline: LiveTutor @ `pre-base-reevaluation-2026-10-07`, 546 tests passing.
Read-only; no baseline file was modified.

| # | Dimension | LiveTutor (frozen) | N.E.K.O | Winner | Confidence |
|---|---|---|---|---|---|
| 1 | Windows shell, buildable from source | **Yes** — OLV patched, `patches/` keeps deltas reviewable | **No** — shell repo 404; only NSIS binary; official path is Steam | **LiveTutor** | High |
| 2 | Live2D avatar | Yes (via OLV) | Yes (dual engine, 88 routes) | Tie | High |
| 3 | Voice in/out | Yes | Yes, streaming + per-sentence | N.E.K.O | High |
| 4 | Barge-in / echo handling | VAD in OLV; loopback silent so unverified | VAD + barge-in + arbitration present, **but no AEC** (SequenceMatcher heuristic) | **LiveTutor** (unproven vs unproven-with-known-defect) | Medium |
| 5 | Screen awareness | **Hybrid OCR + VLM**, `ocr_ms` 489 median, per-turn pipeline | 4 routes; VLM path not wired to activity; **capture needs renderer** | **LiveTutor** | High |
| 6 | Source/window binding | Screen capture with scale fix; no per-window binding | `desktopCapturer` + system picker in shell; **source closed**; Python side is bare `pyautogui` | **LiveTutor** | High |
| 7 | Proactive behaviour | Out of scope (declared) | **10293-line pipeline + 5269-line activity state machine** | **N.E.K.O** | High |
| 8 | Memory | Not built | 5-tier, BM25+ONNX+RRF, atomic writes | **N.E.K.O** | High |
| 9 | Tutor capability | **546 tests**, grounding guard, structured context, latency rig | **Zero** | **LiveTutor** | High |
| 10 | Study Companion | Partial (out of scope: learner model, course RAG, pyBKT) | **Zero, and zero groundwork** | **LiveTutor** | High |
| 11 | Plugin architecture | None — monolith + Brain | **Process isolation, ZMQ, MessagePack, tokens, loopback SSRF guard** | **N.E.K.O** | High |
| 12 | Provider flexibility | DeepSeek-specific tuning path (`v0.2-deepseek-strong-tutor.md`) | Two classes + `extra_body` | **LiveTutor** | Medium |
| 13 | Latency (end to end) | Submit→backend 335 ms, →DOM 3740 ms, →TTS 2215 ms, →final 15215 ms | Backend warm 7–32 ms only; **shell path unmeasured** | **Incomparable** | — |
| 14 | CPU / RAM | Not isolated (single process with shell) | Backend 580 MB, idle 0.23 % core, peak 732 MB; **shell total unmeasured** | **Incomparable** | — |
| 15 | Stability | 546 tests green, known limits documented | Backend ran clean for the session; **shell untested**; ~20–26 s cold start each launch | Incomparable | — |
| 16 | Amount still to build | Teaching layer gaps, declared | **Everything teaching**, plus shell unavailability | **LiveTutor** | High |

**Tally: LiveTutor wins 8, N.E.K.O wins 4, 4 incomparable or unverified.**

Note on row 16, which is the one that actually decides this: the comparison is
not symmetric. N.E.K.O's wins are all in subsystems LiveTutor declared out of
scope and could adopt piecemeal. LiveTutor's wins are in the layer that *is* the
product. Adopting N.E.K.O means paying for the teaching layer in full.

### 8.1 One thing already banked

The v0.3 spike already adopted Skilly's DOM digest as a grounding second path
(`spikes/v0.3-structured-context/web_context.py`,
`docs/v0.3-structured-screen-context.md`). That idea is **not** a new discovery
from this evaluation — it is an existing LiveTutor asset. Whatever else is
decided, that work is not wasted.

---

## 9. Targeted review of the alternatives

| Project | Verified | Platform | Relevance to LiveTutor |
|---|---|---|---|
| **Open-LLM-VTuber** | Real, active, the basis of the current LiveTutor shell | Windows/Web | **Keep.** Not a competitor to evaluate — it is already the current base and it works. |
| **Skilly** | Real; DOM-digest grounding; declarative `SKILL.md` teaching skills (`format_version`, curriculum stages, completion signals, UI vocabulary) | — | **Highest-value borrow after N.E.K.O.** The declarative-skill idea is a way to make teaching content data, not code. Already partly adopted (§8.1). |
| **Clicky** | Real, 7691★; ScreenCaptureKit `excludingWindows` by bundle id | **macOS only** | Idea worth reading, **not portable.** Windows has no equivalent; N.E.K.O's hide-wait-capture-restore is the correct Windows pattern, and it is the better prior art. |
| **Mana** | Real | — | No mechanism that changes a decision here. |
| **DeepTutor** | Real | Web-first | Confirms the tutor-specific layer is where projects differ. Does not offer a Windows desktop substrate. |

Two patterns worth naming from this sweep:

1. **Nobody has solved Windows self-window exclusion properly.** The correct
   Windows primitive is `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` or UI
   Automation tree filtering. N.E.K.O hides all windows and waits for the
   compositor instead — correct, heavier, and closed-source. No candidate does
   better.
2. **The pointing/indicating interaction has been independently reinvented four or
   more times and never validated.** This was already recorded in the frozen
   baseline and this sweep found no new evidence against it. Building it is not
   a differentiator.

---

## 10. Existing coverage

Honest estimates. Denominator is "a working personal AI tutor on Windows", and
the three axes are weighted differently — that weighting is the whole point.

### 10.1 If you adopt N.E.K.O as the base

| Axis | Coverage | Reasoning |
|---|---|---|
| Infrastructure | **~65 %** | Avatar, voice, memory, proactive, plugin isolation all IMPLEMENTED. Deduct: shell source unavailable, capture renderer-bound, no AEC, provider abstraction 2 classes, 20–26 s cold start, 580 MB backend. Verified-blocked items also count against it — voice and capture are implemented but not verifiable in use. |
| Teaching | **0 %** | Zero. No curriculum, no learner model, no course RAG, no exercises, no spaced repetition, no pedagogical gating. Not experimental — absent. |
| UX / shell | **~35 %** | Built but sealed: 88 avatar routes, Live2D+VRM, always-on-top overlay, system picker, self-exclusion. None of it auditable or fixable locally. Cannot be installed without a paid storefront. |
| **Overall reusability** | **~30 %** | And the 30 % is the *easy* 30 %. |

**To ship a tutor on N.E.K.O, the teaching layer is 100 % of the remaining work.**

### 10.2 If you stay on the current LiveTutor base

| Axis | Coverage | Reasoning |
|---|---|---|
| Infrastructure | **~55 %** | Perception + grounding + latency rig are real and tested (546 tests). Weaknesses: no proactive engine, no memory service, OLV is patched rather than owned. |
| Teaching | **~45 %** | Grounded tutor with a grounding guard, structured context, tuned model selection. Missing: learner model, course RAG, pyBKT, adaptive routing. This is the part that exists and the part that matters. |
| UX / shell | **~70 %** | OLV shell is source-available, patched, reviewable deltas, working on this machine today. |
| **Overall reusability** | **~55–60 %** | Of which the teaching half is the irreplaceable half. |

### 10.3 The comparison that matters

Not 30 % vs 55 %. The real question is whether 30 % is a *head start* or a
*detour*. It is a detour: the missing 70 % under N.E.K.O is the teaching layer,
and the teaching layer is the part that must be built regardless. Adopting
N.E.K.O does not reduce teaching work by 30 %; it reduces teaching work by 0 %
and adds a closed shell, a missing capture path, and no AEC.

**Both roads require writing the teaching layer. One of them requires it on top
of a substrate you can read, build, test, and fix.**

---

## 11. STOP BUILDING

Things to actively stop, with the reason each one is now settled:

1. **Stop rebuilding proactive conversation.** 10293 lines of pipeline (source
   gating, anti-repetition, cooldown) plus a 5269-line activity state machine,
   already written and maintained by someone else, already imported.
2. **Stop rebuilding multi-process plugin isolation.** ZMQ + MessagePack +
   per-host tokens, already done, already SSRF-guarded, verified by test. This is
   the single most expensive thing to get right and it is already right.
3. **Stop rebuilding avatar/voice plumbing.** Live2D + VRM, streaming TTS with
   subtitle sync, ASR, VAD, barge-in, arbitration. 27 voice routes, 88 avatar
   routes.
4. **Stop rebuilding the memory service.** Five-tier with hybrid BM25 + ONNX +
   RRF and atomic writes.
5. **Stop rebuilding Live2D rendering, lip-sync, and expression mapping inside
   LiveTutor.** Freeze OLV to that role.
6. **Stop pursuing the pointing/indicating interaction.** Independently
   reinvented 4+ times, never validated, and the evidence in hand says it is
   zero-benefit or harmful.
7. **Stop treating "we might need a different base someday" as work.** It is now
   a decided question with evidence.

---

## 12. STILL WORTH BUILDING

1. **The teaching layer. Entirely.** Curriculum, learner model, course RAG,
   exercise generation, spaced repetition, pedagogical gating. Zero of this
   exists anywhere in N.E.K.O, and it is the product.
2. **Grounding as a hard invariant.** The existing grounding guard with its
   documented 9.5 % false-positive rate is a genuine asset. Tighten it; do not
   replace it.
3. **Progressive structured screen context.** The DOM-digest path is already
   adopted in the v0.3 spike. Finish it. It is the only route to reliable
   grounding that does not depend on OCR reading a 110 px font correctly.
4. **Latency work on the real path.** Submit→final reply is 15215 ms against a
   2215 ms first-TTS. That gap is the actual product problem, and it lives in the
   existing base, not in a new one.
5. **Fix the known measurement gaps.** RapidOCR degradation at large font sizes;
   the grounding guard false positives; the silent-loopback blind spot that makes
   audio unverifiable on this host.
6. **Declarative teaching content, à la Skilly's `SKILL.md`.** Make a unit of
   teaching a versioned data file with stages and completion signals rather than a
   module. This is the highest-leverage idea in the whole sweep.
7. **Defer the decision on Windows self-window exclusion** until something
   actually needs it — and when that day comes, use
   `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` and do not adopt a
   hide-everything approach.
8. **Borrow N.E.K.O's four specific implementations**, by reading them, not by
   adopting the shell: the three-phase self-window exclusion
   (`asar-src/src__main__screen-capture-ipc.js:1768-1905`), the plugin
   MessagePack-over-ZMQ isolation, the loopback-enforced tool registration, and
   the proactive pipeline's shape.

---

## 13. Final architecture recommendation

### Recommendation: **A — stay on the current LiveTutor base.**

Not because N.E.K.O is bad. It is a good project, well-structured in the places
that matter, and it was built by people who solved problems this evaluation did
not need to solve. The recommendation is about **what LiveTutor is**.

**Why not B (N.E.K.O as the base):**

- The teaching layer — the entire product — is 0 % implemented. LiveTutor's is
  ~45 % implemented and test-covered.
- The desktop shell cannot be built, audited, or fixed from source. `N.E.K.O.-PC`
  is 404. The only distributable is an NSIS installer whose documented channel is
  Steam.
- Screen perception is renderer-bound (`no_renderer`), so headless operation and
  GUI-free testing of the most important sense are both impossible.
- Barge-in has no acoustic echo cancellation, and a tutor interrupts itself
  constantly.
- Adopting it does not reduce teaching work. It relocates it onto a worse
  substrate.

**Why not C (hybrid):** the honest hybrid is **"OLV for rendering, N.E.K.O's
patterns for subsystems, LiveTutor Brain for teaching"** — and that is not really
a base decision, it is a borrowing decision. It is already what section 12.8
recommends, and it costs nothing to adopt because it involves no migration. It is
worth doing precisely *because* the answer is A.

### The frozen role of OLV

**OLV is retained, and frozen to: Live2D/VRM rendering, audio I/O, and
expression/lip-sync mapping.** No new perception logic, no new proactive logic,
no brain logic goes into OLV. Its `patches/` stay reviewable. This is the
decision the whole evaluation was built to inform.

### The shape of the system now

```
OLV shell  ──►  LiveTutor Brain  ──►  teaching layer (the product)
   │                  │
   │                  ├── curriculum / learner model / course RAG      [TO BUILD]
   │                  ├── grounding guard (tighten, do not replace)   [EXISTS]
   │                  └── structured screen context                   [v0.3 spike]
   └── rendering + audio I/O only                       [FROZEN HERE]
```

### What would change this recommendation

Stated in advance, so the decision can be revisited on evidence rather than
sentiment:

- N.E.K.O opens the shell source **and** moves capture out of the renderer into a
  service → reconsider B.
- N.E.K.O ships any teaching-layer work at all → re-run section 5 first; that
  single fact flips the comparison.
- A third party ships a Windows tutor substrate with `WDA_EXCLUDEFROMCAPTURE`
  done properly → evaluate it against section 8 rather than starting over.

### Scope of this task

No migration was started. No `LiveTutor-Next` was created. The recommendation
stops here, at A.

---

## Appendix — evidence index

| File | What it proves |
|---|---|
| `evidence/measurements.txt` | Startup, latency, 340 routes, capture 503/405, tools, ports |
| `evidence/brain-integration.txt` | External Brain registers tools, visible, loopback-enforced, clean removal |
| `evidence/cpu-ram.txt` | Corrected CPU/RSS: 580 MB, idle 0.23 % core, 6.8 ms/req |
| `evidence/asar-filelist.txt` | 138 files extracted from shipped `app.asar` |
| `evidence/exe-packer-analysis.txt` | 213.4 MB exe is an NSIS installer (`NSIS` marker, `LZMADEC` section) |
| `evidence/gui-subsystem-control.txt` | Control experiment: GUI subsystem works, so the blocker is packaging |
| `evidence/nsis-direct-launch.txt` | `bad option: --no-sandbox` → stub, not Electron runtime |
| `evidence/storage-setup-attempt.txt` | `/restart` is the only path that commits storage migration |
| `evidence/backend-probe.txt` | Backend standalone launch behaviour |
| `evidence/backend-startup.log` | Cold-start sequence |
| `asar-src/` | 138 extracted Electron sources (the only view of the closed shell) |

Scripts that produced them are in `scripts/`: `measure_neko.py`,
`brain_integration_probe.py`, `cpu_probe.py`, `neko_restart_proper.py`,
`diag_neko_packer.py`, `control_gui_probe.py`, and the rest of the diagnosis chain.
