"""Prove where a target_window capture would come from, on the real desktop.

This reads no pixels and calls no model: it only runs the shipped window-identity
helpers from the plugin source against windows this script creates itself, so the
capture source is confirmed before any OCR or provider call is allowed.

  .tmp-uv-cache/neko-study-venv/Scripts/python.exe scripts/neko_target_window_guard_check.py
"""
from __future__ import annotations

import ast
import ctypes
import hashlib
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "benchmarks/raw/neko-app/resources/bin/plugins/study_companion/entry_ocr_entries.py"
LESSON_TITLE = "Synthetic Lesson Fixture (LiveTutor test)"
DECOY_TITLE = "Synthetic Decoy Fixture (LiveTutor test)"
SELF_TITLE = "N.E.K.O Mimic Fixture (must never be a capture target)"
LESSON_LINES = ("Example 3: substitution", "Let u = 2x + 1", "Then du = 2 dx")
DECOY_LINES = ("Save As", "X:\\Users\\someone\\Documents\\private-final.docx")
HELPERS = (
    "_foreground_hwnd",
    "_window_title",
    "_hwnd_for_title",
    "_named_window_target",
    "_window_target_for_hwnd",
    "_marker_list",
    "_markers_matched",
)


def load_helpers() -> dict[str, object]:
    """Exec the module-level helpers of the shipped plugin, without the plugin package."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    selected = [node for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in HELPERS]
    if sorted(node.name for node in selected) != sorted(HELPERS):
        raise RuntimeError("shipped capture helpers are missing from the plugin source")
    namespace: dict[str, object] = {
        "_ACTIVE_WINDOW_SELF_MARKERS": ("N.E.K.O", "NekoClaw"),
        "_ACTIVE_WINDOW_TITLE_LIMIT": 240,
        "_ACTIVE_WINDOW_MIN_SIDE": 64,
    }
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *selected],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


def make_window(title: str, lines: tuple[str, ...], origin: str, root: tk.Tk | None = None) -> tk.Toplevel:
    window = root or tk.Toplevel()
    window.title(title)
    window.geometry(origin)
    window.configure(background="#eef3f6")
    frame = tk.Frame(window, background="white", highlightthickness=2, highlightbackground="#8da3b0")
    frame.pack(fill="both", expand=True, padx=26, pady=26)
    tk.Label(frame, text="SYNTHETIC STUDY MATERIAL - NOT A PERSONAL SCREEN",
             background="white", foreground="#5b7180", font=("Arial", 11)).pack(pady=(24, 6))
    for line in lines:
        tk.Label(frame, text=line, background="white", foreground="#17242b", font=("Arial", 22)).pack(pady=6)
    window.update_idletasks()
    window.update()
    return window


def main() -> int:
    namespace = load_helpers()
    named = namespace["_named_window_target"]
    foreground = namespace["_foreground_hwnd"]
    window_title = namespace["_window_title"]
    measure = namespace["_window_target_for_hwnd"]
    matched = namespace["_markers_matched"]

    checks: list[dict[str, object]] = []

    def record(name: str, passed: bool, detail: object) -> None:
        checks.append({"check": name, "pass": bool(passed), "detail": detail})
        print(json.dumps({"check": name, "pass": bool(passed), "detail": detail}, ensure_ascii=False))

    def top_hwnd(widget: tk.Tk | tk.Toplevel) -> int:
        child = int(widget.winfo_id())
        return int(ctypes.windll.user32.GetAncestor(child, 2) or 0) or child

    record("an empty title is refused", named("")[1] == "target_window_title_required", named("")[1])
    absent = named("No Such Window Anywhere (LiveTutor test)")
    record("a title with no window is refused", absent == (None, "target_window_not_found", 0), absent)

    lesson = make_window(LESSON_TITLE, LESSON_LINES, "+90+70")
    decoy = make_window(DECOY_TITLE, DECOY_LINES, "+360+250")
    mimic = make_window(SELF_TITLE, ("host overlay",), "+520+330")
    lesson_hwnd, decoy_hwnd, mimic_hwnd = top_hwnd(lesson), top_hwnd(decoy), top_hwnd(mimic)
    lesson.after_idle(lambda: (lesson.lift(), lesson.focus_force()))
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and int(foreground()) != lesson_hwnd:
        lesson.lift()
        lesson.focus_force()
        lesson.update()
        time.sleep(0.05)

    record("the synthetic lesson window really holds the foreground",
           int(foreground()) == lesson_hwnd,
           {"foreground": int(foreground()), "foreground_title": window_title(int(foreground())),
            "lesson_hwnd": lesson_hwnd})

    target, refusal, resolved = named(LESSON_TITLE)
    record("the explicit title resolves to that one window",
           refusal == "" and target is not None and resolved == lesson_hwnd,
           {"refusal": refusal, "hwnd": resolved, "title": (target or {}).get("title")})
    if target:
        screen = (ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
        region = [target["left"], target["top"], target["right"], target["bottom"]]
        record("the cropped region is a strict subset of the primary monitor",
               0 <= region[0] < region[2] <= screen[0] and 0 <= region[1] < region[3] <= screen[1]
               and region != [0, 0, screen[0], screen[1]],
               {"region": region, "screen": list(screen)})

    behind = named(DECOY_TITLE)
    record("a window that exists but is behind the target is refused, not cropped",
           behind[1] == "target_window_not_foreground" and behind[0] is None,
           {"reason": behind[1], "hwnd": behind[2]})
    partial = named("Synthetic Lesson Fixture")
    record("a title that is only a prefix of the real one resolves to nothing",
           partial == (None, "target_window_not_found", 0), partial)

    record("N.E.K.O's own surfaces are never a usable target",
           measure(mimic_hwnd) is None and measure(lesson_hwnd) is not None,
           {"mimic": measure(mimic_hwnd), "lesson": bool(measure(lesson_hwnd))})

    markers = ("let u = 2x + 1", "then du = 2 dx", "integrate e^u")
    ocrish = "Example 3: substitution\nLet  u = 2X+1\nthen du=2 dx"
    record("markers survive the spacing OCR produces", matched(ocrish, markers) == 2,
           {"matched": matched(ocrish, markers), "markers": list(markers)})
    record("the unrelated window's own text matches no lesson marker",
           matched(" ".join(DECOY_LINES), markers) == 0, matched(" ".join(DECOY_LINES), markers))

    for window in (lesson, decoy, mimic):
        window.destroy()

    passed = all(item["pass"] for item in checks)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_kind": "REAL_DESKTOP_WINDOW_TARGET_GUARD",
        "pixels_captured": 0,
        "model_calls": 0,
        "plugin_source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "checks": checks,
        "result": "PASS_TARGET_WINDOW_GUARD" if passed else "FAIL_TARGET_WINDOW_GUARD",
    }
    out_dir = ROOT / "benchmarks/raw/evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"neko-target-window-guard-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "artifact": path.relative_to(ROOT).as_posix(),
                      "passed": sum(1 for item in checks if item["pass"]), "total": len(checks)},
                     ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
