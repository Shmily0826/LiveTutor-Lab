"""Final review tool for the shipped plugin tree: rebuild chain + drift inventory.

Two questions, both answerable without running the host:

1. Rebuild chain — for every module the host imports, is it still the tracked snapshot,
   or is the change reproducible from the tracked patches?
2. Drift — most of the plugin was delivered as part of the preserved (gitignored) app
   bundle, so its bytes are not in Git at all. The inventory turns "was anything I did
   not look at truncated or overwritten?" into a hash comparison.

  python -I -S -B scripts/neko_plugin_source_coverage_check.py
  python -I -S -B scripts/neko_plugin_source_coverage_check.py --write-inventory
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "benchmarks/raw/neko-app/resources/bin"
OVERLAY = ROOT / "patches/neko-study-2026-10-09-v02-overlay"
INVENTORY = ROOT / "patches/neko-study-2026-10-09-final/plugin-tree-inventory.json"
TREES = {"imported_by_host": BIN / "plugins/study_companion",
         "distributed_alias": BIN / "plugin/plugins/study_companion"}
HOST_PLANE = BIN / "plugins"
EXTRA = {"imported_by_host": ["lab_study_plane.py", "lab_study_runtime.py"], "distributed_alias": []}
CHAIN = [
    "patches/neko-study-2026-10-08/study.patch",
    "patches/neko-study-2026-10-09-goal/goal-context.patch",
    "patches/neko-study-2026-10-09-round2/round2-teaching-context.patch",
    "patches/neko-study-2026-10-09-ui/ui-real-tutor.patch",
    "patches/neko-study-2026-10-09-target-window/target-window-capture.patch",
]
PRE_IMAGES = ["patches/neko-study-2026-10-09-ui/_pre",
              "patches/neko-study-2026-10-09-target-window/_pre",
              "patches/neko-study-2026-10-09-round2", "patches/neko-study-2026-10-09-goal/preimage"]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def patch_paths(patch: Path) -> dict[str, str]:
    """module name -> the path the patch writes it at (each patch uses its own prefix)."""
    paths = {}
    for header in re.findall(rb"^\+\+\+ b/(\S+)$", patch.read_bytes(), re.MULTILINE):
        relative = header.decode().replace("\\", "/")
        name = relative.rsplit("study_companion/", 1)[-1] if "study_companion/" in relative else relative.rsplit("/", 1)[-1]
        paths[name] = relative
    return paths


def rebuild_all(modules: dict[str, bytes], chain: list[Path]) -> tuple[dict[str, bytes], dict[str, str]]:
    """Run the whole patch chain once over a staged tree.

    A patch applies against every file it names, so all of them have to be present;
    staging one module at a time makes multi-file patches fail for the wrong reason.
    """
    current = {name: lf(data) for name, data in modules.items()}
    failed: dict[str, str] = {}
    for patch in chain:
        paths = patch_paths(patch)
        present = {name: relative for name, relative in paths.items() if name in current}
        if not present:
            continue
        working = Path(tempfile.mkdtemp(prefix="livetutor-rebuild-"))
        try:
            for name, relative in present.items():
                target = working / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(current[name])
            result = subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "-p1", str(patch.resolve())],
                                    cwd=working, capture_output=True, text=True)
            if result.returncode != 0:
                reason = result.stderr.strip()[:160]
                for name in present:
                    failed.setdefault(name, f"{patch.name}: {reason}")
                continue
            for name, relative in present.items():
                current[name] = lf((working / relative).read_bytes())
        finally:
            shutil.rmtree(working, ignore_errors=True)
    return current, failed


def pre_image(module: str) -> Path | None:
    for directory in PRE_IMAGES:
        root = ROOT / directory
        if not root.is_dir():
            continue
        for candidate in (root / module, *root.rglob(module)):
            if candidate.is_file():
                return candidate
    return None


def tree_modules(tree: Path, label: str) -> list[Path]:
    files = sorted(tree.glob("*.py"))
    if label == "imported_by_host":
        files += sorted([HOST_PLANE / name for name in EXTRA[label] if (HOST_PLANE / name).is_file()])
    return files


def build_inventory() -> dict[str, object]:
    return {
        "format": "livetutor-plugin-tree-inventory-v1",
        "note": "hashes of what the host actually imports; the app bundle itself is not in Git",
        "trees": {
            label: {path.name: {"bytes": len(lf(path.read_bytes())), "sha256": digest(lf(path.read_bytes()))}
                    for path in tree_modules(tree, label)}
            for label, tree in TREES.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-inventory", action="store_true", help="record current hashes into patches/")
    parser.add_argument("--allow-patch", action="append", default=[], help="extra patch to add to the chain")
    args = parser.parse_args()

    if args.write_inventory:
        inventory = build_inventory()
        INVENTORY.parent.mkdir(parents=True, exist_ok=True)
        INVENTORY.write_text(json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8", newline="\n")
        counts = {label: len(entry) for label, entry in inventory["trees"].items()}
        print(json.dumps({"written": INVENTORY.relative_to(ROOT).as_posix(), "modules": counts}, ensure_ascii=False))
        return 0

    chain = [ROOT / entry for entry in CHAIN + args.allow_patch if (ROOT / entry).is_file()]
    manifest = json.loads((OVERLAY / "manifest.json").read_text(encoding="utf-8-sig"))
    declared = {entry["source"].replace("\\", "/"): entry for entry in manifest["files"]}

    # Run the chain twice over a staged tree: once from the v02 snapshot (the real
    # history) and once from each round's own `_pre` mirror (what round 3 recorded as
    # the verified rebuild path), then take whichever reproduces the running bytes.
    named = sorted({name for patch in chain for name in patch_paths(patch)})
    from_snapshot: dict[str, bytes] = {}
    from_mirror: dict[str, bytes] = {}
    for name in named:
        source = next((key for key in declared if key.endswith("/study_companion/" + name)), None)
        if source:
            from_snapshot[name] = (OVERLAY / declared[source]["payload"].replace("\\", "/")).read_bytes()
        mirror = pre_image(name)
        if mirror is not None:
            from_mirror[name] = mirror.read_bytes()
    seed = {name: from_snapshot.get(name) or from_mirror[name] for name in named if
            (from_snapshot.get(name) or from_mirror.get(name))}
    rebuilt_a, failed_a = rebuild_all(seed, chain)
    later = [patch for patch in chain
             if patch.name in {"ui-real-tutor.patch", "target-window-capture.patch"}]
    rebuilt_b, failed_b = rebuild_all({name: from_mirror.get(name) or from_snapshot[name] for name in seed}, later)

    status: dict[str, object] = {}
    problems: list[str] = []
    for label, tree in TREES.items():
        entries: dict[str, list] = {"snapshot_exact": [], "rebuilt_byte_exact": [], "pre_image_plus_patch": [],
                                   "modified_uncovered": [], "not_in_snapshot": [], "rebuild_failed": []}
        for path in tree_modules(tree, label):
            if path.parent != tree:  # host-plane modules are captured by file copy, not by patch
                continue
            source = str(path.relative_to(ROOT)).replace("\\", "/")
            entry = declared.get(source)
            if entry is None and path.name not in named:
                # Delivered inside the app bundle and never re-cut by a patch: only the
                # recorded inventory can say whether it still matches what shipped.
                entries["not_in_snapshot"].append(path.name)
                continue
            snapshot = OVERLAY / entry["payload"].replace("\\", "/") if entry else None
            if entry and (not snapshot.is_file() or digest(snapshot.read_bytes()) != entry["sha256"]):
                problems.append(f"{path.name}: snapshot payload missing or no longer matches its manifest hash")
                continue
            if snapshot is not None and lf(snapshot.read_bytes()) == lf(path.read_bytes()):
                entries["snapshot_exact"].append(path.name)
                continue
            if path.name in named:
                if lf(rebuilt_a.get(path.name, b"")) == lf(path.read_bytes()):
                    entries["rebuilt_byte_exact"].append(
                        {"module": path.name, "chain": [patch.name for patch in chain
                                                        if path.name in patch_paths(patch)]})
                elif lf(rebuilt_b.get(path.name, b"")) == lf(path.read_bytes()):
                    entries["pre_image_plus_patch"].append(
                        {"module": path.name, "chain": [patch.name for patch in later
                                                        if path.name in patch_paths(patch)],
                         "pre_image": (pre_image(path.name) or Path("")).relative_to(ROOT).as_posix()})
                else:
                    entries["rebuild_failed"].append(f"{path.name}: snapshot chain -> {failed_a.get(path.name, 'bytes differ')}"
                                                     f" | mirror chain -> {failed_b.get(path.name, 'bytes differ')}")
            else:
                entries["modified_uncovered"].append(path.name)
        status[label] = entries

    # Drift against the recorded inventory: catches the truncation accident class.
    drift = []
    if INVENTORY.is_file():
        recorded = json.loads(INVENTORY.read_text(encoding="utf-8"))["trees"]
        for label, tree in TREES.items():
            for path in tree_modules(tree, label):
                known = recorded.get(label, {}).get(path.name)
                if known is None:
                    drift.append(f"{label}/{path.name}: not in the recorded inventory")
                elif digest(lf(path.read_bytes())) != known["sha256"]:
                    drift.append(f"{label}/{path.name}: bytes changed since the inventory was recorded")
    else:
        drift.append("no inventory recorded: run --write-inventory")
    if drift:
        problems.append(f"drift: {drift}")

    # Truncation guard: parse every module; the accident under review cut a class body off.
    unparsable = []
    for tree in TREES.values():
        for path in sorted(tree.glob("*.py")):
            try:
                parsed = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError) as error:
                unparsable.append(f"{path.name}: {type(error).__name__}")
                continue
            if path.name == "entry_ocr_entries.py" and not any(
                    isinstance(node, ast.ClassDef) and node.name == "_OcrEntriesMixin" for node in parsed.body):
                unparsable.append(f"{path.name}: class body missing")
    if unparsable:
        problems.append(f"unparsable or truncated: {unparsable}")

    for label, entries in status.items():
        for key in ("modified_uncovered", "rebuild_failed"):
            if entries[key]:
                problems.append(f"{label}: {key}: {entries[key]}")

    counts = {label: {key: len(value) for key, value in entries.items()} for label, entries in status.items()}
    report = {
        "rebuild_chain": [path.name for path in chain],
        "counts": counts,
        "detail": {label: {key: value for key, value in entries.items() if key != "snapshot_exact"}
                   for label, entries in status.items()},
        "modules_not_in_git_snapshot": {label: entries["not_in_snapshot"] for label, entries in status.items()},
        "problems": problems,
        "result": "PASS_SOURCE_COVERAGE" if not problems else "REVIEW_SOURCE_COVERAGE",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS_SOURCE_COVERAGE" else 1


if __name__ == "__main__":
    sys.exit(main())
