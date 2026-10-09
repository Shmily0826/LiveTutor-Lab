# Real Strong Tutor in the shipped Study UI — browser acceptance, 2026-10-09

## Result

`PASS_UNIFIED_OCR_STUDY_UI_REAL_MODEL_LOOP` at **2026-10-09T07:02:26Z**. The original Study
Companion page, served from the extracted static bundle, drove a complete tutoring conversation on a
**live model**: synthetic browser pixels → RapidOCR → teaching explanation → two follow-ups → targeted
practice question → learner answer → grading → session summary → page reload → summary of the same
persisted session.

- Correlation `b1b59244-caa7-494e-a41a-f7e9b4ba5075`, session `study-a9ef0564061347d287c14971ed9442bb`.
- Evidence: [unified acceptance](../benchmarks/raw/evidence/neko-study-unified-b1b59244-caa7-494e-a41a-f7e9b4ba5075.json),
  [plugin proof with every live call](../benchmarks/raw/evidence/neko-study-plugin-ui-20261009T070226Z.json),
  [browser pixels](../benchmarks/raw/evidence/neko-study-browser-pixels-b1b59244-caa7-494e-a41a-f7e9b4ba5075.json),
  [final screenshot after reload](../benchmarks/raw/evidence/neko-study-ocr-ui-final-b1b59244-caa7-494e-a41a-f7e9b4ba5075.png).
- 10 live calls: 14,372 input / 2,587 output tokens, slowest call 4,158 ms.
- Read-only SQLite reopen after shutdown: `PASS_REOPENED_TEMP_SQLITE`, integrity `ok`, 5 interactions,
  each visible explanation matched its persisted row exactly.
- Guard counters for this run: provider connects to one HTTPS host 33, blocked non-provider connect 1,
  blocked audio 1, blocked provider imports 2, host-service refusals 0, SQLite opens 5 (all inside the
  ignored temp tree), downstream provider/socket/audio/WebSocket/external-fetch calls 0, page errors 0.
- Plugin fingerprint unchanged: `4825aaf2195f8b33a581f6e7de08efd7bce04e0b47cd4c776b15ab340c84cbeb`.

This is still **not** the packaged N.E.K.O host. It is the genuine extracted plugin, its genuine
lifecycle, and the shipped UI, wired to a live provider inside the isolated fixture.

## The lifecycle was restored, not bypassed

The previous round injected `TutorLLMAgent` because `startup()` aborted. That is now fixed, and
`plugin.startup()` returns `Ok` with `status: ready` — the agent and the knowledge tracker come from the
lifecycle itself (`lifecycle.agent_from_startup: true`, `knowledge_tracker_from_startup: true`).
Two host dependencies were standing in the way, and both were real findings:

1. `startup()` first calls `self.config.dump()` → `profile_effective()` → `ctx.get_own_config`. The
   isolated context refused every `get_*`. It now serves the plugin's **own shipped `plugin.toml`**
   (`_own_plugin_config()` in `scripts/neko_study_plugin_methods_fixture.py`), with the host-side
   backends still switched off (`plugin.store`, `plugin.database`, `plugin_state`, `auto_start`).
   That single seam is what delivered the real teaching config, including `[study] language = "zh-CN"`
   and `llm.llm_call_timeout_seconds = 120`.
2. `_refresh_dependency_status()` probes `importlib.util.find_spec("dxcam")`. The fail-closed import
   guard *raised* there instead of reporting absence, aborting startup. The real-mode runtime now
   answers that probe as "absent" — which is the truthful state of this environment and still blocks
   the import itself (`allow_dependency_probes`, recorded as
   `capture_dependency_probes_answered_absent: ["dxcam"]`).

Audio/awareness posture came out of the shipped config rather than being invented: `awareness.enabled`
is `false`, `communication.enabled` is `true` with `silent_mode` `true`, so no `StudyEventBus` is built
(`event_bus_present: false`) and nothing in this run could reach a speech or audio sink. The browser
page-side gates (AudioContext, speechSynthesis, media.play, microphone, WebSocket, external fetch) were
still stimulated and blocked before the first action and again after reload.

The direct-`TutorLLMAgent` path is kept only as a labelled fallback: if `startup()` ever fails to
produce an agent, the run records `lifecycle.fallback` with the current refusal counters instead of
silently pretending the lifecycle ran.

## Two UX defects actually fixed

Both came from the previous round's measurements, and both are now asserted in the acceptance gate.

- **Repeated mode banner.** `concept_explain()` prepended `教学模式已开启。` to *every* teaching reply.
  It is now emitted only on the turn that actually switched mode, using the `mode_switch` flag the
  explain entry already computed. Measured in this run: `ui_ux_checks.mode_banner_replies: 0` across
  three live explanations, while the pure-switch reply path is untouched.
- **Language inconsistency.** The session summaries came back in English while everything else was
  Chinese. Root cause was twofold: the fixture served no config (so `language` fell back), and the
  structured prompt builders (summarize / question / evaluate / track) only carried `language` as a
  *data field* inside `context_json` with no output directive. The config now arrives through the real
  lifecycle, and `_build_structured_messages` adds an explicit
  “Write every natural-language field in {language}.” line. Measured:
  `explanations_have_cjk`, `summaries_have_cjk`, `evaluation_feedback_has_cjk` all `true`; the
  reloaded session summary is Chinese prose (`## 本次学习总结 …`).

Source change: 3 files, +8/−1 lines, in
[patches/neko-study-2026-10-09-ui/ui-real-tutor.patch](../patches/neko-study-2026-10-09-ui/ui-real-tutor.patch)
with pre-images (`prompt_templates.py` and `llm_prompts.py` pre-images are byte-verified against the
v02 overlay snapshot; `tutor_llm_agent_concept_explain.py` has no pristine pre-image in this repo, so
its `_pre/` mirror is an inversion of this round's edit — stated in that README). Both extracted copies
(`resources/bin/plugins/...` and `resources/bin/plugin/plugins/...`) were kept byte-identical.

## What the live tutor said

OCR (4,191 ms, one capture) returned `Example 2: u-substitution / Let u =x^2 / Then du = 2x dx / …` from
real browser pixels, and the visible input equalled that text.

1. First explanation (Chinese, from the pixels): derived `du = 2x dx → x dx = (1/2) du`, explained why the
   inner function is the one to pick, and tied it to "被积函数里出现了内层导数的常数倍".
2. Follow-up “为什么例题2有1/2？”: answered by naming the two lines it came from and stating the
   relationship is 1:2, not 1:1 — i.e. it used the on-screen material, not a generic recital.
3. Follow-up “为什么要令 u=x²？”: framed as the *choice rule* for substitution, walked the composite
   structure `exp(x²)`, and did not repeat answer 2.
4. Targeted question from the practice scope: “在换元积分法中，设 u = x^2，则 du 等于多少？”
5. Learner answer `u=x^2, du=2x dx, so the integral is (1/2)e^(x^2)+C.` → verdict **correct / 100** with
   specific feedback, persisted as interaction row 6; topic mastery **0.0 → 0.5937**.
6. After reload the page summarised the **same** session id again (second `study_summarize_session`).

The previous round's separate method-level run had already shown the grader rejecting a wrong answer
(`wrong / 0`, misconception) and marking the model's own reference answer only `partial / 75`, so
`correct / 100` here reflects a genuinely correct submission, not a lenient rubric.

## Measured latency in the browser path

| UI action | live calls | per-call ms | input / output tokens |
| --- | --- | --- | --- |
| explain #1 (OCR material) | 2 | 995 + 2,145 | 435/66, 662/263 |
| explain #2 (follow-up) | 2 | 1,208 + 3,082 | 764/91, 1,444/406 |
| explain #3 (follow-up) | 2 | 1,120 + 4,158 | 829/82, 2,091/546 |
| targeted question | 1 | 1,685 | 2,029/222 |
| grade answer | 1 | 2,338 | 1,506/240 |
| session summary | 1 | 2,063 | 2,306/307 |
| summary after reload | 1 | 2,302 | 2,306/364 |

Plus one OCR at 4,191 ms. The dominant avoidable cost is still the **semantic-routing call in front of
every explanation** (~1.0–1.2 s each, 3 of 10 calls here): it sees only the current text, carries no
history, and sits on the critical path. The plugin path is request/response with no streaming, so a
4–5 s answer leaves the learner staring at a disabled button; the UI does disable controls and show
progress, so this is a latency complaint, not a dead page.

## Remaining defects, in priority order

1. **Session summary ignores the graded answer.** Both summaries described the session as having no
   recorded response, although row 6 (`answer_evaluate`) exists and the answer marker did not appear in
   the 8,816-character summarize prompt (`carried: false`). Reproducing the context build offline (no
   provider call) with three interactions *does* put the answer into the prompt
   (`ANSWER_PRESENT_IN_PROMPT: True`) but already drops the oldest row there: the session boundary in
   `entry_tutor_context_support.py:693-716` is `min(recent_learning_events[*].at)`, and that event ring is
   bounded, so older interactions fall out of `session_history` as a session grows. My marker is a
   40-character digest, so this is a strong lead rather than a fully attributed root cause — the next
   agent should capture the summarize prompt body (or the projected rows) on the host side and fix the
   boundary to the session's own start timestamp.
2. **`question_generate` prompt is already ~2.0–2.3k input tokens** for a five-row session; expect growth
   pressure before long real sessions.
3. Banner and language are fixed for this path; nothing in this run exercises narration delivery — payload
   carries `solution_narration_*` / `general_narration_*` fields, and with `silent_mode` on and no event
   bus, nothing was scheduled or played.

## Still not host-verified

Packaged EXE, Native Realtime/ASR/TTS, microphone, real desktop capture (the OCR raster is a synthetic
browser screenshot fed through the normal `study_ocr_snapshot` entrypoint), the user's real knowledge
base and practice scope (the topic row is the fixture's synthetic `fixture_u_substitution`), and the real
learning database. The Mock path remains the accepted regression: after these shared-code changes it was
re-run and still reports `PASS_UNIFIED_OCR_STUDY_UI_LOOP`, `PASS_PLUGIN_METHOD_LOOP`, and 5/5 focused
context tests.

## Minimal next steps toward the formal N.E.K.O host

1. Fix the summarize session boundary (item 1 above) and re-run the same browser flow — no other
   teaching changes needed.
2. Take the routing call off the critical path (cache per session, or run it concurrently with the
   explanation). This is the single largest measured latency saving: ~1.0–1.2 s per explanation turn.
3. Let the host serve `ctx.get_own_config` (it already does — the fixture only stands in for it) and keep
   `study_set_mode` allowed in any UI proxy so the shipped mode control works.
4. Set `llm_vision_enabled` deliberately: `deepseek-flash` accepts images, so OCR-only grounding could be
   replaced or complemented by a vision turn; today it is `false`.
5. Add streaming or an explicit “正在思考” state before real learners use it.
6. Audio safety exit (mute verification) remains open, and is a prerequisite for starting the real host
   with TTS enabled.

## Reproduce

```powershell
# live model through the shipped UI (a few dozen tokens' worth of real calls)
node scripts/neko_study_ocr_ui_e2e.mjs --real-model
# same command on the deterministic double (offline, no provider)
node scripts/neko_study_ocr_ui_e2e.mjs
# method-level live loop (two cases, 30 calls)
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B scripts/neko_study_real_model_fixture.py
```

`--real-model` accepts `--key-file`, `--base-url`, `--model`, `--thinking host|enabled|disabled`.
No commit, push or reset was performed; the frozen EXE, system settings, the production learning
database and the user's browser were not touched.

## Source-control integrity review (checkpoint)

The running plugin lives in the gitignored `benchmarks/raw/neko-app/resources/bin/`, so the acceptance
results are only trustworthy if every locally edited file is recoverable from Git. Checked offline:

- 54 plugin files carry a post-install mtime; all of them are byte-identical to a tracked capture
  **except** the 3 edited this round (`llm_prompts.py`, `prompt_templates.py`,
  `tutor_llm_agent_concept_explain.py`), and those three are covered by
  `patches/neko-study-2026-10-09-ui/ui-real-tutor.patch`. Uncovered modified code files: **none**.
- Chain verification, not just file listing: applying `ui-real-tutor.patch` onto its `_pre/` mirrors
  reproduces the currently running files exactly (only `git apply`'s CRLF translation differs), and two
  of the three pre-images are byte-identical to the tracked v02 overlay snapshot, so they are true
  pre-images rather than reconstructions.
- Timeline check against the evidence: banner fix at 06:05Z → run `065018Z` reports
  `mode_banner_replies: 0` but `summaries_have_cjk: false`; language fix at 06:58Z → run `070226Z`
  reports all three CJK checks true. The newest accepted proof therefore corresponds to the source
  being committed, and the earlier proof is kept as the explicit "before" measurement.
- One pre-existing gap found in another agent's deliverable: `round2-teaching-context.patch` does not
  rebuild the tracked snapshot for `entry_tutor_context_support.py` (64 lines, the
  `_COMPUTER_SCIENCE_MARKERS`/asyncio additions made after that patch was generated). Nothing is lost —
  the authoritative bytes are in the tracked overlay payload and match the running file — but that patch
  should be read as an incomplete historical diff, and the overlay is the reliable capture.
- `resources/bin/plugins/...` (the copy actually imported and fingerprinted by every proof) and
  `resources/bin/plugin/plugins/...` differ in exactly one file, `__init__.py`, which predates this
  round; both copies are tracked in the overlay under the `bridge` and `live` roots respectively.
- Secret scan over everything committed: no `sk-`/`gsk_`/`ghp_`/bearer/quoted-key matches. Two tracked
  scripts reference the *path* of the user's local key file (never its contents), by existing project
  convention.
