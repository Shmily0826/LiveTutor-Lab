"""Can the patched host be rebuilt from upstream plus this repository alone?

Exports the pinned upstream revision of N.E.K.O into a temporary directory, replays the same
patch chain a launch runs (neko_desktop_tutor_host.apply_voice_host_patch), and compares every
file the host manifest pins with its recorded patched SHA-256. Nothing outside the temporary
directory is written; the real host trees are only read.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
MANIFEST = ROOT / "patches/neko-study-2026-10-10-host/manifest.json"
UPSTREAM = ROOT / "candidates/N.E.K.O"


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    revision = manifest["source_revision"]
    archive = subprocess.run(["git", "-C", str(UPSTREAM), "archive", "--format=tar", revision],
                             check=True, capture_output=True).stdout
    import neko_desktop_tutor_host as host
    # Inside the project: the helper deployer refuses host trees outside it.
    with tempfile.TemporaryDirectory(prefix="claude-host-rebuild-", dir=ROOT / "benchmarks/raw") as folder:
        tree = Path(folder)
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(tree, filter="data")
        chain = host.apply_voice_host_patch(hosts=(tree,), source_app=tree)
        files = []
        for item in manifest["files"]:
            rebuilt = sha(tree / item["path"])
            files.append({"path": item["path"], "matches": rebuilt == item["patched_sha256"],
                          "rebuilt": rebuilt and rebuilt[:12], "pinned": item["patched_sha256"][:12],
                          "live": (sha(host.SOURCE_APP / item["path"]) or "")[:12]})
        helpers = []
        for item in manifest.get("runtime_helpers", []):
            deployed = item.get("deployed_path")
            if deployed:
                rebuilt = sha(tree / deployed) or sha(tree / "main_logic" / deployed)
                helpers.append({"path": deployed, "present": rebuilt is not None})
    mismatched = [entry for entry in files if not entry["matches"]]
    report = {"revision": revision, "files": len(files), "matching": len(files) - len(mismatched),
              "mismatched": mismatched, "helpers": helpers, "chain": chain[:2000]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main())
