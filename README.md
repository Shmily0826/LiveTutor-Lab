# LiveTutor-Lab

An evaluation lab for deciding whether LiveTutor should keep its current base or
adopt Project N.E.K.O. This repository holds reports and diagnostic scripts;
LiveTutor product development happens elsewhere.

## Current status (2026-10-08)

The recorded strategy keeps the LiveTutor base (option A) as the main line while
evaluating native N.E.K.O + Study Companion as a candidate. N.E.K.O is **not yet
accepted for daily realtime tutoring**. This round completed a sampled real Study
UI flow and repaired awareness startup in the local test environment. Region
capture, final proactive-message display and voice/interruption acceptance remain
unfinished. The frozen backend currently uses experimental compatibility hooks.

Start with the [latest handoff](docs/neko-handoff-2026-10-08-goal-wip.md), the
[current progress and evidence](docs/neko-goal-progress-2026-10-08.md), and the
[four-round acceptance report](docs/neko-acceptance-2026-10-08.md), especially its
R2 corrections and R4 final verdict. Earlier sections preserve the investigation
history; later corrections supersede their conclusions.

| Area | Recorded result | Remaining limit |
| --- | --- | --- |
| Native teaching plugin | Real UI: OCR → explanation → follow-up → question → wrong/correct feedback → persisted records | Fixed chain-rule material; broader teaching and grading reliability unverified |
| Semantic routing / knowledge guidance | Routing applied to the sampled follow-up; UI explanation took 3.700 s | Initial noisy OCR explanation did not apply graph guidance |
| Screen grounding | Explicit full-screen OCR recognized the fixture in 6.238 s | Region capture still returned `capture_busy`; foreground and overlay content matter |
| Normal character chat continuity | Awake UI test recalled 47 and computed 150 correctly | Short continuity check; sustained learning dialogue unverified |
| Background awareness | Settings, persistent ticks, subscriptions and first cold startup verified; bridge forwarding observed | Final character UI delivery unverified; awareness restored disabled |
| Voice / interruption | Microphone, ASR and TTS prerequisites identified | Configuration and real audio acceptance unfinished |

The latest handoff separates this round's live results from earlier reported
results. Changes are local and uncommitted; raw evidence remains ignored.

## Read before testing or developing

Read the product documentation and shipped tutorial before interpreting an
unexpected UI response as a missing capability. Check source revisions: the
candidate checkout, packaged application and marketplace plugin can differ.

### Important interaction rules

- **Recent conversation:** the blue handle above the compact chat input opens
  recent conversation history. A collapsed panel does not mean no reply arrived.
  The shipped Day 1 tutorial explicitly teaches this interaction.
- **Message delivery:** after expanding the panel, confirm pasted text is visible
  in the input and the send control appears before pressing Enter.
- **Cat form and sleep:** the product documents CAT1 (awake cat), CAT2 (dozing)
  and CAT3 (sleeping). Clicking the cat runs the existing return action and
  restores the normal character. Ordinary typing or mouse activity does not
  automatically restore the character. Packaged cat-form chat has a separate
  local meow-response implementation, so an awake CAT1 is not sufficient proof
  that normal LLM chat is active. Confirm the return has completed before tutoring.
- **History versus memory:** recent UI messages, durable character memory and
  Study Companion learning records are different surfaces. `/memory_browser`
  is a memory inspection entry, not the compact recent-chat panel. Persisted
  history is not automatically included in full in every model request.
- **Study input:** onboarding describes pasting text or explicitly clicking OCR,
  then choosing explain, generate question or evaluate answer. Opening Study does
  not by itself establish that continuous screen tutoring is running.
- **Screen sharing:** the Day 1 tutorial describes enabling screen sharing during
  a voice call. This is separate from Study OCR and background awareness.
- **Voice readiness:** a registered ASR provider does not establish that its
  resources are installed or the actual microphone/session works. Verify
  preparation, capture, recognition, playback and interruption separately.

### Reading map

Tracked lab reports:

1. [Latest handoff](docs/neko-handoff-2026-10-08-goal-wip.md): deployment, evidence, rollback and remaining work.
2. [Current progress](docs/neko-goal-progress-2026-10-08.md): sampled UI results and root-cause evidence.
3. [Earlier end-of-day handoff](docs/neko-handoff-2026-10-08-eod.md): baseline before this round.
4. [Four-round acceptance](docs/neko-acceptance-2026-10-08.md): measurements and corrected verdicts.
5. [Study Companion audit](docs/neko-study-companion-audit.md): source/release inventory and teaching contracts.
6. [Windows native reality check](docs/neko-windows-native-reality-check.md): earlier runtime baseline, superseded where later acceptance corrects it.
7. [Base maintenance audit](docs/neko-base-maintenance-audit.md): upstream integration and maintenance risks.
8. [External tutor integration](docs/neko-external-tutor-integration.md): extension seams; read with later native acceptance before proposing a separate Tutor Brain.

Local upstream/product references (gitignored; not delivered by cloning this lab):

- `candidates/N.E.K.O/docs/design/seven-day-tutorial-content-inventory.md`
- `candidates/N.E.K.O/docs/design/cat-idle-states-feature.md`
- `candidates/N.E.K.O/docs/zh-CN/architecture/memory-system.md`
- `candidates/N.E.K.O/docs/development/voice-readiness.md`
- `candidates/N.E.K.O/docs/zh-CN/modules/tts-client.md`
- `candidates/N.E.K.O/docs/zh-CN/plugins/migration-v0.9.md`
- Packaged tutorial: `benchmarks/raw/neko-app/resources/bin/static/tutorial/yui-guide/days/`
- Packaged Study onboarding: `benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion/onboarding.md`
- Packaged cat chat: `benchmarks/raw/neko-app/resources/bin/static/app/app-react-chat-window/cat-local-chat.js`

## Next acceptance work

1. On an interactive desktop, correlate a fresh awareness `respond` message with
   the awake character UI, then restore the previous awareness configuration.
2. Diagnose region capture's `capture_busy`; retest the latest explicit capture
   mode metadata and full-screen fallback policy through the physical UI.
3. Broaden grading and teaching samples, including identical-question wrong and
   correct answers, context pressure, realistic materials and longer follow-ups.
4. Review source integration of the host/message-plane repairs. The local frozen
   binary compatibility deployment is not a release solution.
5. With the user present, complete microphone / ASR / TTS and spoken interruption
   acceptance. This round can remain muted and does not require live microphone use.

Awareness periodically reads activity/context and may trigger proactive messages.
Its default `title_first` path is lightweight; optional `ocr_text`/`both` modes
can use OCR. Manual full-screen OCR latency does not establish the cause of its
old startup failure. The proposed normal-character history repair was withdrawn
after the awake chat test passed. No new Tutor Brain or teaching extension is
currently justified solely by the completed tests.

## Evidence and repository layout

```text
docs/                    tracked reports and handoffs
scripts/                 tracked diagnosis and acceptance scripts
patches/                 source patches and deployment notes
benchmarks/materials/    synthetic, shareable acceptance fixtures
candidates/              ignored third-party checkouts with their own history
benchmarks/raw/           ignored packages, extracted source, runtime data
  evidence/              ignored logs, measurements and desktop screenshots
  asar-src/              extracted Electron files
  neko-app/              packaged application
```

GitHub contains the reports and scripts, **not the raw evidence or application
bundle**. A fresh clone alone cannot reproduce this machine's environment or
independently inspect the original screenshots. Arrange sanitized evidence and
version-pinned dependencies separately when handing work to another machine.

## Earlier conclusions and working discipline

[base-evaluation.md](docs/base-evaluation.md) and
[architecture-notes.md](docs/architecture-notes.md) preserve the initial evaluation.
The initial claims that N.E.K.O has no teaching layer, that the desktop shell could
not run, and that `no_renderer` proves a core capture defect were overturned by
later artifact and runtime checks. Do not reuse them as the current rationale for
option A.

Keep raw captures and credentials out of Git. Do not print API keys. Before an
authorized push, check sensitive paths and tracked changes. Confirm the character
state before UI tests, announce desktop control, and return input control afterward.
Agree the scope before configuration changes or core modifications; use isolated
copies and reversible validation where possible. Configuration, source presence
and synthetic tests do not replace real-device acceptance.
