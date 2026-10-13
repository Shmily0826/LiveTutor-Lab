"""Bounded checks for NEW daily material/preferences integration; no devices/retry."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
from neko_lab_client import LabClient
from neko_native_avatar_toolchain import call as callback, registered_tools

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "benchmarks/raw/neko-desktop-egress-cap"
COURSE = "daily-sky-scout-20261014"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "restart"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "prepare" and args.output.exists():
        raise RuntimeError("keep earlier evidence; do not repeat completed paid scenes")
    report = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else {"steps": []}
    if report.get(args.phase + "_complete"):
        raise RuntimeError("phase already completed")
    def ledger(): return json.loads(LEDGER.read_text(encoding="utf-8"))
    before = ledger()
    assert before["round"] == "bargein-autocheck-20261012"
    report[args.phase + "_before"] = before
    client = LabClient()
    def run(entry, fields=None, tool=False):
        assert ledger()["spent"].get("api.deepseek.com", 0) - before["spent"].get("api.deepseek.com", 0) < 25
        result = callback(entry, fields or {}) if tool else client.call(entry, fields or {})
        data = result.get("output", {}) if tool else result["data"]
        evidence_fields = {k: v for k, v in (fields or {}).items() if k != "image_base64"}
        if fields and "image_base64" in fields:
            evidence_fields["image_sha256"] = hashlib.sha256(base64.b64decode(fields["image_base64"])).hexdigest()
        report["steps"].append({"phase": args.phase, "entry": entry, "arguments": evidence_fields,
                                "result": result, "ledger": ledger()})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"entry": entry, "data": data, "seconds": result.get("_seconds", result.get("elapsed_ms", 0)/1000)}, ensure_ascii=False), flush=True)
        assert not result.get("is_error") and data.get("ok", True) and not data.get("degraded"), "stop on failure; keep evidence"
        return data
    report["registered_tools"] = registered_tools()
    assert {"study_material", "study_preferences", "study_point"} <= set(report["registered_tools"])
    if args.phase == "prepare":
        run("study_update_settings_config", {"config": {"llm": {"llm_vision_enabled": True, "llm_vision_max_image_px": 2048}}})
        run("study_session", {"action": "set_course", "course_id": COURSE}, True)
        run("study_preferences", {"preferences": {"language": "zh-CN", "length": "brief", "explanation_style": "step_by_step", "proactive_quiz": False}, "remember": True}, True)
        image = ROOT / "benchmarks/raw/evidence/diagram-input-sky-dark.png"
        if not image.is_file():
            image = ROOT / "benchmarks/raw/neko-diagram-pixels2-20261013/diagram-input-sky-dark.png"
        run("study_submit_image", {"image_base64": base64.b64encode(image.read_bytes()).decode(),
                                   "text": "用两句话解释 Flutter 到天气数据源的请求方向。看不清则说看不清，不出题。"})
        material = run("study_material", tool=True)
        assert material["picture_available"]
        report["material_id"] = material["material_id"]
        run("study_explain", {"question": "Explain that same weather request path in exactly two English sentences, no quiz."}, True)
        run("study_session", {"action": "set_course", "course_id": COURSE + "-other"}, True)
        assert not run("study_material", tool=True)["picture_available"]
        run("study_session", {"action": "set_course", "course_id": COURSE}, True)
        assert run("study_material", tool=True)["material_id"] == report["material_id"]
    else:
        assert run("study_material", tool=True)["material_id"] == report["material_id"]
        assert run("study_preferences", tool=True)["preferences"]["language"] == "zh-CN"
        run("study_explain", {"question": "重启前我们看的是哪张图、讨论哪条请求路线？中文两句话，不出题。"}, True)
        run("study_preferences", {"preferences": {"length": "detailed", "explanation_style": "example_first"}, "remember": True}, True)
        run("study_preferences", {"preferences": {"length": "brief", "explanation_style": "direct"}, "remember": False}, True)
        run("study_explain", {"question": "天气数据源在哪里？这次只答一句，不出题。"}, True)
        assert run("study_preferences", tool=True)["preferences"]["length"] == "detailed"
    report[args.phase + "_complete"] = True
    report[args.phase + "_after"] = ledger()
    report["proof"] = "real model + real plugin callback and database; no playback or human proof"
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
