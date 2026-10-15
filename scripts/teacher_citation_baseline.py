"""Historical baseline: run the deterministic line-citation check over teacher replies already on disk.

Reads benchmarks/raw/evidence/*.json (read-only). A reply counts when it sits next to the
`source_evidence` windows it was written from. Identifier checks need the evidence text, which
those files do not keep, so only line citations are measured here. Offline, no model.
usage: python teacher_citation_baseline.py [out.json]
"""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("citation_check", ROOT / "patches/neko-study-2026-10-10-product/payload/study_companion/study_citation_check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def walk(node, found):
    if isinstance(node, dict):
        reply, sources = node.get("reply"), node.get("source_evidence")
        if isinstance(reply, str) and reply.strip() and isinstance(sources, list) and sources:
            found.append((reply, sources))
        for value in node.values():
            walk(value, found)
    elif isinstance(node, list):
        for value in node:
            walk(value, found)


def main():
    rows, seen = [], set()
    for path in sorted((ROOT / "benchmarks/raw/evidence").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        found = []
        walk(data, found)
        for reply, sources in found:
            if reply in seen:
                continue
            seen.add(reply)
            claims = check.line_claims(reply)
            bad = check.line_violations(reply, sources)
            rows.append({"file": path.name, "reply": reply, "claims": [c["text"] for c in claims],
                         "violations": [{"text": v["text"], "missing": v["missing"]} for v in bad],
                         "shown": {k: [min(v), max(v)] for k, v in check.shown_lines(sources).items() if v}})
    with_claims = [r for r in rows if r["claims"]]
    violating = [r for r in rows if r["violations"]]
    summary = {"replies": len(rows), "with_line_claims": len(with_claims), "violating": len(violating),
               "claims": sum(len(r["claims"]) for r in rows), "violating_claims": sum(len(r["violations"]) for r in rows)}
    out = {"summary": summary, "violating": violating, "all": rows}
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    for r in violating:
        print("-", r["file"], r["violations"], "|", r["reply"][:110].replace("\n", " "))


if __name__ == "__main__":
    main()
