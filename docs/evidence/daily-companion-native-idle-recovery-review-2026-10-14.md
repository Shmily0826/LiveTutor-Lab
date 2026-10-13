# Native idle / local relay review — 2026-10-14

Read contract/plan/status/blockers first. This agent only added this report: no production/test/manifest/ledger edits, host/process starts, API/provider/audio calls or new agent. Existing replacement13 artifacts and necessary deployed host/proxy source were inspected. Main independently owns its current SDK-local run and relay tests.

## Finding: twenty-second local CONNECT relay timeout, not proven provider idle

Replacement13 actual append log (`benchmarks/raw/neko-desktop-host.log:60924-60955`) establishes:

| Event | Wall seconds | Evidence |
| --- | --- | --- |
| Exact old material/token cancelled and gen1 deliberately closed | 1791920404.145 | raw `material_replacement.cancel_received_wall` / native stop receipt; log60929 |
| Fresh gen2 attached/reset | 1791920404.694 | log60937 |
| New socket sent `session.update` | 1791920404.700 | log60939 / raw `wire_trace` gen2 |
| Fresh gen2 lost unexpectedly, no close code | 1791920424.698 | log60949-60951 |
| Core ordinary recovery/teardown began | 1791920424.700 | log60952-60955 |

The new connection lasts **20.004s from attach / 19.998s from session update**. Raw replacement13 has no recorded received gen2 events; `session_ended_by_server` occurs at relative49.703. `picture-replacement13.host.log` is empty; the append log and raw JSON are the usable sources. The original scene did not submit a second utterance before teardown.

Pre-fix local `scripts/neko_desktop_tutor_host.py` set accepted client socket timeout20 (`_handle:674`) and upstream connection timeout20 (`_tunnel:721`), then passed both sockets unchanged into `_pump`. Socket connection timeouts remain read/write timeouts after connect. Each direction's `recv` could therefore time out independently after20s; `_pump` caught `OSError` and closed **both** sockets. An upstream with no events could cause this even while the other direction was transmitting client data. It is not equivalent to twenty seconds of total conversation inactivity.

This explains the no-code transport EOF and exact elapsed time with high confidence. The relay did not log which read timed out, so causation remains an inference from actual timing plus exact local code, not a captured timeout exception. Do not relabel it as a remote Lanlan API idle policy or billing/rate-limit event.

A small no-socket/no-network AST probe of the actual old `_pump`, with a fake `recv` raising built-in `TimeoutError`, confirmed one close on each socket. Its first attempt lacked the `socket` annotation namespace; the corrected probe passed. It verifies the branch, not real twenty-second timing.

## Existing host idle/readiness behavior is different

- Native client local silence timeout is90s (`main_logic/omni_realtime_client/_client.py:381-385`), checked every10s (`_audio.py:136-175`). Replacement13 has no local ninety-second timeout warning. The “silence task cancelled” line is teardown cleanup, not evidence that that task initiated this close.
- Core general session idle reset is1800s/check60s (`main_logic/core/_shared.py:140-141`, `lifecycle.py:894-941`). It cannot explain20s.
- Unexpected no-code EOF is classified `CHARACTER_DISCONNECTED` (`_transport.py:124-148,4019-4040`), closes failed transport and schedules a generation-stamped manager callback outside receive loop (`4318-4380`). Core correctly enters ordinary fail-closed recovery (`lifecycle.py:345-385`). No stale gen1 teardown of gen2 was observed: gen2 owns the failure and the scheduled recovery carries connection generation.
- Existing deferred Native reconnect only recognizes **`API_IDLE_TIMEOUT`** with an active voice-activation factory/runtime and exact current Native/Core lease/generation (`lifecycle.py:289-343`). Its next authorized output path reuses one guarded, bounded reconnect under session-swap lock (`asr_runtime.py:4550-4707`). Replacement13's unclassified EOF does not meet this diagnostic or establish that activation prerequisites existed.
- Material replacement itself performs one normal connect after exact-token cancellation, old close/listener drain, then restores listener/current state (`scripts/neko_material_audio_patch.py:193-230`); it resets input buffers and never calls barge-in PCM replay. The new connection genuinely attached; `session.update` send alone is not provider acknowledgement or new-utterance/device proof.

The general frontend `CHARACTER_DISCONNECTED` recording branch schedules a7.5s restart (`static/app/app-websocket.js:4348-4390,4708`); `session_ended_by_server` clears active/start state and stops recording (`5684-5725`). Ownership/epoch cancellation checks are present. This is not proof of a globally bounded number of reconnect episodes. Replacement13's fixed-input probe ended after server teardown; no successful delayed frontend reconnect was observed.

## Main's minimum relay correction reviewed

During this review Main changed only established `_tunnel` sockets to blocking after successful connect:

```python
conn.settimeout(None)
up.settimeout(None)
```

The CONNECT/header20s and upstream connection20s bounds remain; allowlist, accounting, request count, provider choice, audio/onset/cancel semantics are untouched. `_pump` now calls `shutdown(SHUT_RDWR)` before `close` on both ends (`733-751`), so EOF/error from one direction wakes a peer thread blocked in the other direction. This directly fixes the local per-direction20s close instead of broadening provider recovery to unknown errors.

Source review: appropriate minimum fix for this failure. Important boundary: established tunnel `recv`/`sendall` now has no per-operation timeout. Peer EOF/error, host-owned session teardown and the bounded test/host lifetime must own final closure. `Sink.stop` alone stops future accepts, not a registry of all active tunnel sockets; this patch does not add such a registry. A deliberately abandoned but still-open pair can retain daemon pump threads until its owner/process closes it. Normal host/provider closure and the new shutdown path should terminate peers; do not advertise an autonomous indefinite relay watchdog. `_forward` HTTP sockets retain their existing20s bounds and share only the improved shutdown cleanup.

Main's new `scripts/test_neko_proxy_idle.py` was read, not run by this agent. It uses actual `_tunnel/_pump` with local `socketpair`, a mocked upstream connect and no supplier/credentials/ledger. It checks inherited short deadlines and real21.2s quiet, new bidirectional bytes, unchanged counts and peer EOF/thread completion. At report creation the Main-owned test was running; its eventual result belongs to Main's evidence. These local bytes are transport checks, not audio or model acceptance.

## Bounded recovery plan / remaining provider behavior

1. First retain this relay correction; verify its local quiet/duplex/EOF result and only then, if needed, one Main-owned fixed-input long-quiet scene using a fresh utterance. Record exact fresh connection, received provider events, readiness, close classification and next response. No synthetic loud frames, fake speech onset, old PCM, old material response or old response-ID alias.
2. Do not automatically convert generic `CHARACTER_DISCONNECTED`/no-code EOF into `API_IDLE_TIMEOUT`. Genuine provider quota/auth/policy/network failure remains fail-closed. Preserve service backoff and single-scene bounds.
3. If a later genuine classified provider-idle case remains, reuse current-session guarded reconnect or the existing explicit voice-start flow **only on a new owner-authorized resume intent**. One CONNECT attempt per intent, one deadline, no periodic timer/recursive reconnect; mark intent consumed before awaiting. Fix role/socket/lease/activation/connection identity, recheck after barrier/close/connect/listener awaits, reject stop/route/session/material replacement, and on failure show restart-needed state. Automatic generic7.5s restart should not silently replenish the per-intent attempt cap.
4. The smallest safe on-demand fallback is an explicit resume/start action that waits for ready before accepting a fresh utterance; it uses no cached PCM. If automatic first-speech recovery is later required, preserve only that new utterance's already authorized bounded input via existing ingress/activation ownership, never replay material-old or pre-idle audio, and do not change the ordinary onset/cancel path. That is separate implementation/validation, not justified by this local20s failure alone.

No new production fix was made by this agent; Main's relay delta was only reviewed. Long provider silence beyond the existing90s policy, remote reconnect reliability, readiness acknowledgement, delayed fresh Native/device answer and human experience remain unverified. Scope frozen.
