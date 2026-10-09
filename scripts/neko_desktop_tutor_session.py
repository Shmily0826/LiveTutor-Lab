"""Drive a real text-only Study session through the running N.E.K.O host.

Nothing here is a fixture: every call goes over the host's own plugin /runs
protocol to the plugin the host loaded, and the model calls are the host's own
provider configuration. With --window the lesson is a dedicated synthetic
desktop window that this script creates, brings to the foreground, captures
through the plugin's active-window OCR, and closes again.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from neko_lab_client import LabClient  # noqa: E402

LESSON_TITLE = "Synthetic Lesson Fixture (LiveTutor test)"
LESSON_LINES = (
    "Example 3: substitution",
    "Let u = 2x + 1",
    "Then du = 2 dx",
    "So dx = du / 2",
    "Integrate e^u with the 1/2 factor",
)
FOLLOW_UPS = (
    "为什么这里的 dx 要乘 1/2？",
    "为什么选 u = 2x+1，而不是 u = e^(2x+1)？",
)
WRONG_ANSWER = "令 u = 2x+1，则 du = dx，所以积分就是 e^(2x+1)+C。"
# Anything in this list means the captured region contained a window that is not
# our synthetic lesson, so the text must never reach a provider.
FOREIGN_MARKERS = ("save as", "file explorer", "This PC", "Xiaomi", "search", "organize", "final")


def open_lesson_window() -> tuple[tk.Tk, str]:
    root = tk.Tk()
    root.title(LESSON_TITLE)
    root.geometry("900x520+90+70")
    root.configure(background="#eef3f6")
    frame = tk.Frame(root, background="white", highlightthickness=2, highlightbackground="#8da3b0")
    frame.pack(fill="both", expand=True, padx=26, pady=26)
    tk.Label(frame, text="SYNTHETIC STUDY MATERIAL - NOT A PERSONAL SCREEN",
             background="white", foreground="#5b7180", font=("Arial", 11)).pack(pady=(24, 6))
    tk.Label(frame, text=LESSON_LINES[0], background="white", foreground="#17242b",
             font=("Arial", 28, "bold")).pack(pady=(8, 18))
    for line in LESSON_LINES[1:]:
        tk.Label(frame, text=line, background="white", foreground="#17242b",
                 font=("Arial", 24)).pack(pady=8)
    root.update_idletasks()
    root.update()
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()
    root.update()
    return root, "synthetic lesson window created for active-window capture"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", action="store_true", help="create the synthetic lesson window and OCR it")
    parser.add_argument("--capture-only", action="store_true",
                        help="prove the capture source locally and stop; the session makes no model call")
    parser.add_argument("--text", default="", help="explain this text instead of capturing a window")
    parser.add_argument("--port", type=int, default=48916)
    args = parser.parse_args()
    if args.capture_only and not args.window:
        parser.error("--capture-only needs --window: it exists to stop before the first provider call")

    client = LabClient(port=args.port)
    steps: list[dict[str, object]] = []

    def call(entry: str, timeout: int = 150, **arguments: object) -> dict[str, object]:
        if args.capture_only and entry not in {"study_status", "study_ocr_snapshot"}:
            # Enforced at the call site, not only by the branch order: no later edit can
            # make a capture-only run reach an entry that talks to the provider.
            raise RuntimeError(f"capture-only run refuses entry {entry}: it could reach the provider")
        started = time.monotonic()
        response = client.call(entry, arguments, timeout=timeout)
        # The host wraps every plugin result as {run_id, elapsed_ms, data}.
        data = response.get("data") if isinstance(response.get("data"), dict) else response
        elapsed = round((time.monotonic() - started) * 1000, 1)
        steps.append({"entry": entry, "ms": elapsed,
                      "keys": sorted(str(key) for key in data)[:16],
                      "reply": str(data.get("reply") or data.get("question") or data.get("text")
                                  or data.get("summary") or "")[:1500],
                      "degraded": data.get("degraded"), "verdict": data.get("verdict"),
                      "score": data.get("score"), "diagnostic": data.get("diagnostic")})
        print(json.dumps({"step": entry, "ms": elapsed,
                          "head": steps[-1]["reply"][:260]}, ensure_ascii=False))
        return data

    window_note = ""
    window = None
    capture_guard: dict[str, object] = {}
    session_id = ""
    session: dict[str, object] = {}
    stored: dict[str, object] = {}
    # Decided here, before anything can call the model: a capture-only run stops at the
    # capture, whatever the later branches do.
    stop_after_capture = args.capture_only
    try:
        status = call("study_status")
        runtime = {key: status.get(key) for key in ("model_runtime", "communication_status", "status")
                   if key in status}
        lesson = ""
        if args.window:
            window, window_note = open_lesson_window()
            time.sleep(1.2)
            # The gate now lives in the plugin: `target_window` refuses unless the named
            # window is the foreground window at capture time and its own text proves
            # which window was really cropped. Nothing is sent anywhere on a refusal.
            refusal = ""
            try:
                shot = call("study_ocr_snapshot", capture_mode="target_window",
                            window_title=LESSON_TITLE, expected_markers=list(LESSON_LINES),
                            min_marker_matches=3)
            except RuntimeError as exc:
                shot, refusal = {}, str(exc)[:400]
            captured = str(shot.get("text") or "")
            compact = "".join(captured.lower().split())
            hits = [line for line in LESSON_LINES
                    if "".join(line.lower().split()) in compact]
            # Second opinion: foreign markers prove the region swept in a window that is
            # not ours, so the text stays local even if the plugin gate were absent.
            foreign = [marker for marker in FOREIGN_MARKERS
                       if "".join(marker.lower().split()) in compact]
            gated = shot.get("capture_mode_used") == "target_window"
            lesson = captured if (gated and len(hits) >= 3 and not foreign) else ""
            capture_guard = {
                "plugin_gate": "target_window",
                "plugin_gate_active_in_loaded_build": gated,
                "refusal": refusal,
                "capture_mode_used": shot.get("capture_mode_used"),
                "capture_target_title": shot.get("capture_target_title"),
                "target_window_markers_matched": shot.get("target_window_markers_matched"),
                "active_window_capture_route": shot.get("active_window_capture_route"),
                "lesson_lines_recognised": len(hits),
                "foreign_window_markers": foreign,
                "accepted": bool(lesson),
                "detail": str(shot.get("active_window_capture_detail") or "")[:120],
                "rejected_text_withheld": (not lesson) and {"chars": len(captured),
                                                            "sha256": __import__("hashlib").sha256(
                                                                captured.encode()).hexdigest()[:16]},
            }
            print(json.dumps({"capture_guard": capture_guard}, ensure_ascii=False))
        elif args.text:
            lesson = args.text
        if not stop_after_capture:
            if not lesson.strip():
                raise RuntimeError("no lesson text: capture returned nothing and no --text was given")

            session_id = str(call("study_start_session").get("session_id") or "")
            if not session_id:
                raise RuntimeError("the host plugin started no study session")
            call("study_set_mode", mode="teaching", reason="desktop session")
            call("study_explain_text", text=lesson, session_id=session_id)
            for follow_up in FOLLOW_UPS:
                call("study_explain_text", text=follow_up, session_id=session_id)
            asked = call("study_generate_question", text=lesson, topic="u-substitution-linear",
                         session_id=session_id)
            call("study_evaluate_answer", answer=WRONG_ANSWER, session_id=session_id,
                 question=str(asked.get("question") or ""), expected_answer=str(asked.get("answer") or ""),
                 question_id=str(asked.get("question_id") or ""), attempt_id=str(asked.get("attempt_id") or ""))
            call("study_explain_text", text="结合我刚才答错的那一步，再讲一次系数是怎么来的。",
                 session_id=session_id)
            session = call("study_summarize_session", focus="", session_id=session_id)
            stored = call("study_get_session", session_id=session_id)
    finally:
        if window is not None:
            window.destroy()

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "transport": f"host plugin server /runs on 127.0.0.1:{args.port}",
        "lesson_window": window_note,
        "capture_guard": capture_guard,
        "capture_only": bool(stop_after_capture),
        "model_calls": len([step for step in steps if step["entry"].startswith("study_")
                           and step["entry"] not in {"study_status", "study_ocr_snapshot"}]),
        "host_model_runtime": runtime if isinstance(runtime, (dict, list)) else str(runtime)[:400],
        "steps": steps,
        "summary_head": str(session.get("reply") or session.get("summary") or "")[:600],
        "session_id": session_id,
        "persisted_interaction_count": len((stored or {}).get("interactions") or []),
        "degraded_steps": [step["entry"] for step in steps if step.get("degraded")],
    }
    out_dir = ROOT / "benchmarks/raw/evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"neko-desktop-tutor-session-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if "sk-" in text:
        raise SystemExit("refusing to write a report containing a credential")
    path.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"status": "DESKTOP_TUTOR_CAPTURE_ONLY" if args.capture_only else "DESKTOP_TUTOR_SESSION",
                      "artifact": path.relative_to(ROOT).as_posix(),
                      "model_calls": report["model_calls"], "steps": len(steps),
                      "degraded": report["degraded_steps"],
                      "interactions": report["persisted_interaction_count"]}, ensure_ascii=False))
    if args.capture_only and not capture_guard.get("accepted"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
