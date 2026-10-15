"""Rebuild the patched host from upstream plus this repository, and prove it byte for byte.

The launch-time string patches (neko_voice_host_patch and friends) upgrade trees that went
through this project's history; several _tools.py hunks expect intermediate states, so they
cannot replay onto pristine upstream in any fixed order. This script keeps one reviewable
unified diff per pinned host file (upstream revision -> pinned bytes) under
patches/neko-study-2026-10-10-host/rebuild/ and checks that

    git archive <revision> + git apply <diffs>  ==  every pinned patched_sha256.

  --write   regenerate the diffs from the live runtime tree (only when it matches the pins)
  (default) verify: rebuild into a temporary tree under benchmarks/raw and compare

Nothing outside the temporary tree is written in verify mode; host trees are only read.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "patches/neko-study-2026-10-10-host/manifest.json"
DIFFS = ROOT / "patches/neko-study-2026-10-10-host/rebuild"
UPSTREAM = ROOT / "candidates/N.E.K.O"
LIVE = ROOT / "benchmarks/raw/neko-product-host"


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def upstream_bytes(revision: str, relative: str) -> bytes | None:
    # LF bytes, as pinned: a Windows autocrlf setting would otherwise rewrite them.
    done = subprocess.run(["git", "-c", "core.autocrlf=false", "-C", str(UPSTREAM), "show",
                           f"{revision}:{relative}"], capture_output=True)
    return done.stdout if done.returncode == 0 else None


def diff_name(relative: str) -> str:
    return relative.replace("/", "__") + ".diff"


def write(manifest: dict) -> int:
    revision = manifest["source_revision"]
    stale = [item["path"] for item in manifest["files"] if sha(LIVE / item["path"]) != item["patched_sha256"]]
    if stale:
        print(json.dumps({"refused": "live tree does not match the pins", "files": stale}, indent=2))
        return 1
    DIFFS.mkdir(parents=True, exist_ok=True)
    for old in DIFFS.glob("*.diff"):
        old.unlink()
    with tempfile.TemporaryDirectory(prefix="claude-host-diff-", dir=ROOT / "benchmarks/raw") as folder:
        work = Path(folder)
        for item in manifest["files"]:
            relative = item["path"]
            base = upstream_bytes(revision, relative)
            a = work / "a" / relative
            b = work / "b" / relative
            b.parent.mkdir(parents=True, exist_ok=True)
            b.write_bytes((LIVE / relative).read_bytes())
            if base is not None:
                a.parent.mkdir(parents=True, exist_ok=True)
                a.write_bytes(base)
            done = subprocess.run(["git", "-c", "core.autocrlf=false", "diff", "--no-index", "--binary", "--no-prefix",
                                   "--no-color", f"a/{relative}" if base is not None else "/dev/null",
                                   f"b/{relative}"], cwd=work, capture_output=True)
            if done.returncode not in (0, 1):
                raise RuntimeError(done.stderr.decode("utf-8", "replace"))
            (DIFFS / diff_name(relative)).write_bytes(done.stdout)
    print(json.dumps({"written": len(manifest["files"]), "revision": revision}))
    return 0


def verify(manifest: dict) -> int:
    revision = manifest["source_revision"]
    archive = subprocess.run(["git", "-c", "core.autocrlf=false", "-C", str(UPSTREAM), "archive",
                              "--format=tar", revision], check=True, capture_output=True).stdout
    with tempfile.TemporaryDirectory(prefix="claude-host-rebuild-", dir=ROOT / "benchmarks/raw") as folder:
        tree = Path(folder)
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(tree, filter="data")
        patches = sorted(DIFFS.glob("*.diff"))
        # The tree lives inside this repository; without a ceiling git apply would resolve
        # paths against the outer repository and silently skip every one of them.
        applied = subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "--whitespace=nowarn",
                                  *[str(path) for path in patches if path.stat().st_size]],
                                 cwd=tree, capture_output=True,
                                 env={**__import__("os").environ, "GIT_CEILING_DIRECTORIES": str(tree.parent)})
        results = []
        for item in manifest["files"]:
            rebuilt = sha(tree / item["path"])
            results.append({"path": item["path"], "matches": rebuilt == item["patched_sha256"]})
    mismatched = [entry["path"] for entry in results if not entry["matches"]]
    report = {"revision": revision, "diffs": len(patches), "apply_exit": applied.returncode,
              "apply_error": applied.stderr.decode("utf-8", "replace")[:1000],
              "files": len(results), "matching": len(results) - len(mismatched), "mismatched": mismatched}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not mismatched and applied.returncode == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return write(manifest) if parser.parse_args().write else verify(manifest)


if __name__ == "__main__":
    sys.exit(main())
