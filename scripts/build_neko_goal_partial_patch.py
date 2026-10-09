"""Build a fingerprint-guarded patch for files with a preserved preimage."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PRE_ROOT = ROOT / "patches/neko-study-2026-10-09-round2/_pre"
TARGET_ROOT = ROOT / "benchmarks/raw/goal-isolated/study_companion"
OUTPUT_ROOT = ROOT / "patches/neko-study-2026-10-09-goal"
FILES = (
    "entry_tutor_context_support.py",
    "entry_tutor_explain_entries.py",
    "entry_tutor_question_entries.py",
    "llm_prompts.py",
    "prompt_templates.py",
)
RUNTIME_ROOTS = (
    ROOT / "benchmarks/raw/neko-app/resources/bin/plugin/plugins/study_companion",
    ROOT / "benchmarks/raw/neko-app/resources/bin/plugins/study_companion",
    ROOT / "benchmarks/raw/goal-isolated/study_companion",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_patch() -> dict[str, dict[str, str]]:
    preimage_root = OUTPUT_ROOT / "preimage/plugin/plugins/study_companion"
    preimage_root.mkdir(parents=True, exist_ok=True)
    patch_lines: list[str] = []
    manifest: dict[str, dict[str, str]] = {}
    for name in FILES:
        before = PRE_ROOT / name
        after = TARGET_ROOT / name
        if not before.is_file() or not after.is_file():
            raise FileNotFoundError(name)
        output_hashes = [sha256(root / name) for root in RUNTIME_ROOTS]
        if len(set(output_hashes)) != 1:
            raise RuntimeError(f"runtime copies differ for {name}: {output_hashes}")
        shutil.copyfile(before, preimage_root / name)
        with before.open(encoding="utf-8", newline="") as source:
            before_lines = source.readlines()
        with after.open(encoding="utf-8", newline="") as source:
            after_lines = source.readlines()
        patch_lines.extend(difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/plugins/study_companion/{name}",
            tofile=f"b/plugins/study_companion/{name}",
        ))
        manifest[name] = {
            "preimage_sha256": sha256(before),
            "runtime_postimage_sha256": output_hashes[0],
        }
    with (OUTPUT_ROOT / "goal-context.patch").open("w", encoding="utf-8", newline="") as patch_file:
        patch_file.writelines(patch_lines)
    (OUTPUT_ROOT / "manifest.json").write_text(
        json.dumps({
            "kind": "PARTIAL_FINGERPRINTED_SOURCE_PATCH",
            "base": "preserved round2 _pre source snapshot; not pristine vendor archive",
            "files": manifest,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify_target(path: Path, manifest: dict[str, dict[str, str]]) -> None:
    failures = []
    for name, fingerprints in manifest.items():
        actual = sha256(path / name)
        if actual != fingerprints["preimage_sha256"]:
            failures.append(f"{name}: expected {fingerprints['preimage_sha256']}, got {actual}")
    if failures:
        raise SystemExit("refusing to apply: target does not match preserved preimage\n" + "\n".join(failures))
    print(f"verified {len(manifest)} source preimages under {path}")


def smoke_apply(manifest: dict[str, dict[str, str]]) -> None:
    checks = []
    with tempfile.TemporaryDirectory(prefix=".smoke-", dir=OUTPUT_ROOT) as temp_name:
        temp = Path(temp_name)
        plugin_root = temp / "plugin"
        destination = plugin_root / "plugins/study_companion"
        destination.mkdir(parents=True)
        for name in FILES:
            shutil.copyfile(OUTPUT_ROOT / "preimage/plugin/plugins/study_companion" / name, destination / name)
        prefix = plugin_root.relative_to(ROOT).as_posix()
        patch = (OUTPUT_ROOT / "goal-context.patch").relative_to(ROOT).as_posix()
        subprocess.run(["git", "apply", "--check", f"--directory={prefix}", patch], cwd=ROOT, check=True)
        subprocess.run(["git", "apply", f"--directory={prefix}", patch], cwd=ROOT, check=True)
        for name, fingerprints in manifest.items():
            applied_text = (destination / name).read_text(encoding="utf-8")
            runtime_text = (TARGET_ROOT / name).read_text(encoding="utf-8")
            if applied_text != runtime_text:
                raise RuntimeError(f"patch content mismatch for {name}")
            checks.append({
                "file": name,
                "pass": True,
                "applied_sha256": sha256(destination / name),
                "runtime_sha256": fingerprints["runtime_postimage_sha256"],
                "text_equal_after_newline_normalization": True,
            })
    evidence = {
        "evidence_kind": "PORTABLE_PATCH_SMOKE_APPLY",
        "base": "preserved round2 preimage copied to a disposable temporary tree",
        "applied_with": "git apply --check then git apply",
        "checks": checks,
        "all_pass": all(item["pass"] for item in checks),
        "limitation": "Windows CRLF preimages can retain CRLF; content equality normalizes line endings.",
    }
    evidence_path = ROOT / "benchmarks/raw/evidence/neko-goal-portable-patch-smoke.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"patch smoke apply passed for {len(manifest)} files; temporary tree removed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-target", type=Path)
    parser.add_argument("--smoke-apply", action="store_true")
    args = parser.parse_args()
    manifest = make_patch()
    if args.verify_target:
        verify_target(args.verify_target, manifest)
    if args.smoke_apply:
        smoke_apply(manifest)
    print(f"built {len(manifest)} fingerprinted diffs in {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
