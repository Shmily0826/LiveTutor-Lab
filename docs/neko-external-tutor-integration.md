# Connecting an external Tutor Brain to Project N.E.K.O

## Finding

**Treat native N.E.K.O Study Companion as the default.** Its last in-tree implementation already covers a substantial tutor workflow: explanations, question generation and evaluation, knowledge tracking, summaries, OCR/image input, document analysis, study modes, memory decks/reviews, N.E.K.O chat commands, and optional study-aware supervision. That is likely enough for a conventional study companion; an external Tutor is not required just to have tutoring features.

The visible limit is that `TutorLLMAgent` is primarily a set of structured, one-shot operations. It does not appear to be a general, streamed, state-owning tutor conversation loop. N.E.K.O's own chat can still provide conversational responses with Study Companion context. External Tutor service becomes justified only if a named requirement needs pedagogy or state ownership beyond those native workflows, such as a persistent Socratic dialogue brain, adaptive lesson planning, or an independent tutor tool/curriculum loop.

If such a gap is confirmed, the least invasive first integration seam is the Study Companion plugin's own `TutorLLMAgent`/model gateway boundary. Only use a host-side `ExternalRouteKind` if the service must own the ordinary N.E.K.O chat turn itself. This assessment does not decide between N.E.K.O and OLV.

## Revision and method

- Repository: [`Project-N-E-K-O/N.E.K.O`](https://github.com/Project-N-E-K-O/N.E.K.O)
- Branch: `main`
- Current host revision: [`c8bf3505e455826ca9a3320e7f7dcace240b73c8`](https://github.com/Project-N-E-K-O/N.E.K.O/commit/c8bf3505e455826ca9a3320e7f7dcace240b73c8), `main`, dated 2026-10-07.
- Native Study Companion assessment: [`43c6c39730008f74f4762aac1a9418ee0bd5693f`](https://github.com/Project-N-E-K-O/N.E.K.O/commit/43c6c39730008f74f4762aac1a9418ee0bd5693f), the parent of upstream removal commit [`e27c0f072908ad61ae30c2a58c404203a7edab41`](https://github.com/Project-N-E-K-O/N.E.K.O/commit/e27c0f072908ad61ae30c2a58c404203a7edab41). The removal commit says the built-in plugin was moved to marketplace distribution.
- The workspace had no N.E.K.O checkout. I inspected source files from these exact public GitHub revisions through the GitHub source API. The repository is large; a clone was not completed.
- No GUI, Electron, audio device, or Windows validation was attempted.

The current host commit does not bundle the Study Companion source: `study_companion` is marked marketplace-only in packaging/install code. The native assessment below uses the last upstream in-tree implementation immediately before that move. It is real N.E.K.O source, but it is not proof that the current marketplace package has byte-for-byte identical code. The marketplace's current version should be checked before implementation.

## Native Study Companion capability assessment

### What native already provides

The pre-market-split [`plugin.toml`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/plugin.toml) describes an adaptive study companion for screen classification, question generation, answer evaluation, concept explanation, and session summaries. Source inspection shows a broader workflow:

- [`TutorLLMAgent`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/tutor_llm_agent.py) supports concept explanation, question generation, answer evaluation, knowledge tracking, and session summarization. Results are normalized into `TutorReply`; structured calls have JSON correction, operation deadlines, quota handling, and deterministic degraded fallbacks.
- Separate `agent` and `vision` model runtimes are resolved through [`StudyModelGateway`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/study_model_gateway.py). It can use the host LLM factory for generic supported providers or the Qwen native transport. This is already a useful native model-selection boundary.
- Study modes include companion, teaching, and interactive behavior. The plugin stores current question/evaluation, topic/knowledge state, screen classifications, and session summary context ([`models.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/models.py), [`mode_manager.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/mode_manager.py)).
- OCR and screen/image flows feed text and optional vision images into explanations/questions. Document analysis supports chunking and merge; the plugin also has a notebook, knowledge graph, focused practice scopes, flashcard/deck/review flows, and quality/contribution controls ([Tutor entries](https://github.com/Project-N-E-K-O/N.E.K.O/tree/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion)).
- Study utilities include Pomodoro, check-ins, supervision/reminders, and opt-in screen/activity awareness. N.E.K.O communication exposes commands such as explain current material, quiz me, show progress, start a review, and change mode ([`entry_neko_commands.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/entry_neko_commands.py)). Solution narration can send a completed study response back through N.E.K.O voice ([`entry_tutor_explain_entries.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/entry_tutor_explain_entries.py)).
- Study persistence is owned by the plugin store/database. N.E.K.O still owns desktop/chat/voice/TTS and its separate general memory infrastructure.

These features make **native N.E.K.O only sufficient for ordinary study-companion needs**, provided its current marketplace build retains the workflows above and its model quality/configuration meets the user's bar. The code already has useful fallback behavior and does not need a Strong Tutor service merely to answer study questions or build review workflows.

### Native capability gaps to confirm

The gaps below are limits visible in the inspected code, not assumed needs:

1. **General conversational pedagogy:** `TutorLLMAgent` exposes operation methods and builds operation-specific prompts. It is not a general-purpose autonomous tutor loop with an agent-managed multi-turn dialogue/history contract. N.E.K.O chat can be conversational and can receive study context, but that is the N.E.K.O chat model, not the structured TutorLLMAgent.
2. **Token streaming from TutorLLMAgent:** the generic gateway calls `ainvoke` ([`study_model_gateway.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/43c6c39730008f74f4762aac1a9418ee0bd5693f/plugin/plugins/study_companion/study_model_gateway.py)), and the native transport returns a completed result. That path is request/response. N.E.K.O normal chat has its own streaming callbacks, but the study agent does not expose equivalent token deltas for its structured operations.
3. **Pedagogy/state ownership:** plugin state tracks study workflows and learning artifacts, but the model API is called per operation with constructed context. The inspected code does not establish a long-lived tutor service that autonomously owns curriculum progression, persistent learner model updates, or an iterative teaching policy between turns.
4. **Tutor-specific service tools:** the plugin exposes many bounded study operations, but no generic Tutor Brain tool loop is visible in `TutorLLMAgent` itself. A service that must plan and invoke its own tools requires an agent boundary above the current model call.
5. **Current distribution parity:** Study Companion was removed from the host repository for marketplace distribution on 2026-09-03. The latest marketplace package was not locally available, so the checked historical in-tree capability list needs a quick version check against the installed/current market artifact.

### Decision order

1. Try the native plugin with a representative set of goals: free-form tutoring dialogue, screenshot-grounded explanation, question generation and evaluation, follow-up adaptation, persisted review state, and voice interruption.
2. If native falls short, decide whether a native improvement is enough: streaming operation results, a persistent study dialogue/state layer, or improved prompts/model configuration may close the gap without an external service.
3. Add an external Tutor service only for remaining, concrete gaps (for example, a service-owned adaptive dialog and curriculum state). Do not add one only to reuse another codebase.

## Real turn lifecycle

There are two main input modes; the final output path is shared at the manager boundary.

### Typed text and attachments

1. The frontend sends `stream_data` to the main WebSocket handler. If an external route owns that character, `websocket_router.py` offers the message to `route_external_stream_message` first. A claimed message skips ordinary chat.
2. Otherwise `main_logic/core/streaming.py` maintains ordering, session readiness, turn ownership, image staging and callback bookkeeping. It selects `OmniOfflineClient` for text input and calls `session.stream_text(...)`.
3. The offline client constructs messages from session history, prompt/context, and staged images (`turn_images` and screen/user source labels), then uses its provider/model client to generate the response. Streaming deltas call the manager's `handle_text_data` callback.
4. The manager streams assistant text to the frontend and, when external TTS is enabled, queues the text for its existing TTS runtime. Response completion/discard callbacks close out turn bookkeeping.

### Speech and live audio

1. The WebSocket handler forwards microphone input to the session unless a registered external route claims it. For realtime sessions, `OmniRealtimeClient` owns the provider WebSocket and turn protocol; ASR/transcript events call manager callbacks.
2. `LLMSessionManager.handle_input_transcript` validates and records the transcript, updates activity/turn state, publishes user-utterance events, and then follows the active route or ordinary model path. In external-route flows, the route may use N.E.K.O's realtime session for STT with audio passthrough, or consume a transcript through its route handler.
3. Realtime response text and native audio arrive through client callbacks. Text uses `handle_text_data`; PCM uses `handle_audio_data`; those feed the UI/audio path and TTS/playback lifecycle. New user turns rotate `speech_id`, clear stale speech, and cancellation is coordinated with the client.

### Ownership by component

| Stage | Current owner |
|---|---|
| User text/audio ingress and WebSocket framing | Frontend + `main_routers/websocket_router.py` |
| Session lifetime, turn IDs, interruption and ownership | `LLMSessionManager` (`main_logic/core/*`) |
| Screen/image attachment and source labeling | `main_logic/core/streaming.py`, `OmniOfflineClient` media mixin; realtime client for live multimodal input |
| Prompt assembly and conversation history on normal text turns | `OmniOfflineClient` and its caller/context setup |
| Normal text model/provider call | `OmniOfflineClient` via `utils.llm_client`/provider factory |
| Normal realtime model/provider call | `OmniRealtimeClient` |
| Assistant text delivery | `LLMSessionManager.handle_text_data` |
| External TTS/playback and native audio forwarding | `LLMSessionManager` TTS/runtime callbacks and frontend |
| Durable memory and plugin event fan-out | N.E.K.O memory services and `main_logic.agent_event_bus` consumers |
| Study workflow/learning state | Study Companion plugin store/state (verified in last pre-market-split source); current marketplace package parity not checked |

### Where pedagogy can change

For ordinary N.E.K.O chat, teaching behavior is currently part of prompt/history/model generation in the session client. For a Study Companion-specific turn, pedagogy can be replaced at the service-call boundary owned by the plugin, if its agent exposes one, or before normal chat by a host-side external route. The provider factory is a model boundary, but it is not intrinsically a tutor-turn boundary.

## Existing extension points

### External route registry — strongest whole-turn seam

[`utils/external_route_registry.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/c8bf3505e455826ca9a3320e7f7dcace240b73c8/utils/external_route_registry.py) defines `ExternalRouteKind`. Its handlers include `route_stream_message`, optional `route_voice_transcript`, `on_start_session`, and lifecycle/finalization callbacks. The registry has owner identity checks around awaits so stale route instances do not consume an input. Its module documentation explicitly describes it as an input takeover registry and names the existing mini-game route as its current consumer.

[`main_routers/game_router/__init__.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/c8bf3505e455826ca9a3320e7f7dcace240b73c8/main_routers/game_router/__init__.py) registers a route kind with that registry. [`main_routers/websocket_router.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/c8bf3505e455826ca9a3320e7f7dcace240b73c8/main_routers/websocket_router.py) is a caller/hijack point. This is real turn ownership: a claimed input does not reach the ordinary model path, so an external Tutor can control response content and follow-up turns for as long as the Study route stays active.

Limit: this registry accepts in-process Python callables. N.E.K.O plugins are isolated processes over ZMQ. A regular plugin cannot register an `ExternalRouteKind` using only the documented plugin hooks; a host shim or a new narrow IPC bridge is needed.

### Takeover mixin — useful but incomplete alone

[`main_logic/core/takeover.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/c8bf3505e455826ca9a3320e7f7dcace240b73c8/main_logic/core/takeover.py) provides tokenized `acquire_takeover`/`release_takeover`. It suppresses ordinary output and routes realtime voice transcripts to a dispatcher. It is currently used by the game route. The inspected `handle_input_transcript` interception is conditioned on voice-source transcripts, so this API alone does not establish takeover of typed-text turns. It is also a manager object API, not a plugin-process API. Use the external route registry for typed and spoken input; do not treat `TakeoverMixin` by itself as a complete Tutor integration.

### Plugin hooks and message bus — useful for workflow, not turn replacement

The plugin SDK documents lifecycle handlers (`startup`, `shutdown`, `reload`, `config_change`), message/event handlers, plugin entries, and hooks such as `before_entry`, `around_entry`, and `replace_entry`. Those hooks compose **plugin entries**; they are not hooks around `LLMSessionManager`, `OmniOfflineClient.stream_text`, or the core chat dispatch.

`main_logic.agent_event_bus.dispatch_user_utterance` fans the utterance out to registered sinks. `dispatch_text_user_message` is a first-hit hook used for text-message side effects; the code comments in `main_logic/core/turn.py` explicitly say the mini-game matcher does not consume the message and normal chat still responds. These are not generic chat-response substitution hooks.

### Remote/local plugin tools — not a Tutor turn boundary

[`plugin/sdk/plugin/llm_tool.py`](https://github.com/Project-N-E-K-O/N.E.K.O/blob/c8bf3505e455826ca9a3320e7f7dcace240b73c8/plugin/sdk/plugin/llm_tool.py) describes how a plugin exposes a function to the main model: the plugin registers a tool, the model chooses it, the host calls back into the plugin, then the model resumes. This is valuable for lookup, grading, or a bounded tutoring action. It leaves the primary model in charge of whether to call the tool, how to interpret it, and what to say. It does not guarantee follow-up pedagogy, response wording, or a service-owned conversational state.

## Integration strategies

| Strategy | Core files changed | Streaming preserved | Study state preserved | Memory preserved | Proactive preserved | Upstream merge risk | Recommendation |
|---|---|---|---|---|---|---|---|
| Native N.E.K.O Study Companion only | 0 changes; install/enable marketplace plugin | N.E.K.O chat streams; structured TutorLLMAgent operations are completed calls | Yes; StudyStore and study-state workflows are native | N.E.K.O general memory and plugin study memory remain distinct | Yes; native supervision and awareness options are available | None | **Start here.** Likely sufficient for structured study workflows; validate the specific tutoring goals and current market package first. |
| Native improvement to Study Companion | Plugin source only; for example add token streaming or persistent conversational tutor state to `TutorLLMAgent` | Yes if operation APIs expose deltas and host output callbacks | Strong; extends the native StudyStore/model | Strong; can continue explicit N.E.K.O memory integration | Strong; native plugin stays active | Low for N.E.K.O core; release/package process only | Prefer when a native gap is limited to streaming, dialogue continuity, prompt/model selection, or study-state policy. |
| Provider/model replacement behind `StudyModelGateway` | Usually config only for a supported OpenAI-compatible service; else plugin adapter | Current gateway uses `ainvoke`; replacing the endpoint does not itself add streaming | Yes, native agent and store remain owners | Yes, native plugin and N.E.K.O memory architecture remain | Yes | Low | Suitable for a better model/provider. **Not** a Strong Tutor Brain takeover: current prompts, operation schemas, correction, and pedagogy remain native. |
| TutorLLMAgent adapter to abstract local/remote Tutor service | Study Companion source only; 0 N.E.K.O host files | Current interface is one-shot; add an async delta contract if streaming is a requirement | Yes if adapter sends state/session ID and applies returned updates | N.E.K.O memory remains separate; pass only relevant memory/context | Yes for N.E.K.O; native study supervision remains | Low for N.E.K.O core; plugin release process only | **Lowest intrusion if a confirmed native capability gap requires service-owned pedagogy.** Replace above the native prompt/operation layer if service is to own its policy; provider replacement alone is insufficient. |
| Remote/local Tutor as an LLM tool | 0 core files; plugin tool registration | Tool call is request/response; main model continues the stream | Plugin may persist bounded action state | Normal N.E.K.O memory stays; tutor gets only passed tool arguments | Yes | Low | Keep for hints, grading, and retrieval. It does not close a whole-turn pedagogy gap. |
| Host-side `ExternalRouteKind` + HTTP Tutor service | Add route adapter and import/registration wiring (estimate 1 new host module + 1 registration site; possibly context helper) | Yes; route can forward deltas through manager text/TTS | Yes, if it owns stable session/state sync; otherwise native plugin state is bypassed | N.E.K.O memory only with explicit read/publish; normal model history commit is bypassed | N.E.K.O proactive remains; tutor-aware proactive needs deliberate state bridge | Low to medium; narrow designed registry | Use only if the Tutor must own the **ordinary N.E.K.O chat turn**, not just Study Companion operations. More intrusion than adapting the plugin's own agent. |
| Direct `OmniOfflineClient` provider adapter | Modify provider/client construction and config (estimate 2–4 host files) | Yes for OpenAI-compatible streaming | N.E.K.O session history remains owner; external study state needs explicit sync | Strong normal memory/context reuse | Yes | Medium | Avoid as first Tutor integration. It is a global/session model path, not a Study Companion agent seam. |
| Replace core agent/session loop | `main_logic/core/streaming.py`, `turn.py`, `lifecycle.py`, `manager.py`, plus session/memory/TTS paths (many files) | Must rebuild callback/cancellation contracts | High regression risk | High regression risk | High regression risk | High | Avoid. Native plugin and route/provider boundaries are narrower. |

## Recommended decision and shape

The current evidence supports this order:

- **Native-only:** enough for the Study Companion capabilities implemented in the last inspected native version: structured explanations, questions/evaluation, OCR/screen grounding, document and review workflows, study persistence, and N.E.K.O voice/chat interaction. Verify against the current marketplace build because the code was moved out of the main repository.
- **If native is short on token streaming or sustained free-form dialogue:** first extend the native Study Companion agent API/state model. That preserves its mature workflows and avoids a remote service boundary.
- **If a concrete requirement needs a distinct tutor policy/state machine or tutor-owned agent tool loop:** then call an abstract local/remote Tutor service from an adapter above `TutorLLMAgent`, while keeping native Study Companion responsible for UI, study workflow, storage, OCR, and N.E.K.O hooks. Pass state explicitly and return structured state updates.
- **If that service must own every normal N.E.K.O chat response during Study mode:** use `ExternalRouteKind` as the host-side input gate; this is a separate, slightly higher-intrusion design.

```text
N.E.K.O desktop / avatar / voice / screen / memory / proactive
                         │
        Native Study Companion workflows and state
                         │
               TutorLLMAgent boundary
                         │ HTTP (SSE or NDJSON)
           local or remote Strong Tutor service
                         │
       structured result or deltas → N.E.K.O UI/voice
```

For a service call, pass only the context it needs: a stable study session ID, utterance/operation, mode, bounded relevant history, learning-state snapshot, and selected screen/OCR/image context. Have it return the teaching reply plus optional structured state updates. Keep UI, speech, cancellation, and memory storage semantics in N.E.K.O/the plugin. Do not forward all N.E.K.O memory or screen data by default.

Suggested small service contract:

```json
{
  "request_id": "turn-uuid",
  "character_id": "...",
  "study_session_id": "...",
  "utterance": "...",
  "study_mode": "...",
  "learning_state": {},
  "conversation": [],
  "screen_context": {"text": "...", "images": []}
}
```

Use SSE/NDJSON events such as `delta`, `state_update`, `done`, and `error`. Send cancellation with the same `request_id` when N.E.K.O rotates/interupts the active speech turn. Keep the Tutor service from deciding UI/audio mechanics; it returns pedagogy text and optional structured learning-state updates.

## Minimal PoC status

No end-to-end PoC was run. The Cloud environment was available, but `/workspace` contained no N.E.K.O checkout; the source was inspected remotely at the pinned commit. A standalone HTTP mock/client here would prove only that HTTP streaming works, not that the real route is registered, that Study Companion can activate it, or that N.E.K.O memory/TTS/interruption callbacks remain correct. The source-level boundary is verified: the registry accepts async route handlers and the existing game route registers one, while the normal text client exposes streamed deltas and the manager exposes text/TTS callbacks. A real headless PoC still needs a local checkout plus a tiny host adapter and tests for claimed text input, one voice transcript, stream cancellation, and memory synchronization.

## Safe extension points

- `utils.external_route_registry.ExternalRouteKind` for a complete per-character input route, after Study-mode activation wiring is available.
- `OmniOfflineClient.stream_text` / `OmniRealtimeClient` callback contracts when the external service fits the normal provider model.
- `LLMSessionManager.handle_text_data`, turn IDs, response lifecycle callbacks, and TTS queue as host output infrastructure.
- Plugin SDK lifecycle, persistent `PluginStore`, bus read/watch, and `llm_tool` for plugin-owned workflows, state, and bounded tools.
- `main_logic.agent_event_bus` fan-out for memory/plugin observation, with explicit publication when a normal turn is bypassed.

## Core fork required

- A separate plugin process cannot currently register an external route or claim the default chat turn by declaring a lifecycle hook.
- The existing `TakeoverMixin` does not intercept typed turns by itself and is not exposed as plugin RPC.
- `dispatch_text_user_message` is observational/side-effect plumbing, not a response replacement API.
- If a Tutor must receive screen state, learning state, and memory and own every ordinary chat turn, N.E.K.O currently has no single generic tutor-provider contract that bundles those inputs with session ownership. Add a narrow Study-mode route/adapter and explicit state synchronization. Replacing the full agent loop would cross many active session, turn, context, memory, realtime, and TTS files.

## Do not modify for this goal

- Avoid rewriting `main_logic/core/manager.py`, `turn.py`, and `streaming.py` as a new general-purpose agent framework. They own concurrency, turn IDs, stale-response rejection, callback delivery, memory bookkeeping, and TTS/interruption races.
- Avoid modifying both `OmniOfflineClient` and `OmniRealtimeClient` unless the design deliberately replaces both model modes. Start at the route boundary or Study Companion's own adapter.
- Avoid using plugin tool registration as a substitute for turn ownership. It adds an optional tool, not an external tutor authority.

## Unresolved blockers

1. The current marketplace package was not available locally. Compare it with the last pre-market-split source to confirm feature parity, turn ownership, and any new `TutorLLMAgent` streaming/state interfaces.
2. The current host route registry has no documented plugin-process registration API. A route adapter is a small N.E.K.O host addition unless Study Companion already owns its own turn.
3. The precise memory API and data policy for sharing excerpts with a local/remote Tutor must be chosen. Route claiming skips the ordinary text model history write unless the adapter deliberately mirrors relevant turns.
4. Screen context is not automatically transformed into a Tutor request by the route registry. Define whether screen images/captions are forwarded from input events or sampled through an existing screen context service, and enforce payload/retention limits.
5. Streaming interruption requires request cancellation at the remote Tutor service and a reliable mapping from its request ID to the host's current speech ID; the existing client callbacks do not automatically cancel an arbitrary HTTP service.
6. Study-aware proactive prompts need explicit integration. N.E.K.O's proactive infrastructure can continue, but Tutor-owned learning state will not magically reach it.
