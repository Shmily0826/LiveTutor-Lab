"""Audit the inherited deployment and apply this Goal's explicit budget grant."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "benchmarks/raw/neko-desktop-egress-cap"
ROUND = "bargein-autocheck-20261012"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-budget", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; keep previous evidence")
    before = json.loads(LEDGER.read_text(encoding="utf-8"))
    if before.get("round") != ROUND:
        raise RuntimeError("unexpected round; no budget mutation")
    if args.apply_budget:
        after = {**before, "budgets": {**before["budgets"],
                 "api.deepseek.com": 2000, "www.lanlan.app": None, "www.lanlan.tech": 0}}
        assert after["spent"] == before["spent"]
        pending = LEDGER.with_suffix(".daily.tmp")
        pending.write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
        os.replace(pending, LEDGER)
    after = json.loads(LEDGER.read_text(encoding="utf-8"))
    manifest = ROOT / "patches/neko-study-2026-10-10-product/manifest.json"
    product = manifest.parent
    data = json.loads(manifest.read_text(encoding="utf-8"))
    checks = []
    for entry in data["files"]:
        source = product / entry["path"]
        name = entry["path"].removeprefix("payload/study_companion/")
        deployed = ROOT / data["deployment"] / name
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        checks.append({"path": entry["path"], "current_sha256": actual,
                       "manifest_current": actual == entry["sha256"],
                       "deployment_current": deployed.is_file() and
                       hashlib.sha256(deployed.read_bytes()).hexdigest() == actual})
    result = {"budget_before": before, "budget_after": after,
              "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "worktree": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
              "inherited_deployment_checks": checks,
              "proof": "read-only fingerprints, not runtime/model/playback acceptance"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"budget": after, "files": len(checks),
                      "manifest_current": sum(x["manifest_current"] for x in checks),
                      "deployment_current": sum(x["deployment_current"] for x in checks)}))


if __name__ == "__main__":
    main()
