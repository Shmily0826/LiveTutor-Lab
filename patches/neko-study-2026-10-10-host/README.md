# Isolated N.E.K.O source-host text mute

Base: official `1d814cf32fba8c02b5727d2890710e4e7b8ece24` (candidate checkout unchanged).
The isolated source snapshot is `benchmarks/raw/neko-product-host`; `text-only-audio.patch`
preserves all changes, with exact base/patched hashes in `manifest.json`.

Set `NEKO_DEV_TEXT_ONLY=1` before importing or starting the isolated host. The flag
is pinned when its gate module is imported, so changing configuration or reloading
the Study Companion does not remove the gate. Optional `NEKO_DEV_AUDIO_AUDIT`
is a JSONL path for event/counter/PID evidence, without any speech content.

The gate forces the existing dummy worker before TTS provider selection, rejects
and counts queued nonempty dummy speech without invoking telemetry, refuses
native realtime connections before network calls with `_native_audio=False`,
and drops both normal speech and cached speech at the final frame boundary.
It also rejects any unsolicited native audio callback. This text product does
not support Realtime/ASR. Audio is disabled independently of plugin silent mode
and `DISABLE_TTS` configuration. The automatic Agent-LLM connectivity ping is
also skipped in this development mode, and the isolated web_search manifest
uses its existing `auto_start=false` preference.

Run the focused no-network regression:

```powershell
benchmarks/raw/goal-python/cpython-3.11.15-windows-x86_64-none/python.exe -B patches/neko-study-2026-10-10-host/test_text_only_audio.py
```

`audio-boundary-test-result.json` records eight exercised rejection boundaries,
with provider/websocket/telemetry sinks all zero. The regression compiles the
actual patched upstream method bodies and imports the actual gate. It supplies
fake downstream endpoints and no substitute mute guards. It does not boot the
whole host, deliver a plugin message through its EventBus, or prove operating
system isolation. Real source-host boot/UI/provider audit remains separate.

Official launch: Python 3.11 `launcher.py` from the isolated source directory,
with `NEKO_MERGED=1`. All storage variables, `APPDATA` and `LOCALAPPDATA` must
point to disposable project data before imports. The system Python is 3.14;
the preserved frozen distribution has `python311.dll` but no interpreter exe.
Use the existing isolated Python 3.11 and the source `uv.lock` for dependencies.
