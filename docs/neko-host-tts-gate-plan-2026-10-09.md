# N.E.K.O host TTS gate: evidence and next step (2026-10-09)

## Decision

**Host and real Study UI remain BLOCKED.** No N.E.K.O process, plugin load, microphone, audio device, live network, credential, or database was accessed. No sound was generated. This pass made no changes to the checkpoint, overlay, candidate source, or frozen binaries.

The current evidence is insufficient to prove a host-wide mute before launch. The installed host must not be used for Study UI E2E until a gate has been verified against its exact build in an isolated fixture.

## What the package identifies

- The preserved server artifact is `benchmarks/raw/neko-app/resources/bin/projectneko_server.exe` (531,506,448 bytes; SHA-256 `BE32BD8555EFE6450F01191DB4FAB41D4C25B6C14C8C52C44B1F645086AF6288`). Its Windows ProductVersion and FileVersion are both `1.0.0.0`; these generic fields do not identify a source revision.
- The extracted bundle exposes `main_logic/asr_client`, but not the server's `main_logic/core` or TTS implementation. No build manifest/source map found in the inspected package tree links the server binary to a commit.
- `candidates/N.E.K.O` is a separate source checkout at `1d814cf32fba8c02b5727d2890710e4e7b8ece24`, whose `config/application.py` declares `0.9.0`. No evidence ties that commit to the server binary above. Treat all source findings below as candidate-only.

## Candidate source findings

- Candidate `DISABLE_TTS` selects a dummy external TTS worker/provider. It does not disable the native realtime route: candidate `main_logic/core/turn.py` can call `send_speech`, which reaches websocket audio output in `main_logic/core/tts_runtime.py`.
- Candidate tests cover many TTS and websocket behaviors, but the reviewed test inventory did not establish the required end-to-end negative assertion: a real plugin message increments a host reject counter while both provider and websocket fakes receive zero calls.
- Plugin `silent_mode` only guards plugin message paths. It is not evidence of a host-wide output gate. Historical `tts:free` activity and the limits of the earlier checkpoint are recorded in `neko-goal-v0.2-checkpoint.md`.

## Required safe route to unblock

1. Obtain an authoritative package manifest or reproducible build record that maps the installed server binary hash to the exact source revision and build configuration. Keep the installed executable frozen.
2. On that matching source revision, add a development-only, fail-closed gate at both boundaries: reject and count external TTS dispatch before provider invocation, and drop and count every audio frame at the final websocket output boundary. Disable native audio before session construction. Keep the gate unavailable to normal production configuration.
3. Verify only in an offline fixture: no external network route, no real credentials or DB, no microphone/audio device, fake provider and websocket sinks. Submit an actual plugin message and separately exercise ordinary and native-realtime audio paths. Require both attempt counters to increment and both downstream call counts to stay zero. Make startup fail closed if the fixture guard is missing; exercise failure and restoration using only the fixture.
4. Preserve the gate's build fingerprint and fixture evidence. Only then consider a local Study UI run against that isolated build, synthetic fixture screen, and disposable store. A pass there proves that isolated build only; it does not prove the installed production runtime.

## Resume criteria for Study UI E2E

The isolated UI run may proceed only after the matching-source gate above passes. Keep it local and fixture-only, then record visible transitions and persistence for: a short concept, explanation prompt, same-example follow-up, retrieval question, submitted answer, visible score, saved Session/Mastery, and later reuse. Do not use a personal screen, production/live network, or real student store.

Until source/build identity and both host output boundaries are proven, report **host TTS gate: BLOCKED; Study UI E2E: BLOCKED**. Do not infer runtime safety from plugin silence, worker selection, candidate tests, or package version strings.
