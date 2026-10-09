# Real Strong Tutor run — Study Companion with a live model, 2026-10-09

## Result

The isolated Study Companion teaching loop now runs on a **real model** instead of the deterministic
double, and the accepted Mock evidence stays green.

- Provider: `https://api.deepseek.com/v1`, model `deepseek-flash`, provider type `openai_compatible`,
  transport `openai_compatible`, thinking dialect resolved from N.E.K.O's own
  `config/providers.py` table (`{"thinking": {"type": "disabled"}}`, i.e. the host default).
- 30 live model calls across two cases: 0 failed calls, **0 degraded entries**,
  37,580 input + 10,451 output tokens.
- Plugin fingerprint unchanged: `4825aaf2195f8b33a581f6e7de08efd7bce04e0b47cd4c776b15ab340c84cbeb`.
- Timestamped proof: [neko-study-plugin-real-20261009T053736Z.json](../benchmarks/raw/evidence/neko-study-plugin-real-20261009T053736Z.json)
  (run `2026-10-09T05:37:36Z`, OCR + math + asyncio). An earlier text-only pass is
  [neko-study-plugin-real-20261009T053427Z.json](../benchmarks/raw/evidence/neko-study-plugin-real-20261009T053427Z.json).
  Both are gitignored, like the rest of `benchmarks/raw/evidence`.

This is real model I/O with the genuine extracted plugin. It is **not** a packaged N.E.K.O host run:
the host lifecycle, TTS/audio, desktop capture and the shipped browser UI still use their previous
evidence levels (see “Still mock or isolated”).

## What was connected, and how thin the change is

Adopt → adapt → build, in that order:

1. **Adopted** the plugin's own production path end to end: `StudyCompanionPlugin` entries →
   `TutorLLMAgent` → `StudyModelGateway` → `build_operation_messages` → JSON corrector →
   normalizers → SQLite session/mastery. No teaching logic was written or modified.
2. **Adapted** only the two host seams the gateway already expects and that the offline fixture
   deliberately stubbed:
   - `utils.config_manager.get_config_manager().get_model_api_config("agent" | "vision")`
     now returns a real `{model, base_url, api_key, provider_type}` instead of `{}`
     (which is why every previous run reported `model_unavailable`).
   - `utils.llm_client.create_chat_llm_async(...)` is an OpenAI-compatible transport satisfying the
     existing contract (`ainvoke(messages)` → `content` + `response_metadata.token_usage/finish_reason`,
     `aclose()`). `max_retries` is refused unless it is `0`, so a run cannot silently re-spend.
     langchain/openai SDKs are not installed and stay blocked by the import guard.
   The agent is a genuine `TutorLLMAgent` instance built from the plugin's own `StudyConfig`.
3. **Guard change, one exception, fail-closed elsewhere**
   (`scripts/neko_study_plugin_methods_fixture.py`): network guards became address-aware. A provider
   hostname may be named; DNS answers for that name are remembered so its TLS connection is allowed.
   Every other destination, the loopback-only bind rule, audio/process/capture/provider-import guards,
   and the SQLite/temp-root confinement are unchanged. `NETWORK_ALLOW_HOSTS` is empty for the Mock and
   browser regressions, so they behave exactly as before — verified below.
4. **Mock retained**: `neko_study_plugin_methods_fixture.py`, `test_neko_study_context_fixture.py` and
   the browser reproducer are untouched in behaviour. The real harness is a new sibling
   (`scripts/neko_study_real_model_fixture.py`) that reuses the same guards, plugin, OCR pipeline and
   temp SQLite store, and never touches the production learning database.

Credential handling: the key is read from the local file the user left for this project
**before** the filesystem guard is installed, never printed, and the runner refuses to write evidence
if the secret appears anywhere in it. Recorded usage is token counts and latency only.

## Teaching results (actual behaviour, not self-report)

Math — synthetic screen pixels → real RapidOCR → teach (case `math_u_substitution_from_ocr`):
OCR returned `Example 2: u-substitution / Let u = x^2 / Then du = 2x dx / So x dx = (1/2) du / …`
(1 capture call, 2,370 ms, plugin OCR state matched). From those pixels the tutor derived
`du = 2x dx → x dx = du/2 → (1/2)∫e^u du = (1/2)e^(x²)+C`, verified the answer by differentiating,
and grounded substitution in the reverse chain rule with explicit boundaries
(“u′ must appear in the integrand, up to a constant”, “definite integrals need the limits changed too”).

Continuous follow-ups stayed on-context rather than repeating:
- “为什么会出现 1/2？直接把 e^(x²) 积分不行吗？” — explained where the factor comes from **and** that
  `∫e^(x²)dx` has no elementary antiderivative, which is why the extra `x` matters.
- “为什么令 u=x²，而不是 u=x 或 u=e^(x²)？” — tested both alternatives and showed why `u=x` does not
  reduce the integral; noted `u=e^(x²)` is in fact workable here (correct).
- Transfer probe `∫x²·e^(x²)dx` — answered that the substitution still legalises the integral but now
  needs integration by parts, produced `(1/2)(x²e^(x²) − e^(x²))+C` and re-verified by differentiation.

Python asyncio (case `python_asyncio`): correct serial reading of two `await bake(...)` calls
(`start bread → done bread → start cake → done cake`, 2+3≈5 s), then `asyncio.gather` →
`start bread → start cake → done bread → done cake`, max(2,3)≈3 s, and for `time.sleep` the real
distinction: in the serial version nothing observable changes, while inside `gather` it blocks the
thread and degrades to 5 s. The final turn contrasted cooperative yielding with OS threads/processes.

Question → grading → learning state:
- Weak answer on math (`du = x dx`, missing 1/2): verdict **wrong**, score **0**, `error_type: misconception`,
  feedback naming the exact differential mistake. The reference answer to the next generated question was
  graded **correct / 100**, and `u-substitution` mastery moved **0.0 → 0.2053**.
- Asyncio: the same misconception answer got **wrong / 0**; the model's own reference answer got
  **partial / 75** (`missing_step`: right outcome, unexplained await ordering and no 2+3=5 arithmetic),
  and mastery moved **0.0 → 0.1468**. The grader is discriminating rather than rubber-stamping.
- State reuse is real, not asserted: `explain_after_error` explicitly re-teaches the recorded error
  (“你上次错在…你把 `du = x dx` 写反了” / “你把顺序 await 误解成了并发”), 9 interactions persisted per
  session, and `study_summarize_session` produced Weak Points / Next Actions built from those rows.
- Prompt-level check: verbatim digests matched only intermittently (2 of the marker probes came back
  `carried: true`, both on the asyncio session). The plugin embeds history as structured rows
  (input text, verdict, weak points) rather than as whole previous replies, and the model alternates
  `²`/`^2`, so byte-equality is the wrong instrument. Grounding should be read off the answers above —
  e.g. the math re-teach names the learner's exact wrong line `du = x dx` and disproves it numerically —
  and a host-side run should record full prompt bodies if per-field attribution is needed.

## Measured performance

Per-turn entry latency 2.0–7.0 s; 20 turns total 78.9 s of plugin entry time for both cases.

| Stage | Calls | Mean | Max | Mean tokens (in/out) |
| --- | --- | --- | --- | --- |
| Semantic routing (`knowledge_semantic_route`) | 10 | 1,284 ms | 1,436 ms | 387 / 72 |
| Teaching / question / grading / summary | 20 | 3,033 ms | 5,573 ms | 1,686 / 487 |
| RapidOCR on synthetic pixels (once) | — | 2,370 ms | — | — |

Bottlenecks, in order:

1. **Every `study_explain_text` turn costs two serial model calls** — a context-free routing call
   (~1.2 s, 12.8 s = ~17% of model time here) then the explanation (~2.9 s). The router receives only
   the current text, so it cannot use history; it is also on the critical path of the follow-up.
2. **Prompt growth with history**: teaching/grading calls took 321–2,368 input tokens (mean 1,686) as
   the session history, current question, evaluation and knowledge parameters accumulated. Observed
   latency tracked output length more than payload size — the slowest call (5.6 s) produced 824 output
   tokens while a 2,368-token prompt answered in 3.7 s — so generation length, not transport, dominates.
3. **No streaming**: the plugin contract is request/response, so “first response latency” equals the
   full call. For a 4–5 s explanation the learner sees nothing until it completes.
4. OCR (2.4 s) is smaller than one teaching call but is paid once per snapshot; the browser-pixel path
   measured 4.5 s earlier, so real capture+OCR will exceed this synthetic number.

## Quality assessment

Strong enough to be worth wiring into the host: correct maths and concurrency semantics, self-verification
by differentiation, adaptation to follow-ups, honest and specific grading, and visible use of the recorded
error. Remaining defects, all observed in this run:

- **Language mixing.** The isolated context advertises `default_locale: en`, so `summarize_session`
  returned English section bodies in both cases even though every explanation was in Chinese, and the
  math `answer_evaluate` feedback came back in English while the asyncio feedback came back in Chinese
  (the model mirrored the answer text rather than the configured language). For a Chinese-language
  learner this needs `StudyConfig.language` (or the host locale) set deliberately.
- **“教学模式已开启。” prefixes explanation turns.** The mode-transition phrase is prepended to the
  teaching reply, which reads oddly on every turn after the first, especially in a long session.
- **Two calls per turn** is a UX/cost problem more than a correctness one.
- **Reference-answer grading is strict to the point of surprising**: `partial / 75` for a correct answer
  that omitted explanation. Defensible pedagogically, but the rubric should be explicit to the learner.
- Nothing here measures general OCR accuracy (single synthetic raster) or long-session context degradation
  (history limit is 12 rows).

## Still mock or isolated

- Deterministic double still backs the accepted browser/UI and method-loop evidence; those were re-run
  after the guard change and still pass: `PASS_PLUGIN_METHOD_LOOP`, 5/5 focused regressions, and
  `PASS_UNIFIED_OCR_STUDY_UI_LOOP` (session mastery `0.6189`, browser/adapter cleaned up, no page errors).
- Real desktop capture is not used; the OCR image is a synthetic raster fed through the normal
  `study_ocr_snapshot` entrypoint with the capture seam stubbed, as before.
- Targeted practice scope is still the fixture topic path, not the user's real knowledge base;
  the production learning database was not opened.
- No N.E.K.O host, no packaged EXE, no Native Realtime/TTS, no microphone and no audio output in this
  run.

**Superseded on the same day.** This round deliberately skipped the plugin's host `startup()` lifecycle
(it needs the config bus, and its failure path discarded the knowledge tracker), so the agent was built
directly. That workaround has since been removed: `startup()` now runs and returns `ready` in the
isolated runtime, the shipped UI is driven by the live model, and the two UX defects noted below
(repeated mode banner, English session summaries) are fixed and measured in
[neko-real-tutor-ui-2026-10-09.md](neko-real-tutor-ui-2026-10-09.md). The teaching-quality findings,
token counts and per-call latencies recorded here still stand.

## Next steps for the formal N.E.K.O host

1. Give the host `agent` model group a real config and let the plugin resolve it through the genuine
   `utils.config_manager` (this run proves the gateway works once that slot is filled; the ASSIST
   `deepseek` profile already sets all slots to `deepseek-flash`).
2. ~~Exercise the real `startup()` lifecycle~~ **done the same day** in the isolated runtime
   (`startup()` → `ready`, agent and tracker from the lifecycle) and the shipped UI was driven on the
   live model — see [neko-real-tutor-ui-2026-10-09.md](neko-real-tutor-ui-2026-10-09.md). Remaining risk
   is only the packaged host itself.
3. ~~Decide the language contract and suppress the repeated mode-transition prefix~~ **done the same
   day**: `plugin.toml` language now reaches `StudyConfig` through the lifecycle, the structured prompts
   carry an explicit output-language directive, and the mode banner appears only on the switch turn.
4. Cut the routing call off the critical path: cache the per-session route, or run it concurrently with
   the explanation, and consider 凝神/thinking mode for hard maths — this run deliberately measured the
   host default (`thinking: disabled`).
5. Add streaming, or at least an early “working…” UI state, since 3–5 s responses are normal.
6. Keep the audio exit question open: `study_explain_text` payloads carry narration fields, so before the
   real host runs with TTS enabled, the mute/sink safety from the earlier rounds still has to be settled.

## Reproduce

```powershell
# one cheap probe (16 output tokens), no plugin
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B scripts/neko_study_real_model_fixture.py --probe
# full real run: synthetic OCR + math + asyncio + two graded answers per case
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B scripts/neko_study_real_model_fixture.py
# offline Mock regressions (no network allowlist is set, so guards behave as before)
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B scripts/neko_study_plugin_methods_fixture.py
& '.tmp-uv-cache\neko-study-venv\Scripts\python.exe' -I -B scripts/test_neko_study_context_fixture.py
node scripts/neko_study_ocr_ui_e2e.mjs
```

`--key-file`, `--base-url`, `--model`, `--thinking host|enabled|disabled` and `--no-ocr` adjust the run.
Each successful run writes a new timestamped evidence file; no commit, push or reset was performed and no
production database, EXE, system setting or user browser was touched.
