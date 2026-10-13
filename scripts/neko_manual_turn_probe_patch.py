"""Opt-in Lanlan.app MANUAL support probe; no automatic endpointing policy.

Apply only to an isolated source/deployment root, then start that host with
NEKO_FREE_MANUAL_TURN_PROBE=1. The owning audio socket may send
{action: end_audio_turn, request_id: <unique id>} after fixed input ends.
The acknowledgement confirms local dispatch only, never provider support.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

MODE_MARKER = "# free-manual-turn-support-probe-v1"
ROUTER_MARKER = "# free-manual-turn-probe-router-v1"
MODE_HELPER = '''    # free-manual-turn-support-probe-v1
    def _select_free_manual_turn_probe(self):
        import os
        route = getattr(getattr(self, "_realtime_protocol_capabilities", None), "route_key", None)
        enabled = (os.environ.get("NEKO_FREE_MANUAL_TURN_PROBE") == "1"
                   and route == "lanlan_app_gemini" and self._is_free_proxy)
        previous = getattr(self, "_manual_turn_probe_original_mode", None)
        if enabled:
            if previous is None:
                self._manual_turn_probe_original_mode = self.turn_detection_mode
            self.turn_detection_mode = TurnDetectionMode.MANUAL
        elif previous is not None:
            self.turn_detection_mode = previous
            del self._manual_turn_probe_original_mode
        self._free_manual_turn_probe_enabled = enabled

'''

ROUTER_HELPER = '''# free-manual-turn-probe-router-v1
def _manual_turn_probe_enabled():
    import os
    return os.environ.get("NEKO_FREE_MANUAL_TURN_PROBE") == "1"


async def _dispatch_manual_turn_probe(manager, websocket, message, *, owns_voice):
    request_id = message.get("request_id")
    valid_id = isinstance(request_id, str) and 0 < len(request_id) <= 128
    session = getattr(manager, "session", None)
    generation = getattr(session, "_connection_generation", None)
    route = getattr(getattr(session, "_realtime_protocol_capabilities", None), "route_key", None)
    reason = ""
    if not _manual_turn_probe_enabled():
        reason = "disabled"
    elif not owns_voice():
        reason = "not_voice_owner"
    elif not valid_id:
        reason = "invalid_request_id"
    elif (getattr(manager, "input_mode", None) != "audio"
          or getattr(manager, "_asr_route_mode", None) != "native"
          or route != "lanlan_app_gemini" or not getattr(session, "_is_free_proxy", False)
          or not getattr(session, "_free_manual_turn_probe_enabled", False)
          or getattr(session, "_fatal_error_occurred", False)):
        reason = "not_live_manual_native_free_session"
    elif getattr(session, "_manual_turn_probe_last_request", None) == request_id:
        reason = "duplicate_request"
    dispatched = False
    if not reason:
        # Reserve the probe id before awaiting so a retry never commits it twice.
        session._manual_turn_probe_last_request = request_id
        try:
            await asyncio.wait_for(session.signal_user_activity_end(), timeout=10.0)
            dispatched = True
            if (not owns_voice() or getattr(manager, "session", None) is not session
                    or getattr(session, "_connection_generation", None) != generation):
                reason = "owner_or_session_changed_during_dispatch"
        except Exception as exc:
            reason = type(exc).__name__
    await websocket.send_text(json.dumps({"type": "manual_turn_probe",
        "request_id": request_id if valid_id else None,
        "dispatched": dispatched, "reason": reason,
        "generation": generation, "wall": time.time(), "mono": time.monotonic(),
        "proof": "local dispatch only; inspect provider events for MANUAL support"}))


'''


def _replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError("manual probe source changed; inspect anchors before applying")
    return source.replace(old, new, 1)


def patch_transport(source: str) -> str:
    if MODE_MARKER in source:
        ast.parse(source)
        return source
    anchor = "    async def connect(self, instructions: str, native_audio=True) -> None:\n"
    result = _replace_once(source, anchor, MODE_HELPER + anchor)
    result = _replace_once(result, "        self._native_audio = native_audio\n",
                           "        self._native_audio = native_audio\n        self._select_free_manual_turn_probe()\n")
    ast.parse(result)
    return result


def patch_router(source: str) -> str:
    if ROUTER_MARKER in source:
        ast.parse(source)
        return source
    anchor = "def _is_voice_path_message(message: dict) -> bool:\n"
    result = _replace_once(source, anchor, ROUTER_HELPER + anchor)
    classify = '    if action in {"voice_input_control", "voice_identity_control", "pause_session"}:\n'
    result = _replace_once(result, classify,
        '    if action == "end_audio_turn" and _manual_turn_probe_enabled():\n        return True\n' + classify)
    superseded = '        if message.get("action") == "voice_identity_control":\n'
    result = _replace_once(result, superseded,
        '        if message.get("action") == "end_audio_turn" and _manual_turn_probe_enabled():\n'
        '            await _dispatch_manual_turn_probe(voice_mgr, websocket, message, owns_voice=_owns_voice_connection)\n'
        '            return\n' + superseded)
    primary = '            if action == "voice_identity_control":\n'
    result = _replace_once(result, primary,
        '            if action == "end_audio_turn" and _manual_turn_probe_enabled():\n'
        '                await _dispatch_manual_turn_probe(session_manager[lanlan_name], websocket, message, owns_voice=_owns_voice_connection)\n'
        '                continue\n' + primary)
    ast.parse(result)
    return result


def remove_router_probe(source: str) -> str:
    """Strip only a complete known probe, preserving every unrelated byte."""
    blocks = (
        ROUTER_HELPER,
        '    if action == "end_audio_turn" and _manual_turn_probe_enabled():\n        return True\n',
        '        if message.get("action") == "end_audio_turn" and _manual_turn_probe_enabled():\n'
        '            await _dispatch_manual_turn_probe(voice_mgr, websocket, message, owns_voice=_owns_voice_connection)\n'
        '            return\n',
        '            if action == "end_audio_turn" and _manual_turn_probe_enabled():\n'
        '                await _dispatch_manual_turn_probe(session_manager[lanlan_name], websocket, message, owns_voice=_owns_voice_connection)\n'
        '                continue\n',
    )
    symbols = (ROUTER_MARKER, "_manual_turn_probe_enabled", "_dispatch_manual_turn_probe")
    if not any(symbol in source for symbol in symbols):
        ast.parse(source)
        return source
    if any(source.count(block) != 1 for block in blocks):
        raise ValueError("partial or unknown manual router probe; cannot safely remove")
    result = source
    for block in blocks:
        result = result.replace(block, "", 1)
    if any(symbol in result for symbol in symbols):
        raise ValueError("unknown manual router probe content remains")
    ast.parse(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    edits = []
    for relative, patcher in (("main_logic/omni_realtime_client/_transport.py", patch_transport),
                               ("main_routers/websocket_router.py", patch_router)):
        path = root / relative
        original = path.read_text(encoding="utf-8")
        updated = patcher(original)
        edits.append((path, original, updated))
    # Validate both files before writing either. Preserve unrelated content.
    for path, original, updated in edits:
        state = "already_patched" if original == updated else "patch_available"
        if args.apply and original != updated:
            pending = path.with_suffix(".manual-probe.tmp")
            if pending.exists():
                raise RuntimeError("existing manual probe temporary file; inspect first")
            try:
                pending.write_text(updated, encoding="utf-8")
                pending.replace(path)
            finally:
                if pending.exists():
                    pending.unlink()
            state = "patched"
        print(json.dumps({"path": str(path), "status": state, "enabled_by_default": False,
                          "automatic_endpointing_added": False}))


if __name__ == "__main__":
    main()
