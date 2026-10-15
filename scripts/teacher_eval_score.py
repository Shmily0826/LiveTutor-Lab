"""Score teacher replies against scripts/teacher_eval_set.json (deterministic part of R2).

Reads probe output files from `neko_source_scene_probe.py --scenario r3eval` (one turn per question, `kind`
= question id). Per question it reports: citation findings from the payload gate (`citation_check`, present
when the gate ran in observe/on mode), line-window violations recomputed from the shown windows, forbidden
statements that matched, and which expected points were not matched. Matching expected points is a coarse
regex aid; a person still judges every reply against `expected_facts`.
usage: python teacher_eval_score.py out.json probe_output.json [probe_output.json ...]
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "citation_check", ROOT / "patches/neko-study-2026-10-10-product/payload/study_companion/study_citation_check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
EVAL = json.loads((Path(__file__).with_name("teacher_eval_set.json")).read_text(encoding="utf-8"))["questions"]


def score_reply(question, reply, sources, citation_check=None):
    """One reply against one eval question. Pure: used by the tests and the CLI."""
    line_bad = check.line_violations(reply, sources)
    forbidden = [f["id"] for f in question.get("forbidden", []) if re.search(f["regex"], reply)]
    missed = [i for i, alternatives in enumerate(question.get("must_match", []))
              if not any(re.search(pattern, reply, re.I) for pattern in alternatives)]
    gate = (citation_check or {})
    return {"id": question["id"], "kind": question["kind"], "line_violations": [v["text"] for v in line_bad],
            "gate_violations": gate.get("violations", 0), "gate_result": gate.get("result") or gate.get("mode", ""),
            "forbidden_hits": forbidden, "unmatched_points": missed, "reply": reply}


def main():
    out, files = Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]
    by_id = {q["id"]: q for q in EVAL}
    rows = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for turn in data.get("turns", []):
            question = by_id.get(turn.get("kind"))
            if not question:
                continue
            output = turn.get("output") or {}
            reply = turn.get("reply") or output.get("reply") or ""
            rows.append({"run": path.name, **score_reply(question, reply, turn.get("source_evidence") or output.get("source_evidence") or [],
                                                         output.get("citation_check"))})
    total = len(rows)
    summary = {"replies": total,
               "with_line_violation": sum(bool(r["line_violations"]) for r in rows),
               "with_gate_finding": sum(bool(r["gate_violations"]) for r in rows),
               "with_forbidden_statement": sum(bool(r["forbidden_hits"]) for r in rows),
               "with_unmatched_point": sum(bool(r["unmatched_points"]) for r in rows)}
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    for r in rows:
        flags = [name for name, bad in (("line", r["line_violations"]), ("gate", r["gate_violations"]),
                                        ("forbidden", r["forbidden_hits"]), ("missed", r["unmatched_points"])) if bad]
        print(f"{r['run'][:28]:28} {r['id']} {','.join(flags) or 'ok'}")


if __name__ == "__main__":
    main()
