"""Ask the running host's plugin where a target_window capture would have come from.

Four cases against the shipped gate, through the host's own plugin /runs protocol,
and no model call at all: three refusals must return no text, and only the window
whose own words were confirmed may return any.

  python scripts/neko_target_window_host_probe.py            # host already started
"""
from __future__ import annotations

import argparse
import ctypes
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from neko_desktop_tutor_session import FOREIGN_MARKERS, LESSON_LINES, LESSON_TITLE, open_lesson_window
from neko_lab_client import LabClient

DECOY_TITLE = "Synthetic Decoy Fixture (LiveTutor test)"
IMPOSSIBLE_MARKERS = ("Xiaomi File Explorer", "private-final.docx")


def compact(value: str) -> str:
    return "".join(str(value or "").lower().split())


def refused(result: dict[str, object], reason: str) -> bool:
    """A refusal must come back as an Err naming its reason; `carried_text` shows no text."""
    return bool(not result.get("ok") and reason in str(result.get("error") or ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=48916)
    args = parser.parse_args()

    client = LabClient(port=args.port)
    cases: list[dict[str, object]] = []

    def snapshot(**arguments: object) -> dict[str, object]:
        started = time.monotonic()
        try:
            result = client.call("study_ocr_snapshot", arguments, timeout=180)
            data = result["data"]
            data = data.get("data") if isinstance(data.get("data"), dict) else data
            return {"ok": True, "ms": round((time.monotonic() - started) * 1000), "data": data}
        except RuntimeError as error:
            # The refusal text is all that comes back; an Err carries no OCR payload.
            return {"ok": False, "ms": round((time.monotonic() - started) * 1000), "error": str(error)[:600]}

    def record(name: str, passed: bool, evidence: dict[str, object]) -> None:
        cases.append({"case": name, "pass": bool(passed), **evidence})
        print(json.dumps({"case": name, "pass": bool(passed), **evidence}, ensure_ascii=False)[:400])

    user32 = ctypes.windll.user32

    def lesson_hwnd() -> int:
        child = int(lesson.winfo_id())
        return int(user32.GetAncestor(child, 2) or 0) or child

    def focus_lesson() -> dict[str, object]:
        """Windows only lets the process that owns the foreground keep it, so re-claim it
        before each case and report what the desktop actually shows."""
        lesson.lift()
        lesson.attributes("-topmost", True)
        lesson.focus_force()
        lesson.update()
        hwnd = lesson_hwnd()
        user32.SwitchToThisWindow(hwnd, True)
        user32.SetForegroundWindow(hwnd)
        lesson.update()
        time.sleep(0.6)
        front = int(user32.GetForegroundWindow() or 0)
        return {"wants": hwnd, "foreground": front, "foreground_title": window_title(front),
                "is_foreground": front == hwnd}

    def window_title(hwnd: int) -> str:
        if not hwnd:
            return ""
        length = int(user32.GetWindowTextLengthW(hwnd) or 0)
        buffer = ctypes.create_unicode_buffer(length + 2)
        user32.GetWindowTextW(hwnd, buffer, length + 2)
        return str(buffer.value or "").strip()[:60]

    def foreground_state() -> dict[str, object]:
        front = int(user32.GetForegroundWindow() or 0)
        return {"foreground": front, "is_foreground": front == lesson_hwnd()}

    lesson = None
    decoy = None
    try:
        lesson, _note = open_lesson_window()
        decoy = tk.Toplevel(lesson)
        decoy.title(DECOY_TITLE)
        decoy.geometry("620x300+520+300")
        decoy.configure(background="#f7dede")
        for line in ("Save As", "X:\\Users\\someone\\Documents\\private-final.docx"):
            tk.Label(decoy, text=line, background="#f7dede", font=("Arial", 20)).pack(pady=8)
        decoy.update()
        decoy.lower()
        lesson.lift()
        lesson.focus_force()
        lesson.update()
        time.sleep(1.2)

        focus_lesson()
        unmarked = snapshot(capture_mode="target_window", window_title=LESSON_TITLE)
        record("request without expected_markers is refused before any pixel is read",
               refused(unmarked, "expected_markers"),
               {"error": unmarked.get("error", "")[:220], "carried_text": "text" in unmarked,
                "ms": unmarked["ms"]})

        behind = snapshot(capture_mode="target_window", window_title=DECOY_TITLE,
                          expected_markers=list(LESSON_LINES), min_marker_matches=1)
        record("a window that is not the foreground one is refused, not cropped",
               refused(behind, "target_window_not_foreground"),
               {"error": behind.get("error", "")[:220], "carried_text": "text" in behind,
                "ms": behind["ms"]})

        focus = focus_lesson()
        mismatched = snapshot(capture_mode="target_window", window_title=LESSON_TITLE,
                              expected_markers=list(IMPOSSIBLE_MARKERS), min_marker_matches=1)
        record("right window, unconfirmable content is refused with no text",
               (refused(mismatched, "content_mismatch")
                and not any(compact(marker) in compact(mismatched.get("error", ""))
                            for marker in IMPOSSIBLE_MARKERS)),
               {"error": mismatched.get("error", "")[:220], "carried_text": "text" in mismatched,
                "desktop": focus, "ms": mismatched["ms"]})

        focus = focus_lesson()
        accepted = snapshot(capture_mode="target_window", window_title=LESSON_TITLE,
                            expected_markers=list(LESSON_LINES), min_marker_matches=3)
        data = accepted.get("data") or {}
        text = str(data.get("text") or "")
        recognised = [line for line in LESSON_LINES if compact(line) in compact(text)]
        foreign = [marker for marker in FOREIGN_MARKERS if compact(marker) in compact(text)]
        record("the named window is captured and its own text proves the source",
               (accepted["ok"] and data.get("capture_mode_used") == "target_window"
                and data.get("capture_target_title") == LESSON_TITLE
                and int(data.get("target_window_markers_matched") or 0) >= 3
                and len(recognised) >= 3 and not foreign),
               {"ms": accepted["ms"], "capture_mode_used": data.get("capture_mode_used"),
                "capture_target_title": data.get("capture_target_title"),
                "route": data.get("active_window_capture_route"),
                "markers_matched": data.get("target_window_markers_matched"),
                "lesson_lines_recognised": len(recognised), "foreign_markers": foreign,
                "chars": len(text), "desktop": focus,
                "text_sha256": sha256(text.encode()).hexdigest()[:16]})
    finally:
        # The decoy shares the lesson window's interpreter, so it goes first.
        for window in filter(None, (decoy, lesson)):
            window.destroy()

    passed = all(case["pass"] for case in cases)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_kind": "HOST_PLUGIN_TARGET_WINDOW_GATE",
        "transport": f"host plugin server /runs on 127.0.0.1:{args.port}",
        "model_calls": 0,
        "cases": cases,
        "result": "PASS_HOST_TARGET_WINDOW_GATE" if passed else "FAIL_HOST_TARGET_WINDOW_GATE",
    }
    out_dir = ROOT / "benchmarks/raw/evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"neko-target-window-host-gate-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "artifact": path.relative_to(ROOT).as_posix(),
                      "passed": sum(1 for case in cases if case["pass"]), "total": len(cases)},
                     ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
